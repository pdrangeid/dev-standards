"""``session-lint`` and ``session-schema`` console scripts."""

import json
import logging
from collections import Counter
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dev_standards.logging_setup import configure_logging

from .export import generate_schemas
from .lint import Severity, collect_paths, validate_session

logger = logging.getLogger(__name__)
console = Console()

lint_app = typer.Typer(help="Lint .session/ files against the session schema.")
schema_app = typer.Typer(help="Export the session JSON Schemas.")

_DEBUG = typer.Option(False, "--debug", help="Enable debug logging.")
_STYLE = {Severity.error: "red", Severity.warning: "yellow", Severity.info: "cyan"}


class OutputFormat(StrEnum):
    text = "text"
    json = "json"


@lint_app.command()
def lint(
    paths: list[Path] = typer.Argument(
        ..., help="Session files or directories (recurses *.md)."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Treat files without frontmatter as errors."
    ),
    fmt: OutputFormat = typer.Option(OutputFormat.text, "--format"),
    debug: bool = _DEBUG,
) -> None:
    """Lint session files. Exits 1 if any error-severity issue is found."""
    configure_logging(debug)
    files = collect_paths(paths)
    issues = []
    for f in files:
        if not f.is_file():
            logger.error(f"Failed to lint {f}: not a file")
            console.print(f"[bold red]❌ {f}: not a file[/bold red]")
            raise typer.Exit(1)
        logger.debug(f"🔍 linting {f}")
        issues.extend(validate_session(f, strict=strict))

    counts = Counter(str(i.severity) for i in issues)
    status = "fail" if counts["error"] else "pass"
    logger.info(
        f"SUMMARY files={len(files)} errors={counts['error']} "
        f"warnings={counts['warning']} infos={counts['info']} status={status}"
    )
    if fmt == OutputFormat.json:
        typer.echo(json.dumps([i.to_dict() for i in issues], indent=2))
    else:
        if issues:
            table = Table(show_lines=False)
            for col in ("file", "line", "severity", "rule", "message"):
                table.add_column(col, overflow="fold")
            for i in issues:
                style = _STYLE[i.severity]
                table.add_row(
                    i.path,
                    str(i.line or ""),
                    f"[{style}]{i.severity}[/{style}]",
                    i.rule,
                    i.message,
                )
            console.print(table)
        mark = "❌" if counts["error"] else "✅"
        console.print(
            f"{mark} {len(files)} file(s): {counts['error']} error(s), "
            f"{counts['warning']} warning(s), {counts['info']} info"
        )
    if counts["error"]:
        raise typer.Exit(1)


@schema_app.callback()
def _schema_root() -> None:
    """Export the session JSON Schemas."""


@schema_app.command("export")
def export(
    out: Path = typer.Option(Path("schemas"), "--out", help="Output directory."),
    debug: bool = _DEBUG,
) -> None:
    """Write session-header/ledger JSON Schemas generated from the models."""
    configure_logging(debug)
    out.mkdir(parents=True, exist_ok=True)
    for name, schema in generate_schemas().items():
        (out / name).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        console.print(f"✅ wrote {out / name}")
    logger.info(f"SUMMARY action=export dir={out} files=2")
