"""Schema and parsing behaviour for registry files."""

import pytest

from dev_standards.registry.models import (
    RegistryError,
    load_entry,
    parse_mapping,
    registry_filename,
    validate_entry,
)


def test_filename_uses_underscores():
    assert registry_filename("lifeos-core") == "lifeos_core_registry.yaml"


def test_minimal_entry_valid():
    entry = validate_entry({"repo": "r", "purpose": "Why"}, "t")
    assert entry.interfaces == [] and entry.integration_points.deps == []


@pytest.mark.parametrize("purpose", ["", "   ", None])
def test_purpose_required(purpose):
    with pytest.raises(RegistryError, match="purpose"):
        validate_entry({"repo": "r", "purpose": purpose}, "t")


def test_missing_repo_fails():
    with pytest.raises(RegistryError, match="repo"):
        validate_entry({"purpose": "Why"}, "t")


def test_unknown_key_fails():
    with pytest.raises(RegistryError, match="bogus"):
        validate_entry({"repo": "r", "purpose": "Why", "bogus": 1}, "t")


def test_lenient_list_coercion():
    entry = validate_entry(
        {
            "repo": "r",
            "purpose": "Why",
            "interfaces": "one",
            "contracts": None,
            "integration_points": {"env": [8080, "X", ""], "deps": "dep"},
        },
        "t",
    )
    assert entry.interfaces == ["one"]
    assert entry.contracts == []
    assert entry.integration_points.env == ["8080", "X"]
    assert entry.integration_points.deps == ["dep"]


def test_parse_strips_fences_and_prose():
    assert parse_mapping("Sure!\n```yaml\npurpose: x\n```\nbye", "t") == {
        "purpose": "x"
    }


def test_parse_unwraps_single_item_list():
    """The old ad hoc generator emitted a one-entry list."""
    assert parse_mapping("- repo: r\n  purpose: x\n", "t") == {
        "repo": "r",
        "purpose": "x",
    }


@pytest.mark.parametrize("text", ["just prose", "- a\n- b\n", "", "[unclosed: yaml: :"])
def test_parse_rejects_non_mappings(text):
    with pytest.raises(RegistryError):
        parse_mapping(text, "t")


def test_load_entry_reads_existing_ecosystem_shape(tmp_path):
    """Existing hand-made files (repo/purpose/... with no generated_from) still load."""
    path = tmp_path / "lifeos_mcp_registry.yaml"
    path.write_text(
        'repo: "lifeos-mcp"\npurpose: "Semantic interface"\ninterfaces: ["cli"]\n'
        'contracts: ["Payload"]\nintegration_points:\n  env: ["X"]\n  config: ["y"]\n'
        '  deps: ["lifeos-core"]\nmodel_prefs: "Qwen for Tier 1"\n'
    )
    entry = load_entry(path)
    assert entry.repo == "lifeos-mcp" and entry.generated_from is None
