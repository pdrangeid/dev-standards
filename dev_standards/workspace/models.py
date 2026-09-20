"""Pydantic model for ``workspace.yaml`` — a workspace's single source of truth."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class WorkspaceError(Exception):
    """Any user-facing workspace problem (bad yaml, missing dir, bad markers)."""


@dataclass(frozen=True)
class ServerProfile:
    """What we know about an MCP server package's env contract and tool names."""

    database_var: str
    read_only_var: str
    static_env: dict[str, str] = field(default_factory=dict)
    secret_vars: tuple[str, ...] = ()
    default_write_tool: str | None = None


# Keyed by PyPI package name. The official Neo4j server (github.com/neo4j/mcp)
# reads NEO4J_MCP_* as canonical names; the un-prefixed NEO4J_* names are legacy
# aliases, so we emit exactly one scheme. Verified against v1.6.0 config.go.
KNOWN_SERVERS: dict[str, ServerProfile] = {
    "neo4j-mcp-server": ServerProfile(
        database_var="NEO4J_MCP_DATABASE",
        read_only_var="NEO4J_MCP_READ_ONLY",
        static_env={"NEO4J_MCP_TELEMETRY": "false"},
        secret_vars=("NEO4J_MCP_URI", "NEO4J_MCP_USERNAME", "NEO4J_MCP_PASSWORD"),
        default_write_tool="write-cypher",
    ),
}


def _require_absolute(value: Path, label: str) -> Path:
    """Reject relative paths and unexpanded ``~`` so the yaml means one thing."""
    if str(value).startswith("~"):
        raise ValueError(f"{label} must be absolute; '~' is not expanded (got {value})")
    if not value.is_absolute():
        raise ValueError(f"{label} must be an absolute path (got {value})")
    return value


class Repo(BaseModel):
    """One repo in the workspace."""

    model_config = ConfigDict(extra="forbid")

    name: str
    role: str | None = None  # fallback when no registry YAML describes the repo

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(f"invalid repo name {v!r}")
        return v


class Graph(BaseModel):
    """Graph target shared by every session in the workspace."""

    model_config = ConfigDict(extra="forbid")

    database: str
    read_only: bool = True

    @field_validator("database")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("graph.database must not be empty")
        return v


class McpServer(BaseModel):
    """An MCP server rendered into ``.mcp.json``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    package: str
    version: str  # exact pin — ranges/latest are rejected
    env_file: str = ".env"
    write_tool: str | None = None  # gets a permissions deny rule; defaults per profile
    env: dict[str, str] = Field(default_factory=dict)  # extra non-secret env

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError(f"invalid MCP server name {v!r}")
        return v

    @field_validator("version")
    @classmethod
    def _pinned(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d+(\.\d+)*([A-Za-z0-9.+-]*)$", v):
            raise ValueError(f"version must be an exact pin like '1.6.0' (got {v!r})")
        return v

    @property
    def profile(self) -> ServerProfile | None:
        """Known env/tool contract for this package, if any."""
        return KNOWN_SERVERS.get(self.package)

    @property
    def effective_write_tool(self) -> str | None:
        """Explicit ``write_tool`` wins; otherwise the profile's default."""
        if self.write_tool:
            return self.write_tool
        return self.profile.default_write_tool if self.profile else None


class Mcp(BaseModel):
    """MCP section of ``workspace.yaml``."""

    model_config = ConfigDict(extra="forbid")

    servers: list[McpServer] = Field(default_factory=list)


class Standards(BaseModel):
    """Which dev-standards fragments compose the workspace AGENTS.md."""

    model_config = ConfigDict(extra="forbid")

    modules: list[str] = Field(default_factory=list)  # base + workspace are implicit

    @field_validator("modules")
    @classmethod
    def _no_implicit(cls, v: list[str]) -> list[str]:
        implicit = {"base", "workspace"} & set(v)
        if implicit:
            raise ValueError(
                f"{sorted(implicit)} are always included; do not list them"
            )
        return v


class Workspace(BaseModel):
    """Validated ``workspace.yaml``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    repos_root: Path
    registry_dir: Path | None = None  # where <repo>_registry.yaml files live
    repos: list[Repo] = Field(min_length=1)
    graph: Graph
    mcp: Mcp = Field(default_factory=Mcp)
    standards: Standards = Field(default_factory=Standards)

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(f"invalid workspace name {v!r}")
        return v

    @field_validator("repos_root")
    @classmethod
    def _root_abs(cls, v: Path) -> Path:
        return _require_absolute(v, "repos_root")

    @field_validator("registry_dir")
    @classmethod
    def _registry_abs(cls, v: Path | None) -> Path | None:
        return None if v is None else _require_absolute(v, "registry_dir")

    @field_validator("repos")
    @classmethod
    def _unique_repos(cls, v: list[Repo]) -> list[Repo]:
        names = [r.name for r in v]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise ValueError(f"duplicate repos: {dupes}")
        return v

    def repo_path(self, repo: Repo) -> Path:
        """Absolute path of ``repo`` under ``repos_root``."""
        return self.repos_root / repo.name

    def missing_paths(self) -> list[Path]:
        """Repo dirs (and repos_root itself) that do not exist on this machine."""
        if not self.repos_root.is_dir():
            return [self.repos_root]
        return [p for r in self.repos if not (p := self.repo_path(r)).is_dir()]


def load_workspace(path: Path, *, check_paths: bool = True) -> Workspace:
    """Load and validate ``workspace.yaml``; raise WorkspaceError on any problem.

    With ``check_paths`` the repo directories must exist on this machine.
    """
    try:
        raw = yaml.safe_load(Path(path).read_text())
    except OSError as e:
        raise WorkspaceError(f"Cannot read {path}: {e}") from e
    except yaml.YAMLError as e:
        raise WorkspaceError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(raw, dict):
        raise WorkspaceError(f"{path} must contain a YAML mapping at the top level")
    try:
        ws = Workspace.model_validate(raw)
    except ValidationError as e:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in e.errors()
        )
        raise WorkspaceError(f"Invalid {path}: {problems}") from e
    if check_paths:
        missing = ws.missing_paths()
        if missing:
            listing = ", ".join(str(p) for p in missing)
            raise WorkspaceError(f"Repo directories not found: {listing}")
    logger.debug(f"Loaded workspace {ws.name} with {len(ws.repos)} repos from {path}")
    return ws
