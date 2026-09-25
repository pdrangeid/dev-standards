"""The committed JSON Schemas must match what the models generate."""

import json
from pathlib import Path

from typer.testing import CliRunner

from dev_standards.session_schema import generate_schemas
from dev_standards.session_schema.cli import schema_app

SCHEMAS = Path(__file__).parent.parent / "schemas"


def test_committed_schemas_match_models():
    generated = generate_schemas()
    assert sorted(generated) == [
        "session-header.v1.schema.json",
        "session-ledger.v1.schema.json",
    ]
    for name, schema in generated.items():
        committed = json.loads((SCHEMAS / name).read_text())
        assert (
            committed == schema
        ), f"{name} is stale; run `uv run session-schema export --out schemas/`"


def test_schemas_document_the_validator_limitation():
    for schema in generate_schemas().values():
        assert "necessary but not sufficient" in schema["description"]


def test_export_writes_byte_identical_files(tmp_path):
    result = CliRunner().invoke(schema_app, ["export", "--out", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for name in generate_schemas():
        assert (tmp_path / name).read_bytes() == (SCHEMAS / name).read_bytes()
