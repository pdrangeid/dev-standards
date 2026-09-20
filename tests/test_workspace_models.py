"""Validation failures and successes for workspace.yaml."""

import pytest

from dev_standards.workspace.models import WorkspaceError, load_workspace


def test_valid_yaml_loads(make_yaml):
    ws = load_workspace(make_yaml())
    assert ws.name == "test-ws"
    assert [r.name for r in ws.repos] == ["repo-a", "repo-b"]
    assert ws.mcp.servers[0].effective_write_tool == "write-cypher"


def test_relative_repos_root_fails(make_yaml):
    with pytest.raises(WorkspaceError, match="repos_root must be an absolute path"):
        load_workspace(make_yaml(repos_root="develop"))


def test_tilde_repos_root_fails(make_yaml):
    with pytest.raises(WorkspaceError, match="'~' is not expanded"):
        load_workspace(make_yaml(repos_root="~/develop"))


@pytest.mark.parametrize("database", ["", "   "])
def test_empty_graph_database_fails(make_yaml, database):
    with pytest.raises(WorkspaceError, match="graph.database must not be empty"):
        load_workspace(make_yaml(graph={"database": database}))


def test_missing_repo_dir_fails(make_yaml):
    path = make_yaml(repos=[{"name": "repo-a"}, {"name": "does-not-exist"}])
    with pytest.raises(WorkspaceError, match="does-not-exist"):
        load_workspace(path)


def test_missing_repo_dir_ignored_when_paths_not_checked(make_yaml):
    path = make_yaml(repos=[{"name": "does-not-exist"}])
    assert load_workspace(path, check_paths=False).repos[0].name == "does-not-exist"


def test_duplicate_repos_fail(make_yaml):
    with pytest.raises(WorkspaceError, match="duplicate repos"):
        load_workspace(make_yaml(repos=[{"name": "repo-a"}, {"name": "repo-a"}]))


@pytest.mark.parametrize("version", ["latest", ">=1.0", ""])
def test_unpinned_mcp_version_fails(make_yaml, version):
    servers = [{"name": "neo4j", "package": "neo4j-mcp-server", "version": version}]
    with pytest.raises(WorkspaceError, match="version"):
        load_workspace(make_yaml(mcp={"servers": servers}))


def test_implicit_modules_rejected(make_yaml):
    with pytest.raises(WorkspaceError, match="always included"):
        load_workspace(make_yaml(standards={"modules": ["workspace"]}))


def test_unknown_key_fails(make_yaml):
    with pytest.raises(WorkspaceError, match="bogus"):
        load_workspace(make_yaml(bogus=1))


def test_non_mapping_yaml_fails(tmp_path):
    path = tmp_path / "workspace.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(WorkspaceError, match="YAML mapping"):
        load_workspace(path)
