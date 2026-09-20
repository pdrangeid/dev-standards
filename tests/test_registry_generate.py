"""Generator behaviour: overwrite-not-append, idempotency, and safe failure."""

import shlex

import pytest
import yaml

from dev_standards.registry.generate import generate_entry, resolve_llm_cmd
from dev_standards.registry.models import RegistryError, load_entry


def gen(root, fake_llm, **kw):
    return generate_entry(root, llm_cmd=shlex.split(fake_llm.cmd), **kw)


def test_creates_file_named_from_directory(make_repo, fake_llm):
    root = make_repo("my-repo")
    result = gen(root, fake_llm)
    assert result.status == "created"
    assert result.path == root / "my_repo_registry.yaml"
    entry = load_entry(result.path)
    assert entry.repo == "my-repo"
    assert entry.generated_from.startswith("sha256:")
    assert entry.contracts == ["SingleContract"]  # scalar coerced to a list


def test_output_satisfies_consumer_contract(make_repo, fake_llm):
    """The file must be a dict with a purpose, exactly what lookup_purpose reads."""
    path = gen(make_repo(), fake_llm).path
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict) and data["purpose"]


def test_repo_identity_is_not_trusted_from_the_llm(make_repo, fake_llm):
    fake_llm.mode("stray")  # emits repo: wrong-name and an unknown "notes" key
    entry = load_entry(gen(make_repo("real-name"), fake_llm).path)
    assert entry.repo == "real-name"


def test_fenced_output_accepted(make_repo, fake_llm):
    fake_llm.mode("fenced")
    assert gen(make_repo(), fake_llm).status == "created"


def test_rerun_on_unchanged_repo_is_a_noop(make_repo, fake_llm):
    root = make_repo()
    first = gen(root, fake_llm)
    before = first.path.read_bytes()
    second = gen(root, fake_llm)
    assert second.status == "skipped"
    assert first.path.read_bytes() == before
    assert fake_llm.calls == 1  # the LLM was not consulted again


def test_changed_docs_overwrite_not_append(make_repo, fake_llm):
    root = make_repo()
    path = gen(root, fake_llm).path
    (root / "README.md").write_text("# Changed\n")
    result = gen(root, fake_llm)
    assert result.status == "updated"
    assert fake_llm.calls == 2
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict)  # still one mapping, never a growing list
    assert data["purpose"] == "Version 2 of my-repo"
    assert path.read_text().count("purpose:") == 1


def test_force_regenerates(make_repo, fake_llm):
    root = make_repo()
    gen(root, fake_llm)
    assert gen(root, fake_llm, force=True).status == "updated"
    assert fake_llm.calls == 2


def test_hand_edit_survives_until_inputs_change(make_repo, fake_llm):
    root = make_repo()
    path = gen(root, fake_llm).path
    path.write_text(path.read_text().replace("Version 1", "Hand edited"))
    assert gen(root, fake_llm).status == "skipped"
    assert "Hand edited" in path.read_text()
    (root / "README.md").write_text("# New docs\n")
    gen(root, fake_llm)
    assert "Hand edited" not in path.read_text()


@pytest.mark.parametrize("mode", ["fail", "empty", "bad", "nopurpose"])
def test_llm_failures_never_touch_an_existing_file(make_repo, fake_llm, mode):
    root = make_repo()
    path = gen(root, fake_llm).path
    good = path.read_text()
    (root / "README.md").write_text("# Changed so it must regenerate\n")
    fake_llm.mode(mode)
    with pytest.raises(RegistryError):
        gen(root, fake_llm)
    assert path.read_text() == good


def test_missing_llm_command_reports_clearly(make_repo):
    with pytest.raises(RegistryError, match="not found"):
        generate_entry(make_repo(), llm_cmd=["definitely-not-a-real-llm-cmd"])


def test_repo_without_docs_fails(tmp_path, fake_llm):
    empty = tmp_path / "empty-repo"
    empty.mkdir()
    with pytest.raises(RegistryError, match="nothing to analyze"):
        gen(empty, fake_llm)
    assert fake_llm.calls == 0


def test_llm_command_resolution(monkeypatch):
    monkeypatch.delenv("DEV_STANDARDS_REGISTRY_LLM_CMD", raising=False)
    assert resolve_llm_cmd() == ["claude", "-p"]
    monkeypatch.setenv("DEV_STANDARDS_REGISTRY_LLM_CMD", "gemini -p x")
    assert resolve_llm_cmd() == ["gemini", "-p", "x"]
    assert resolve_llm_cmd("other --x") == ["other", "--x"]
