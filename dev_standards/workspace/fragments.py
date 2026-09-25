"""Fragment library access — composes base + modules the same way the shell scripts do.

The shell scripts fetch ``claude/base.md`` and ``claude/modules/<m>.md`` over HTTP and
concatenate them. This module reads the same files from a local dev-standards checkout,
so core improvements flow into workspaces on the next render.
"""

import logging
import os
from pathlib import Path

from .models import Workspace, WorkspaceError

logger = logging.getLogger(__name__)

FRAGMENTS_ENV = "DEV_STANDARDS_CLAUDE_DIR"


def resolve_fragments_dir(override: Path | None = None) -> Path:
    """Locate ``claude/``: explicit option, then env var, then the checkout."""
    if override is not None:
        candidate = Path(override)
    elif os.environ.get(FRAGMENTS_ENV):
        candidate = Path(os.environ[FRAGMENTS_ENV])
    else:
        # dev_standards/workspace/fragments.py -> repo root (editable install)
        candidate = Path(__file__).resolve().parents[2] / "claude"
    if not (candidate / "base.md").is_file():
        raise WorkspaceError(
            f"dev-standards fragments not found at {candidate} (base.md missing). "
            f"Install with 'uv pip install -e .' from a checkout, "
            f"or set {FRAGMENTS_ENV}."
        )
    logger.debug(f"Using fragments from {candidate}")
    return candidate


def _read(path: Path, label: str) -> str:
    """Read a fragment, raising a WorkspaceError naming the missing piece."""
    try:
        return path.read_text().strip("\n")
    except OSError as e:
        raise WorkspaceError(f"Cannot read {label} fragment {path}: {e}") from e


def read_fragment(fragments_dir: Path, name: str) -> str:
    """Return a top-level template file (e.g. ``session-template.md``) byte-for-byte."""
    path = fragments_dir / name
    try:
        return path.read_text()
    except OSError as e:
        raise WorkspaceError(f"Cannot read template {path}: {e}") from e


def compose_standards(fragments_dir: Path, modules: list[str]) -> str:
    """Return base.md followed by each selected module, blank-line separated."""
    parts = [_read(fragments_dir / "base.md", "base")]
    for module in modules:
        parts.append(
            _read(fragments_dir / "modules" / f"{module}.md", f"module '{module}'")
        )
    return "\n\n".join(parts)


def workspace_rules(fragments_dir: Path, ws: Workspace) -> str:
    """Return the workspace fragment with workspace-specific values substituted."""
    text = _read(fragments_dir / "modules" / "workspace.md", "workspace")
    return text.replace("{{ graph_access }}", graph_access(ws))


def graph_access(ws: Workspace) -> str:
    """The workspace's graph rules, derived from the ``graph`` section."""
    g = ws.graph
    lines = [f"Database: `{g.database}`."]
    if g.profile:
        lines.append(
            f"Pipeline tools connect through the lifeos-neo4j profile `{g.profile}`; "
            "the MCP server uses the database above."
        )
    if g.allow_writes:
        lines.append(
            "The MCP write tool is enabled (`graph.allow_writes`). Before an ad-hoc "
            "write, state what it creates or changes; record the result in the "
            "session ledger."
        )
    else:
        lines.append(
            "Ad-hoc Cypher is read-only. Graph writes happen only by running "
            "pipeline tools."
        )
    return " ".join(lines)
