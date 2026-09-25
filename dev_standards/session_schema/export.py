"""Generate the published JSON Schemas from the Pydantic models."""

from .models import SCHEMA_VERSION, SessionHeader, SessionLedger

SCHEMA_BASE_URL = "https://github.com/pdrangeid/dev-standards/blob/develop/schemas"
_LIMITATION = (
    "Generated from dev_standards.session_schema.models; do not edit by hand. "
    "Captures shape and enums only: cross-field rules (model validators) are not "
    "expressible in JSON Schema, so validating against this schema is necessary "
    "but not sufficient. Run session-lint for the full rule set."
)


def schema_filename(kind: str) -> str:
    return f"session-{kind}.v{SCHEMA_VERSION}.schema.json"


def generate_schemas() -> dict[str, dict]:
    """Return {filename: JSON Schema} for the header and ledger models."""
    out: dict[str, dict] = {}
    for kind, model, what in (
        ("header", SessionHeader, "YAML frontmatter of a session file"),
        ("ledger", SessionLedger, "'yaml session-ledger' block under '## Ledger'"),
    ):
        name = schema_filename(kind)
        schema = model.model_json_schema()
        out[name] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{SCHEMA_BASE_URL}/{name}",
            **schema,
            "description": f"{what} (schema_version {SCHEMA_VERSION}). {_LIMITATION}",
        }
    return out
