"""refresh-dev-standards.sh: AGENTS.md refresh plus the .session/ scaffold sync.

Runs the real script against a temp project, fetching from this checkout's
claude/ via a file:// DEV_STANDARDS_RAW.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "refresh-dev-standards.sh"
CLAUDE = ROOT / "claude"
PROJECT_SPECIFIC = "## Project-Specific\n\nKeep me byte-for-byte.\n"
HEADER = "<!-- AUTO-GENERATED: base + modules[] -->\n"

pytestmark = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("curl")), reason="needs bash + curl"
)


def run(project: Path, *args: str, raw: str | None = None):
    env = {**os.environ, "DEV_STANDARDS_RAW": raw or CLAUDE.as_uri()}
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "AGENTS.md").write_text(HEADER + "old standards\n\n" + PROJECT_SPECIFIC)
    return tmp_path


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_refresh_creates_full_session_scaffold(project):
    result = run(project)
    assert result.returncode == 0, result.stdout + result.stderr
    session = project / ".session"
    assert (session / "_template.md").read_text() == (
        CLAUDE / "session-template.md"
    ).read_text()
    assert (session / "specs/adr/_template.md").read_text() == (
        CLAUDE / "adr-template.md"
    ).read_text()
    assert (session / "specs/adr/index.md").read_text() == (
        CLAUDE / "adr-index-template.md"
    ).read_text()
    assert (session / "archive/.gitkeep").is_file()
    agents = (project / "AGENTS.md").read_text()
    assert agents.endswith(PROJECT_SPECIFIC)
    assert (CLAUDE / "base.md").read_text() in agents


def test_refresh_replaces_templates_but_keeps_project_data(project):
    session = project / ".session"
    (session / "specs/adr").mkdir(parents=True)
    (session / "_template.md").write_text("# Session: [Topic]\nStatus: draft\n")
    (session / "specs/adr/index.md").write_text("| 0001 | mine | accepted |\n")
    (session / "specs/adr/0001-mine.md").write_text("my adr\n")
    (session / "2026-01-01-old.md").write_text("Status: complete\n")

    result = run(project)
    assert result.returncode == 0, result.stdout
    assert "Updated ./.session/_template.md" in result.stdout
    assert "```yaml session-ledger" in (session / "_template.md").read_text()
    assert (
        session / "specs/adr/index.md"
    ).read_text() == "| 0001 | mine | accepted |\n"
    assert (session / "specs/adr/0001-mine.md").read_text() == "my adr\n"
    assert (session / "2026-01-01-old.md").read_text() == "Status: complete\n"


def test_second_refresh_is_a_no_op(project):
    run(project)
    before = snapshot(project)
    result = run(project)
    assert result.returncode == 0
    assert snapshot(project) == before
    assert "[DRY-RUN]" not in result.stdout
    assert "unchanged" in result.stdout and "Created" not in result.stdout


def test_dry_run_writes_nothing(project):
    before = snapshot(project)
    result = run(project, "--dry-run")
    assert result.returncode == 0, result.stdout
    assert "[DRY-RUN] Would create: ./.session/_template.md" in result.stdout
    assert snapshot(project) == before


def test_failed_fetch_writes_nothing(project, tmp_path_factory):
    partial = tmp_path_factory.mktemp("claude")
    shutil.copy(CLAUDE / "base.md", partial / "base.md")  # templates missing
    before = snapshot(project)
    result = run(project, raw=partial.as_uri())
    assert result.returncode == 1
    assert "Failed to fetch session-template.md" in result.stdout
    assert snapshot(project) == before


def test_legacy_migration_also_syncs_scaffold(tmp_path):
    (tmp_path / "claude.md").write_text(HEADER + "old\n\n" + PROJECT_SPECIFIC)
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert not (tmp_path / "claude.md").exists()
    assert (tmp_path / "AGENTS.md").read_text().endswith(PROJECT_SPECIFIC)
    assert (tmp_path / ".session/_template.md").is_file()
    assert (tmp_path / ".session/specs/adr/index.md").is_file()
