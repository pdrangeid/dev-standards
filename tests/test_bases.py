"""Built base fragments: committed files match their sources; names map to files."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dev_standards.bases import (
    available_bases,
    base_filename,
    bases_app,
    build_bases,
    stale_bases,
)

CLAUDE = Path(__file__).parent.parent / "claude"


def test_committed_bases_are_built_from_sources():
    assert stale_bases(CLAUDE) == [], "run `uv run dev-standards bases build`"


def test_python_and_ops_bases_exist():
    assert available_bases(CLAUDE) == ["ops", "python"]
    assert sorted(build_bases(CLAUDE)) == ["base-ops.md", "base.md"]


def test_every_base_carries_the_shared_session_rules():
    common = (CLAUDE / "base-src/common.md").read_text()
    for rel in build_bases(CLAUDE):
        text = (CLAUDE / rel).read_text()
        assert text.endswith(common)
        assert "## Session Management" in text


def test_ops_base_has_no_python_toolchain_rules():
    ops = (CLAUDE / "base-ops.md").read_text()
    assert "# Claude Standards: Base Ops Conventions" in ops
    assert "set -euo pipefail" in ops
    for python_only in ("## CLI Conventions (Typer)", "config.py", "pytest-cov"):
        assert python_only not in ops


@pytest.mark.parametrize(
    ("name", "filename"), [("python", "base.md"), ("ops", "base-ops.md")]
)
def test_base_filename(name, filename):
    assert base_filename(name) == filename


@pytest.mark.parametrize("bad", ["", "Ops", "../x", "a b", "-x"])
def test_base_filename_rejects_bad_names(bad):
    with pytest.raises(ValueError):
        base_filename(bad)


def _copy_fragments(tmp_path: Path) -> Path:
    root = tmp_path / "claude"
    (root / "base-src").mkdir(parents=True)
    for src in (CLAUDE / "base-src").glob("*.md"):
        (root / "base-src" / src.name).write_text(src.read_text())
    return root


def test_check_fails_when_stale_and_build_fixes_it(tmp_path):
    root = _copy_fragments(tmp_path)
    runner = CliRunner()
    check = runner.invoke(bases_app, ["check", "--fragments-dir", str(root)])
    assert check.exit_code == 1
    assert "base-ops.md is stale" in check.output

    build = runner.invoke(bases_app, ["build", "--fragments-dir", str(root)])
    assert build.exit_code == 0, build.output
    assert (root / "base.md").read_text() == (CLAUDE / "base.md").read_text()

    again = runner.invoke(bases_app, ["build", "--fragments-dir", str(root)])
    assert "All bases up to date" in again.output
    assert (
        runner.invoke(bases_app, ["check", "--fragments-dir", str(root)]).exit_code == 0
    )
