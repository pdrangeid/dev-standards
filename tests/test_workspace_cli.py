"""End-to-end CLI behaviour: new, render, check."""

import json
import subprocess

from typer.testing import CliRunner

from dev_standards.main import app

runner = CliRunner()


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


def test_new_creates_git_repo_with_rendered_files(tmp_path, make_yaml):
    dest = tmp_path / "ws"
    result = runner.invoke(
        app, ["workspace", "new", str(dest), "--from", str(make_yaml())]
    )
    assert result.exit_code == 0, result.output

    for rel in (
        "workspace.yaml",
        "CLAUDE.md",
        "AGENTS.md",
        ".mcp.json",
        ".env.example",
        ".gitignore",
        ".claude/settings.json",
        ".session/_template.md",
    ):
        assert (dest / rel).is_file(), rel
    assert "Session: [Topic]" in (dest / ".session/_template.md").read_text()

    tracked = set(_git(dest, "ls-files").split())
    assert "workspace.yaml" in tracked
    assert ".claude/settings.local.json" not in tracked  # gitignored, machine-specific
    assert ".env" not in tracked
    assert "scaffold workspace test-ws" in _git(dest, "log", "-1", "--format=%s")
    assert _git(dest, "status", "--porcelain") == ""


def test_new_refuses_non_empty_dir(tmp_path, make_yaml):
    dest = tmp_path / "ws"
    dest.mkdir()
    (dest / "file").write_text("x")
    result = runner.invoke(
        app, ["workspace", "new", str(dest), "--from", str(make_yaml())]
    )
    assert result.exit_code == 1
    assert "not empty" in result.output


def test_new_validates_before_creating_anything(tmp_path, make_yaml):
    dest = tmp_path / "ws"
    result = runner.invoke(
        app,
        [
            "workspace",
            "new",
            str(dest),
            "--from",
            str(make_yaml(graph={"database": ""})),
        ],
    )
    assert result.exit_code == 1
    assert not dest.exists()


def test_check_and_render_cycle(tmp_path, make_yaml):
    dest = tmp_path / "ws"
    runner.invoke(app, ["workspace", "new", str(dest), "--from", str(make_yaml())])

    assert runner.invoke(app, ["workspace", "check", str(dest)]).exit_code == 0

    (dest / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
    drifted = runner.invoke(app, ["workspace", "check", str(dest)])
    assert drifted.exit_code == 1
    assert ".mcp.json" in drifted.output

    fixed = runner.invoke(app, ["workspace", "render", str(dest)])
    assert fixed.exit_code == 0
    assert ".mcp.json" in fixed.output
    assert runner.invoke(app, ["workspace", "check", str(dest)]).exit_code == 0

    again = runner.invoke(app, ["workspace", "render", str(dest)])
    assert "already up to date" in again.output


def test_check_fails_on_invalid_yaml(tmp_path, make_yaml):
    dest = tmp_path / "ws"
    runner.invoke(app, ["workspace", "new", str(dest), "--from", str(make_yaml())])
    (dest / "workspace.yaml").write_text("name: x\n")
    result = runner.invoke(app, ["workspace", "check", str(dest)])
    assert result.exit_code == 1
    assert "Invalid" in result.output
