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


FAKE_LLM = r"""
import os, re, sys
prompt = sys.stdin.read()
log = os.environ["FAKE_LLM_LOG"]
with open(log, "a") as f:
    f.write("call\n")
n = sum(1 for _ in open(log))
mode = os.environ.get("FAKE_LLM_MODE", "ok")
repo = re.search(r'for the repository "([^"]+)"', prompt).group(1)
if mode == "fail":
    sys.stderr.write("boom: auth expired")
    sys.exit(3)
if mode == "empty":
    sys.exit(0)
if mode == "bad":
    print("I cannot help with that. [not: yaml: at: all")
    sys.exit(0)
if mode == "nopurpose":
    print("interfaces: [a]")
    sys.exit(0)
body = (
    f"purpose: 'Version {n} of {repo}'\n"
    "interfaces: ['cli']\n"
    "contracts: 'SingleContract'\n"          # scalar where a list belongs
    "integration_points:\n  env: [FOO]\n  config: []\n  deps: [other-repo]\n"
    "model_prefs: None\n"
)
if mode == "fenced":
    body = "Here you go:\n```yaml\n" + body + "```\n"
if mode == "stray":
    body = "repo: wrong-name\nnotes: extra\n" + body
print(body)
"""


class FakeLlm:
    """A stand-in LLM command whose output changes on every call."""

    def __init__(self, tmp_path, monkeypatch):
        import shlex
        import sys

        self.script = tmp_path / "fake_llm.py"
        self.script.write_text(FAKE_LLM)
        self.log = tmp_path / "fake_llm.log"
        self.cmd = shlex.join([sys.executable, str(self.script)])
        self._mp = monkeypatch
        monkeypatch.setenv("FAKE_LLM_LOG", str(self.log))

    @property
    def calls(self) -> int:
        return len(self.log.read_text().splitlines()) if self.log.exists() else 0

    def mode(self, value: str) -> None:
        self._mp.setenv("FAKE_LLM_MODE", value)


@pytest.fixture
def fake_llm(tmp_path, monkeypatch):
    return FakeLlm(tmp_path, monkeypatch)


@pytest.fixture
def make_repo(tmp_path):
    """Create a repo dir with a README and return its path."""

    def _make(name: str = "my-repo", readme: str = "# My repo\nDoes things.\n") -> Path:
        root = tmp_path / "repos" / name
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(readme)
        return root

    return _make
