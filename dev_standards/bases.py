"""Build the selectable base fragments from their shared parts.

Each base is ``claude/base-src/<name>.md`` (the language/tooling sections) followed by
``claude/base-src/common.md`` (docs currency, git workflow, session management). The
built files are committed so the bash scripts can fetch one file per base over HTTP:

    python -> claude/base.md        (the default; name kept so old checkouts still work)
    <name> -> claude/base-<name>.md

Edit ``base-src/`` and run ``dev-standards bases build``; never edit a built file.
``tests/test_bases.py`` fails if the committed files are stale.
"""

import logging
import re
from pathlib import Path

import typer
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

DEFAULT_BASE = "python"
COMMON = "common"
SEPARATOR = "\n\n---\n\n"
BASE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

bases_app = typer.Typer(help="Build claude/base*.md from claude/base-src/.")


def base_filename(name: str) -> str:
    """File under ``claude/`` that holds the built base ``name``."""
    if not BASE_NAME_RE.match(name):
        raise ValueError(f"invalid base name {name!r}")
    return "base.md" if name == DEFAULT_BASE else f"base-{name}.md"


def available_bases(fragments_dir: Path) -> list[str]:
    """Base names that have a source file in ``base-src/``."""
    src = Path(fragments_dir) / "base-src"
    return sorted(p.stem for p in src.glob("*.md") if p.stem != COMMON)


def build_bases(fragments_dir: Path) -> dict[str, str]:
    """Return ``{built filename: content}`` for every base in ``base-src/``."""
    src = Path(fragments_dir) / "base-src"
    common = (src / f"{COMMON}.md").read_text()
    built = {}
    for name in available_bases(fragments_dir):
        head = (src / f"{name}.md").read_text().rstrip("\n")
        built[base_filename(name)] = head + SEPARATOR + common
    return built


def stale_bases(fragments_dir: Path) -> list[str]:
    """Built files that are missing or differ from what ``build_bases`` produces."""
    stale = []
    for rel, content in build_bases(fragments_dir).items():
        path = Path(fragments_dir) / rel
        if not path.is_file() or path.read_text() != content:
            stale.append(rel)
    return stale


def _default_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "claude"


def _setup_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@bases_app.command("build")
def build_cmd(
    fragments_dir: Path = typer.Option(
        None, "--fragments-dir", help="claude/ directory (default: this checkout)."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """Write claude/base*.md from base-src/."""
    _setup_logging(debug)
    root = fragments_dir or _default_dir()
    changed = []
    for rel, content in build_bases(root).items():
        path = root / rel
        if path.is_file() and path.read_text() == content:
            logger.debug(f"Unchanged: {rel}")
            continue
        path.write_text(content)
        changed.append(rel)
    for rel in changed:
        console.print(f"✅ Wrote claude/{rel}")
    if not changed:
        console.print("✅ All bases up to date")
    logger.info(f"SUMMARY bases={len(available_bases(root))} written={len(changed)}")


@bases_app.command("check")
def check_cmd(
    fragments_dir: Path = typer.Option(
        None, "--fragments-dir", help="claude/ directory (default: this checkout)."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """Exit 1 if any built base is stale."""
    _setup_logging(debug)
    root = fragments_dir or _default_dir()
    stale = stale_bases(root)
    for rel in stale:
        console.print(f"❌ claude/{rel} is stale; run `dev-standards bases build`")
    logger.info(f"SUMMARY bases={len(available_bases(root))} stale={len(stale)}")
    if stale:
        raise typer.Exit(1)
    console.print("✅ All bases up to date")
