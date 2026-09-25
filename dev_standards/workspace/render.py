"""Render a workspace: compute desired file contents, then apply or diff them.

``plan_render`` is pure with respect to the workspace folder except that it reads the
current files whose hand-written or unrelated content must survive a render. Both
``render`` and ``check`` are built on the same plan, so a render followed by a check
can never disagree.

Ownership per file:
  fully generated  CLAUDE.md, .mcp.json, .env.example,
                   .session/_template.md, .session/specs/adr/_template.md
  merge-rendered   .claude/settings.json (enableAllProjectMcpServers + this
                   workspace's MCP write-tool deny entries; other keys and deny
                   entries survive), .claude/settings.local.json (only
                   permissions.additionalDirectories)
  marker regions   AGENTS.md (only <!-- BEGIN/END GENERATED: name --> regions)
  ensure-lines     .gitignore (missing required lines appended, nothing removed)
  create-if-absent .session/specs/adr/index.md, .session/archive/.gitkeep
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .fragments import compose_standards, read_fragment, workspace_rules
from .models import Workspace, WorkspaceError
from .registry import lookup_purpose

logger = logging.getLogger(__name__)

MARKER_RE = re.compile(r"<!-- (BEGIN|END) GENERATED: ([A-Za-z0-9_-]+) -->")
NOTES_STUB = (
    "## Notes\n\n(hand-written; preserved on re-render)\n\n"
    "### Next Steps\n\n### Technical Debt\n\n### Review Log\n"
)
GITIGNORE_LINES = [".env", ".claude/settings.local.json"]


@dataclass(frozen=True)
class Drift:
    """One file whose on-disk content differs from what a render would produce."""

    path: str
    kind: str  # "missing" | "modified"


# --- AGENTS.md marker regions ------------------------------------------------


def region_block(name: str, body: str) -> str:
    """Wrap ``body`` in BEGIN/END markers for region ``name``."""
    inner = body.strip("\n")
    return f"<!-- BEGIN GENERATED: {name} -->\n{inner}\n<!-- END GENERATED: {name} -->"


def _find_region(text: str, name: str) -> tuple[int, int] | None:
    """Return (start, end) offsets of region ``name`` including markers, or None.

    Raises WorkspaceError if the markers are unbalanced, duplicated or out of order —
    we refuse to guess rather than risk overwriting hand-written text.
    """
    begins = [
        m
        for m in MARKER_RE.finditer(text)
        if m.group(2) == name and m.group(1) == "BEGIN"
    ]
    ends = [
        m
        for m in MARKER_RE.finditer(text)
        if m.group(2) == name and m.group(1) == "END"
    ]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0].start() > ends[0].start():
        raise WorkspaceError(
            f"AGENTS.md region '{name}' has malformed markers "
            f"({len(begins)} BEGIN, {len(ends)} END); fix or remove them by hand"
        )
    return begins[0].start(), ends[0].end()


def _insert_region(text: str, block: str) -> str:
    """Insert a region before the ``## Notes`` heading (outside regions), or append."""
    last_end = max(
        (m.end() for m in MARKER_RE.finditer(text) if m.group(1) == "END"), default=0
    )
    notes = re.compile(r"(?m)^## Notes\s*$").search(text, last_end)
    if notes:
        return text[: notes.start()] + block + "\n\n" + text[notes.start() :]
    logger.debug(
        "No '## Notes' heading found after generated regions; appending region"
    )
    return text.rstrip("\n") + "\n\n" + block + "\n"


def merge_regions(existing: str | None, regions: dict[str, str]) -> str:
    """Replace each region's contents in ``existing``; hand-written text is untouched.

    A missing file starts from a bare Notes stub, so the same code path creates and
    updates. A region absent from an existing file is inserted before Notes.
    """
    text = existing if existing is not None else NOTES_STUB
    for name, body in regions.items():
        block = region_block(name, body)
        span = _find_region(text, name)
        if span is None:
            logger.debug(f"AGENTS.md region '{name}' absent; inserting")
            text = _insert_region(text, block)
        else:
            text = text[: span[0]] + block + text[span[1] :]
    return text


# --- Individual file renderers ---------------------------------------------------


def _cell(value: str) -> str:
    """Make ``value`` safe for a single markdown table cell."""
    return " ".join(value.split()).replace("|", "\\|")


def repo_map(ws: Workspace) -> str:
    """Markdown table of repos; role comes from registry YAML, else ``role`` in yaml."""
    rows = ["## Repos", "", "| Repo | Path | Role |", "|---|---|---|"]
    for repo in ws.repos:
        role = (
            lookup_purpose(repo.name, ws.registry_dir)
            or repo.role
            or "(no description)"
        )
        rows.append(
            f"| {_cell(repo.name)} | {_cell(str(ws.repo_path(repo)))} | {_cell(role)} |"
        )
    return "\n".join(rows)


def _json(obj) -> str:
    return json.dumps(obj, indent=2) + "\n"


def render_mcp_json(ws: Workspace, root: Path) -> str:
    """``.mcp.json`` — no secrets; credentials come from the env file at launch."""
    servers = {}
    for server in ws.mcp.servers:
        env: dict[str, str] = {}
        if profile := server.profile:
            env[profile.database_var] = ws.graph.database
            if ws.graph.read_only:
                env[profile.read_only_var] = "true"
            env.update(profile.static_env)
        else:
            logger.debug(
                f"No profile for {server.package}; rendering only its explicit env"
            )
        env.update(server.env)

        env_file = Path(server.env_file)
        if not env_file.is_absolute():
            env_file = root / env_file
        entry = {
            "command": "uvx",
            "args": ["--env-file", str(env_file), f"{server.package}@{server.version}"],
        }
        if env:
            entry["env"] = env
        servers[server.name] = entry
    return _json({"mcpServers": servers})


def _load_json_object(existing: str | None, path: Path) -> dict:
    """Parse an existing JSON settings file; refuse to guess at a broken one."""
    if existing is None:
        return {}
    try:
        data = json.loads(existing)
    except json.JSONDecodeError as e:
        raise WorkspaceError(f"{path} is not valid JSON ({e}); fix it by hand") from e
    if not isinstance(data, dict):
        raise WorkspaceError(f"{path} must contain a JSON object")
    return data


def render_settings_json(ws: Workspace, existing: str | None, path: Path) -> str:
    """``.claude/settings.json`` — deny each write tool unless writes are allowed.

    Owns ``enableAllProjectMcpServers`` and this workspace's write-tool deny entries;
    other keys and hand-added deny rules survive a render.
    """
    ours = [
        f"mcp__{s.name}__{tool}"
        for s in ws.mcp.servers
        if (tool := s.effective_write_tool)
    ]
    data = _load_json_object(existing, path)
    data["enableAllProjectMcpServers"] = True
    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    kept = [e for e in permissions.get("deny", []) if e not in ours]
    permissions["deny"] = kept + ([] if ws.graph.allow_writes else ours)
    data["permissions"] = permissions
    return _json(data)


def render_settings_local(ws: Workspace, existing: str | None, path: Path) -> str:
    """Merge ``permissions.additionalDirectories`` into the existing local settings."""
    data = _load_json_object(existing, path)
    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    permissions["additionalDirectories"] = [str(ws.repo_path(r)) for r in ws.repos]
    data["permissions"] = permissions
    return _json(data)


def render_env_example(ws: Workspace) -> str:
    """``.env.example`` — the variable names each configured server needs, no values."""
    names: list[str] = []
    for server in ws.mcp.servers:
        if server.profile:
            names += [n for n in server.profile.secret_vars if n not in names]
    if not names:
        return "# No credentials required by the configured MCP servers.\n"
    return "".join(f"{n}=\n" for n in names)


def render_gitignore(existing: str | None) -> str:
    """Append any required ignore lines that are missing; never remove anything."""
    text = existing or ""
    present = {line.strip() for line in text.splitlines()}
    missing = [line for line in GITIGNORE_LINES if line not in present]
    if not missing:
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n".join(missing) + "\n"


# --- Plan / apply / diff -----------------------------------------------------------


def _read_existing(path: Path) -> str | None:
    """Current file content, or None if the file does not exist."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def plan_render(ws: Workspace, root: Path, fragments_dir: Path) -> dict[str, str]:
    """Return ``{relative path: desired content}`` for every rendered file."""
    root = Path(root).resolve()
    agents_regions = {
        "header": f"# Workspace: {ws.name}\n\n{ws.description}".rstrip()
        + "\n\n<!-- Rendered by `dev-standards workspace render` from workspace.yaml. "
        "Edit outside GENERATED regions only. -->",
        "standards": compose_standards(fragments_dir, ws.standards.modules),
        "workspace-rules": workspace_rules(fragments_dir, ws),
        "repo-map": repo_map(ws),
    }
    local_path = root / ".claude" / "settings.local.json"
    settings_path = root / ".claude" / "settings.json"
    plan = {
        "CLAUDE.md": "@AGENTS.md\n",
        "AGENTS.md": merge_regions(_read_existing(root / "AGENTS.md"), agents_regions),
        ".mcp.json": render_mcp_json(ws, root),
        ".claude/settings.json": render_settings_json(
            ws, _read_existing(settings_path), settings_path
        ),
        ".claude/settings.local.json": render_settings_local(
            ws, _read_existing(local_path), local_path
        ),
        ".env.example": render_env_example(ws),
        ".gitignore": render_gitignore(_read_existing(root / ".gitignore")),
    }
    plan.update(session_scaffold(root, fragments_dir))
    return plan


def session_scaffold(root: Path, fragments_dir: Path) -> dict[str, str]:
    """``.session/`` templates (owned) plus the ADR index and archive (only if absent).

    Mirrors what ``refresh-dev-standards.sh`` does for single repos. Session files
    themselves are never part of the plan.
    """
    plan = {
        ".session/_template.md": read_fragment(fragments_dir, "session-template.md"),
        ".session/specs/adr/_template.md": read_fragment(
            fragments_dir, "adr-template.md"
        ),
    }
    create_only = {
        ".session/specs/adr/index.md": read_fragment(
            fragments_dir, "adr-index-template.md"
        ),
        ".session/archive/.gitkeep": "",
    }
    for rel, content in create_only.items():
        if not (root / rel).exists():
            plan[rel] = content
    return plan


def diff_plan(root: Path, plan: dict[str, str]) -> list[Drift]:
    """Compare a plan with the folder on disk; empty list means no drift."""
    drift = []
    for rel, desired in plan.items():
        current = _read_existing(Path(root) / rel)
        if current is None:
            drift.append(Drift(rel, "missing"))
        elif current != desired:
            drift.append(Drift(rel, "modified"))
    return drift


def apply_plan(root: Path, plan: dict[str, str]) -> list[str]:
    """Write every file whose content differs; return the relative paths changed."""
    changed = []
    for rel, desired in plan.items():
        path = Path(root) / rel
        if _read_existing(path) == desired:
            logger.debug(f"Unchanged: {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(desired)
        changed.append(rel)
        logger.debug(f"Wrote: {rel}")
    return changed
