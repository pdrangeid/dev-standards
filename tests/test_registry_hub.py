"""Hub behaviour: symlinks, rollup, and the locked consumer contract."""

import shlex

import pytest
import yaml

from dev_standards.registry.generate import generate_entry
from dev_standards.registry.hub import (
    build_rollup,
    link_repo,
    linked_repos,
    resolve_hub,
    write_rollup,
)
from dev_standards.registry.models import RegistryError
from dev_standards.workspace.registry import lookup_purpose


@pytest.fixture
def hub(tmp_path):
    return tmp_path / "hub"


def make_registered(name, make_repo, fake_llm, hub):
    root = make_repo(name)
    generate_entry(root, llm_cmd=shlex.split(fake_llm.cmd))
    link_repo(hub, root)
    return root


def test_link_creates_symlink_to_repo_file(make_repo, fake_llm, hub):
    root = make_registered("my-repo", make_repo, fake_llm, hub)
    link = hub / "my_repo_registry.yaml"
    assert link.is_symlink()
    assert link.resolve() == (root / "my_repo_registry.yaml").resolve()
    assert linked_repos(hub) == [root.resolve()]


def test_link_is_idempotent_and_guards_conflicts(make_repo, fake_llm, hub, tmp_path):
    root = make_registered("my-repo", make_repo, fake_llm, hub)
    assert link_repo(hub, root) == "exists"
    # a different repo whose name maps to the same filename (foo-bar vs foo_bar)
    other = make_repo("my_repo")
    with pytest.raises(RegistryError, match="already points to"):
        link_repo(hub, other)
    assert link_repo(hub, other, force=True) == "relinked"
    assert linked_repos(hub) == [other.resolve()]


def test_link_refuses_to_replace_a_plain_file(make_repo, hub):
    hub.mkdir()
    (hub / "my_repo_registry.yaml").write_text("purpose: hand made\n")
    with pytest.raises(RegistryError, match="not a symlink"):
        link_repo(hub, make_repo("my-repo"))


def test_consumer_resolves_per_repo_file_through_symlink(make_repo, fake_llm, hub):
    """registry.py is unchanged: it just opens <name>_registry.yaml in registry_dir."""
    make_registered("my-repo", make_repo, fake_llm, hub)
    assert lookup_purpose("my-repo", hub) == "Version 1 of my-repo"


def test_consumer_falls_back_to_generated_rollup(make_repo, fake_llm, hub):
    make_registered("my-repo", make_repo, fake_llm, hub)
    write_rollup(hub)
    (hub / "my_repo_registry.yaml").unlink()  # only the aggregate remains
    assert lookup_purpose("my-repo", hub) == "Version 1 of my-repo"


def test_rollup_shape_sorted_and_without_metadata(make_repo, fake_llm, hub):
    for name in ("zeta", "alpha", "mid-repo"):
        make_registered(name, make_repo, fake_llm, hub)
    changed, result = write_rollup(hub)
    assert changed and result.count == 3 and not result.problems
    data = yaml.safe_load((hub / "registry.yaml").read_text())
    assert isinstance(data, list)  # the aggregate contract: a list of dicts
    assert [e["repo"] for e in data] == ["alpha", "mid-repo", "zeta"]
    assert all(e["purpose"] and "generated_from" not in e for e in data)


def test_rollup_is_idempotent(make_repo, fake_llm, hub):
    make_registered("my-repo", make_repo, fake_llm, hub)
    assert write_rollup(hub)[0] is True
    before = (hub / "registry.yaml").read_bytes()
    assert write_rollup(hub)[0] is False
    assert (hub / "registry.yaml").read_bytes() == before


def test_rollup_reports_and_skips_bad_and_broken_files(make_repo, fake_llm, hub):
    make_registered("good", make_repo, fake_llm, hub)
    bad = make_registered("bad", make_repo, fake_llm, hub)
    (bad / "bad_registry.yaml").write_text("purpose: ''\nrepo: bad\n")  # schema failure
    gone = make_registered("gone", make_repo, fake_llm, hub)
    (gone / "gone_registry.yaml").unlink()  # broken symlink
    result = build_rollup(hub)
    assert result.count == 1
    assert {p.split(":")[0] for p in result.problems} == {
        "bad_registry.yaml",
        "gone_registry.yaml",
    }


def test_rollup_of_empty_hub_is_an_empty_list(hub):
    hub.mkdir()
    assert yaml.safe_load(build_rollup(hub).text) == []


def test_hub_resolution(monkeypatch, tmp_path):
    monkeypatch.delenv("DEV_STANDARDS_REGISTRY_HUB", raising=False)
    assert resolve_hub().name == ".repository_registry"
    monkeypatch.setenv("DEV_STANDARDS_REGISTRY_HUB", str(tmp_path / "envhub"))
    assert resolve_hub() == (tmp_path / "envhub").resolve()
    assert resolve_hub(tmp_path / "opt") == (tmp_path / "opt").resolve()
