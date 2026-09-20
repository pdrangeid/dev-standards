"""``dev-standards registry`` commands: generate, add, refresh, rollup, check."""

import logging
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console

from dev_standards.logging_setup import configure_logging

from .generate import generate_entry, resolve_llm_cmd
from .hub import (
    ROLLUP_NAME,
    build_rollup,
    link_repo,
    linked_repos,
    registry_files,
    resolve_hub,
    write_rollup,
)
from .models import RegistryError, load_entry, registry_filename

logger = logging.getLogger(__name__)
console = Console()
registry_app = typer.Typer(help="Generate repo registry files and maintain the hub.")

_DEBUG = typer.Option(False, "--debug", help="Enable debug logging.")
_HUB = typer.Option(
    None,
    "--hub",
    help="Hub dir (default: $DEV_STANDARDS_REGISTRY_HUB or ~/.repository_registry).",
)
_LLM = typer.Option(
    None,
    "--llm-cmd",
    help="LLM command, prompt on stdin (default: $DEV_STANDARDS_REGISTRY_LLM_CMD "
    "or claude -p).",
)
_FORCE = typer.Option(
    False, "--force", help="Regenerate even if source docs are unchanged."
)


def _fail(e: RegistryError) -> "typer.Exit":
    logger.error(str(e))
    console.print(f"[bold red]❌ {e}[/bold red]")
    return typer.Exit(1)


def _rollup_line(hub: Path, changed: bool, count: int) -> None:
    verb = "updated" if changed else "unchanged"
    console.print(f"  🔗 rollup {verb}: {count} repo(s) in {hub / ROLLUP_NAME}")


@registry_app.command("generate")
def generate(
    path: Path = typer.Argument(Path("."), help="Repo root."),
    llm_cmd: str | None = _LLM,
    force: bool = _FORCE,
    debug: bool = _DEBUG,
) -> None:
    """Generate (or refresh) <repo>_registry.yaml at the repo root."""
    configure_logging(debug)
    try:
        result = generate_entry(path, llm_cmd=resolve_llm_cmd(llm_cmd), force=force)
    except RegistryError as e:
        raise _fail(e) from e
    logger.info(
        f"SUMMARY action=generate repo={result.path.parent.name} status={result.status}"
    )
    console.print(f"[bold green]✅ {result.path.name}: {result.status}[/bold green]")


@registry_app.command("add")
def add(
    path: Path = typer.Argument(Path("."), help="Repo root to register."),
    hub: Path | None = _HUB,
    llm_cmd: str | None = _LLM,
    no_generate: bool = typer.Option(
        False,
        "--no-generate",
        help="Link only; do not generate a missing registry file.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Replace a link that points elsewhere."
    ),
    debug: bool = _DEBUG,
) -> None:
    """Register a repo in the hub (generating its registry file if missing)."""
    configure_logging(debug)
    try:
        root = path.resolve()
        hub_dir = resolve_hub(hub)
        target = root / registry_filename(root.name)
        if not target.is_file() and not no_generate:
            console.print(f"  🌿 generating {target.name}")
            generate_entry(root, llm_cmd=resolve_llm_cmd(llm_cmd))
        action = link_repo(hub_dir, root, force=force)
        changed, rollup = write_rollup(hub_dir)
    except RegistryError as e:
        raise _fail(e) from e
    logger.info(
        f"SUMMARY action=add repo={root.name} link={action} rollup_repos={rollup.count}"
    )
    console.print(f"[bold green]✅ {root.name}: {action}[/bold green]")
    _rollup_line(hub_dir, changed, rollup.count)


@registry_app.command("refresh")
def refresh(
    hub: Path | None = _HUB,
    llm_cmd: str | None = _LLM,
    force: bool = _FORCE,
    debug: bool = _DEBUG,
) -> None:
    """Regenerate every repo linked in the hub (skipping unchanged), then the rollup."""
    configure_logging(debug)
    hub_dir = resolve_hub(hub)
    try:
        argv = resolve_llm_cmd(llm_cmd)
    except RegistryError as e:
        raise _fail(e) from e

    repos = linked_repos(hub_dir)
    if not repos:
        logger.warning(
            f"No repos linked in {hub_dir}; use 'dev-standards registry add'"
        )
    counts: Counter[str] = Counter()
    failed: list[str] = []
    for root in repos:
        try:
            status = generate_entry(root, llm_cmd=argv, force=force).status
        except RegistryError as e:
            # One bad repo must not stop the run; collect and surface at the end.
            logger.error(f"Failed to generate registry for {root.name}: {e}")
            failed.append(root.name)
            counts["failed"] += 1
            continue
        counts[status] += 1
        console.print(f"  🌿 {root.name}: {status}")

    changed, rollup = write_rollup(hub_dir)
    _rollup_line(hub_dir, changed, rollup.count)
    problems = len(rollup.problems)
    logger.info(
        f"SUMMARY action=refresh repos={len(repos)} created={counts['created']} "
        f"updated={counts['updated']} "
        f"unchanged={counts['unchanged'] + counts['skipped']} "
        f"failed={counts['failed']} rollup_repos={rollup.count} "
        f"rollup_problems={problems}"
    )
    if failed or problems:
        console.print(
            f"[yellow]⚠️  failed: {failed or 'none'}; "
            f"rollup problems: {problems}[/yellow]"
        )
        raise typer.Exit(1)
    console.print("[bold green]✅ registry refreshed[/bold green]")


@registry_app.command("rollup")
def rollup_cmd(hub: Path | None = _HUB, debug: bool = _DEBUG) -> None:
    """Rebuild the hub's registry.yaml from the linked per-repo files."""
    configure_logging(debug)
    hub_dir = resolve_hub(hub)
    changed, result = write_rollup(hub_dir)
    _rollup_line(hub_dir, changed, result.count)
    logger.info(
        f"SUMMARY action=rollup repos={result.count} problems={len(result.problems)}"
    )
    if result.problems:
        for problem in result.problems:
            console.print(f"  ⚠️  {problem}")
        raise typer.Exit(1)


@registry_app.command("check")
def check(hub: Path | None = _HUB, debug: bool = _DEBUG) -> None:
    """Validate every hub file against the schema and report rollup drift."""
    configure_logging(debug)
    hub_dir = resolve_hub(hub)
    problems: list[str] = []
    for path in registry_files(hub_dir):
        try:
            load_entry(path)
        except RegistryError as e:
            problems.append(f"{path.name}: {e}")
    rollup = build_rollup(hub_dir)
    rollup_path = hub_dir / ROLLUP_NAME
    current = rollup_path.read_text() if rollup_path.is_file() else None
    if current != rollup.text:
        problems.append(
            f"{ROLLUP_NAME}: {'missing' if current is None else 'out of date'}"
        )
    for problem in problems:
        logger.warning(f"Registry problem: {problem}")
        console.print(f"  ⚠️  {problem}")
    logger.info(
        f"SUMMARY action=check files={len(registry_files(hub_dir))} "
        f"problems={len(problems)}"
    )
    if problems:
        console.print(
            "[yellow]Run 'dev-standards registry rollup' or 'refresh' to fix.[/yellow]"
        )
        raise typer.Exit(1)
    console.print(
        f"[bold green]✅ {len(registry_files(hub_dir))} file(s) valid, "
        "rollup current[/bold green]"
    )
