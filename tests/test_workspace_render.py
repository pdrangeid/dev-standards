"""Render behaviour: generated content, idempotency, and preservation guarantees."""

import json

import pytest
import yaml

from dev_standards.workspace.fragments import resolve_fragments_dir
from dev_standards.workspace.models import WorkspaceError, load_workspace
from dev_standards.workspace.render import apply_plan, diff_plan, plan_render


@pytest.fixture
def fragments():
    return resolve_fragments_dir()


@pytest.fixture
def render(tmp_path, make_yaml, fragments):
    """A render() callable bound to a workspace folder; yaml is re-read each call."""
    root = tmp_path / "ws"
    root.mkdir()
    yaml_path = make_yaml()

    def _render(path=None):
        ws = load_workspace(path or yaml_path)
        return apply_plan(root, plan_render(ws, root, fragments))

    _render.root = root
    _render.yaml_path = yaml_path
    return _render


def test_generated_files(render):
    render()
    root = render.root
    assert (root / "CLAUDE.md").read_text() == "@AGENTS.md\n"

    mcp = json.loads((root / ".mcp.json").read_text())
    server = mcp["mcpServers"]["neo4j"]
    assert server["args"] == ["--env-file", f"{root}/.env", "neo4j-mcp-server@1.6.0"]
    # exactly one env var scheme, no secrets, read-only flag present
    assert server["env"] == {
        "NEO4J_MCP_DATABASE": "lifeos-kg",
        "NEO4J_MCP_READ_ONLY": "true",
        "NEO4J_MCP_TELEMETRY": "false",
    }
    assert not any(
        k.startswith("NEO4J_") and not k.startswith("NEO4J_MCP_") for k in server["env"]
    )

    settings = json.loads((root / ".claude/settings.json").read_text())
    assert settings["permissions"]["deny"] == ["mcp__neo4j__write-cypher"]
    assert settings["enableAllProjectMcpServers"] is True

    assert (root / ".env.example").read_text() == (
        "NEO4J_MCP_URI=\nNEO4J_MCP_USERNAME=\nNEO4J_MCP_PASSWORD=\n"
    )
    assert (root / ".gitignore").read_text() == ".env\n.claude/settings.local.json\n"


def test_read_only_false_omits_flag_but_keeps_deny(render, make_yaml):
    render(make_yaml(graph={"database": "lifeos-kg", "read_only": False}))
    root = render.root
    env = json.loads((root / ".mcp.json").read_text())["mcpServers"]["neo4j"]["env"]
    assert "NEO4J_MCP_READ_ONLY" not in env
    deny = json.loads((root / ".claude/settings.json").read_text())["permissions"][
        "deny"
    ]
    assert deny == ["mcp__neo4j__write-cypher"]


def test_agents_md_composition(render, fragments):
    render()
    text = (render.root / "AGENTS.md").read_text()
    assert text.count("<!-- BEGIN GENERATED:") == 4
    assert "# Workspace: test-ws" in text
    assert "A test workspace" in text
    # core + selected module + workspace rules all composed from the fragment library
    assert "# Claude Standards: Base Python Conventions" in text
    assert "Neo4j" in text
    assert "Database: `lifeos-kg`" in text
    assert (
        "{{"
        not in text.split("BEGIN GENERATED: workspace-rules")[1].split("END GENERATED")[
            0
        ]
    )
    assert text.rstrip().endswith("(hand-written; preserved on re-render)")


def test_repo_map_uses_role_fallback_and_absolute_paths(render, repos_root):
    render()
    text = (render.root / "AGENTS.md").read_text()
    assert f"| repo-a | {repos_root}/repo-a | Role of A |" in text
    assert f"| repo-b | {repos_root}/repo-b | (no description) |" in text


def test_registry_purpose_wins_over_role(render, make_yaml, tmp_path):
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "repo_a_registry.yaml").write_text(
        "repo: repo-a\npurpose: 'From registry | with pipe'\n"
    )
    (reg / "registry.yaml").write_text("- repo: repo-b\n  purpose: From aggregate\n")
    render(make_yaml(registry_dir=str(reg)))
    text = (render.root / "AGENTS.md").read_text()
    assert "From registry \\| with pipe" in text
    assert "Role of A" not in text
    assert "| From aggregate |" in text


def test_idempotent(render):
    first = render()
    assert "AGENTS.md" in first
    snapshot = {p.name: p.read_bytes() for p in render.root.rglob("*") if p.is_file()}
    assert render() == []  # nothing rewritten
    assert {
        p.name: p.read_bytes() for p in render.root.rglob("*") if p.is_file()
    } == snapshot


def test_hand_written_sections_preserved(render):
    render()
    agents = render.root / "AGENTS.md"
    text = agents.read_text()
    text = text.replace(
        "## Notes\n\n(hand-written; preserved on re-render)",
        "## Notes\n\nMy own note.\n\n## Extra\n\nMore hand-written text.",
    )
    text = text.replace(
        "<!-- BEGIN GENERATED: header -->",
        "Hand-written preamble.\n\n<!-- BEGIN GENERATED: header -->",
    )
    agents.write_text(text)
    render()
    result = agents.read_text()
    assert "My own note." in result
    assert "## Extra\n\nMore hand-written text." in result
    assert result.startswith("Hand-written preamble.")


def test_edits_inside_generated_region_are_overwritten(render):
    render()
    agents = render.root / "AGENTS.md"
    agents.write_text(
        agents.read_text().replace("## Precedence", "## Precedence HACKED")
    )
    assert "AGENTS.md" in render()
    assert "HACKED" not in agents.read_text()


def test_adding_a_repo_updates_map_and_dirs(render, repos_root, make_yaml):
    render()
    (repos_root / "repo-c").mkdir()
    path = make_yaml(
        repos=[{"name": "repo-a"}, {"name": "repo-b"}, {"name": "repo-c", "role": "C"}]
    )
    render(path)
    assert (
        f"| repo-c | {repos_root}/repo-c | C |"
        in (render.root / "AGENTS.md").read_text()
    )
    dirs = json.loads((render.root / ".claude/settings.local.json").read_text())
    assert dirs["permissions"]["additionalDirectories"][-1] == f"{repos_root}/repo-c"


def test_settings_local_unrelated_keys_preserved(render, repos_root):
    local = render.root / ".claude" / "settings.local.json"
    local.parent.mkdir(parents=True)
    local.write_text(
        json.dumps(
            {
                "enabledMcpjsonServers": ["neo4j"],
                "permissions": {
                    "allow": ["Bash(ls:*)"],
                    "additionalDirectories": ["/stale"],
                },
            }
        )
    )
    render()
    data = json.loads(local.read_text())
    assert data["enabledMcpjsonServers"] == ["neo4j"]
    assert data["permissions"]["allow"] == ["Bash(ls:*)"]
    assert data["permissions"]["additionalDirectories"] == [
        f"{repos_root}/repo-a",
        f"{repos_root}/repo-b",
    ]


def test_invalid_settings_local_json_is_not_clobbered(render):
    local = render.root / ".claude" / "settings.local.json"
    local.parent.mkdir(parents=True)
    local.write_text("{not json")
    with pytest.raises(WorkspaceError, match="not valid JSON"):
        render()
    assert local.read_text() == "{not json"


def test_gitignore_appends_without_removing(render):
    (render.root / ".gitignore").write_text("node_modules/\n.env")
    render()
    assert (render.root / ".gitignore").read_text() == (
        "node_modules/\n.env\n.claude/settings.local.json\n"
    )


def test_session_dir_never_touched(render):
    session = render.root / ".session"
    session.mkdir()
    (session / "2026-01-01-topic.md").write_text("mine")
    render()
    assert [p.name for p in session.iterdir()] == ["2026-01-01-topic.md"]


def test_missing_region_inserted_before_notes(render):
    render()
    agents = render.root / "AGENTS.md"
    start = agents.read_text().index("<!-- BEGIN GENERATED: repo-map -->")
    end = agents.read_text().index("<!-- END GENERATED: repo-map -->") + len(
        "<!-- END GENERATED: repo-map -->\n\n"
    )
    text = agents.read_text()
    agents.write_text(text[:start] + text[end:])
    assert "repo-map" not in agents.read_text()
    render()
    result = agents.read_text()
    assert result.index("BEGIN GENERATED: repo-map") < result.index("## Notes")


def test_malformed_markers_refuse_to_write(render):
    render()
    agents = render.root / "AGENTS.md"
    broken = agents.read_text().replace("<!-- END GENERATED: repo-map -->", "")
    agents.write_text(broken)
    with pytest.raises(WorkspaceError, match="malformed markers"):
        render()
    assert agents.read_text() == broken


def test_diff_plan_reports_missing_and_modified(render, fragments):
    ws = load_workspace(render.yaml_path)
    plan = plan_render(ws, render.root, fragments)
    assert {d.kind for d in diff_plan(render.root, plan)} == {"missing"}

    render()
    assert diff_plan(render.root, plan_render(ws, render.root, fragments)) == []

    (render.root / ".mcp.json").write_text("{}\n")
    (render.root / "CLAUDE.md").unlink()
    drift = {
        d.path: d.kind
        for d in diff_plan(render.root, plan_render(ws, render.root, fragments))
    }
    assert drift == {".mcp.json": "modified", "CLAUDE.md": "missing"}


def test_local_settings_unrelated_keys_are_not_drift(render, fragments):
    render()
    local = render.root / ".claude" / "settings.local.json"
    data = json.loads(local.read_text())
    data["somethingElse"] = True
    local.write_text(json.dumps(data, indent=2) + "\n")
    ws = load_workspace(render.yaml_path)
    assert diff_plan(render.root, plan_render(ws, render.root, fragments)) == []


def test_yaml_roundtrip_fixture_sanity(render):
    assert yaml.safe_load(render.yaml_path.read_text())["name"] == "test-ws"
