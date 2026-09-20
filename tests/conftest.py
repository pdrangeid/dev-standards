"""Shared fixtures for workspace tests."""

from pathlib import Path

import pytest
import yaml

REPO_NAMES = ["repo-a", "repo-b"]


@pytest.fixture
def repos_root(tmp_path: Path) -> Path:
    """A fake repos_root containing the directories named in REPO_NAMES."""
    root = tmp_path / "develop"
    for name in REPO_NAMES:
        (root / name).mkdir(parents=True)
    return root


@pytest.fixture
def make_yaml(tmp_path: Path, repos_root: Path):
    """Write a workspace.yaml (with overrides) and return its path."""

    def _make(name: str = "workspace.yaml", **overrides) -> Path:
        data = {
            "name": "test-ws",
            "description": "A test workspace",
            "repos_root": str(repos_root),
            "repos": [{"name": "repo-a", "role": "Role of A"}, {"name": "repo-b"}],
            "graph": {"database": "lifeos-kg", "read_only": True},
            "mcp": {
                "servers": [
                    {"name": "neo4j", "package": "neo4j-mcp-server", "version": "1.6.0"}
                ]
            },
            "standards": {"modules": ["neo4j"]},
        }
        data.update(overrides)
        path = tmp_path / name
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        return path

    return _make


@pytest.fixture(autouse=True)
def git_identity(monkeypatch):
    """Give git a deterministic identity so `workspace new` can commit anywhere."""
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "test@example.com")
