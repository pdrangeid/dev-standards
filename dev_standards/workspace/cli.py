"""``dev-standards workspace`` commands: new, render, check."""

import logging
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from dev_standards.logging_setup import configure_logging

from .fragments import resolve_fragments_dir
from .models import WorkspaceError, load_workspace
from .render import apply_plan, diff_plan, plan_render

logger = logging.getLogger(__name__)
console = Console()
workspace_app = typer.Typer(
    help="Scaffold and maintain multi-repo Claude Code workspaces."
)

YAML_NAME = "workspace.yaml"

_DEBUG = typer.Option(False, "--debug", help="Enable debug logging.")
_FRAGMENTS = typer.Option(
    None,
    "--fragments-dir",
    help="dev-standards claude/ dir (default: $DEV_STANDARDS_CLAUDE_DIR or checkout).",
)


def _fail(e: WorkspaceError) -> "typer.Exit":
    logger.error(str(e))
    console.print(f"[bold red]❌ {e}[/bold red]")
    return typer.Exit(1)


def _git(root: Path, *args: str) -> None:
    """Run a git command in ``root``, surfacing stderr on failure."""
    try:
        subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        detail = getattr(e, "stderr", "") or str(e)
        raise WorkspaceError(f"git {' '.join(args)} failed: {detail.strip()}") from e


@workspace_app.command("new")
def new(
    path: Path = typer.Argument(..., help="Folder to create."),
    from_yaml: Path = typer.Option(..., "--from", help="workspace.yaml to start from."),
    no_commit: bool = typer.Option(
        False, "--no-commit", help="Skip the initial commit."
    ),
    fragments_dir: Path | None = _FRAGMENTS,
    debug: bool = _DEBUG,
) -> None:
    """Create a workspace: folder, git init, render (incl. .session/), first commit."""
    configure_logging(debug)
    try:
        if path.exists() and any(path.iterdir()):
            raise WorkspaceError(f"{path} already exists and is not empty")
        ws = load_workspace(from_yaml)  # validate before touching the filesystem
        fragments = resolve_fragments_dir(fragments_dir)

        root = path.resolve()
        root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(from_yaml, root / YAML_NAME)
        _git(root, "init")
        changed = apply_plan(root, plan_render(ws, root, fragments))

        if not no_commit:
            _git(root, "add", "-A")
            _git(
                root,
                "commit",
                "-m",
                f"chore: scaffold workspace {ws.name} from workspace.yaml",
            )
    except WorkspaceError as e:
        raise _fail(e) from e
    logger.info(
        f"SUMMARY workspace={ws.name} action=new "
        f"files={len(changed)} repos={len(ws.repos)}"
    )
    console.print(f"[bold green]✅ Workspace {ws.name} created at {root}[/bold green]")


@workspace_app.command("render")
def render(
    path: Path = typer.Argument(Path("."), help="Workspace folder."),
    fragments_dir: Path | None = _FRAGMENTS,
    debug: bool = _DEBUG,
) -> None:
    """Re-render generated files after editing workspace.yaml."""
    configure_logging(debug)
    try:
        root = path.resolve()
        ws = load_workspace(root / YAML_NAME)
        plan = plan_render(ws, root, resolve_fragments_dir(fragments_dir))
        changed = apply_plan(root, plan)
    except WorkspaceError as e:
        raise _fail(e) from e
    for rel in changed:
        console.print(f"  🌿 {rel}")
    logger.info(f"SUMMARY workspace={ws.name} action=render changed={len(changed)}")
    console.print(
        f"[bold green]✅ Rendered {ws.name}: "
        f"{len(changed)} file(s) changed[/bold green]"
        if changed
        else f"[bold green]✅ {ws.name} already up to date[/bold green]"
    )


@workspace_app.command("check")
def check(
    path: Path = typer.Argument(Path("."), help="Workspace folder."),
    fragments_dir: Path | None = _FRAGMENTS,
    debug: bool = _DEBUG,
) -> None:
    """Validate workspace.yaml and report drift between it and the rendered files."""
    configure_logging(debug)
    try:
        root = path.resolve()
        ws = load_workspace(root / YAML_NAME)
        drift = diff_plan(
            root, plan_render(ws, root, resolve_fragments_dir(fragments_dir))
        )
    except WorkspaceError as e:
        raise _fail(e) from e
    for d in drift:
        logger.warning(f"Drift: {d.path} ({d.kind})")
        console.print(f"  ⚠️  {d.path}: {d.kind}")
    logger.info(f"SUMMARY workspace={ws.name} action=check drift={len(drift)}")
    if drift:
        console.print("[yellow]Run 'dev-standards workspace render' to fix.[/yellow]")
        raise typer.Exit(1)
    console.print(f"[bold green]✅ {ws.name}: yaml valid, no drift[/bold green]")
