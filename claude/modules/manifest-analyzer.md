# Claude Module: Manifest Analyzer

Manifest-first philosophy, URI conventions, confidence tracking, UnresolvedAsset pattern,
Pydantic data models, TypeMapper, and DataSampler conventions.

---

## Manifest-First Philosophy

- **Never** couple extraction directly to graph export in the same code path
- The JSON manifest is the contract between the ingestion layer and the export layer
- Manifests must be human-readable and auditable before any Cypher is generated
- Manifests are versioned (`version` field on `Manifest` model)

### Connectionless Exporters
- Exporters read from manifest files only — no database connections, no network calls
- This enables use in air-gapped / restricted environments
- Cypher files are numbered and sequenced: `01_constraints.cypher`, `02_nodes.cypher`, `03_relationships.cypher`

---

## URI Convention

All nodes in the graph are identified by a stable, hierarchical URI:
```
{layer_prefix}/{table_name}          # Table node
{layer_prefix}/{table_name}/{column} # Column node
transformation/{script_stem}          # Transformation node
unresolved/{script_name}/{asset}      # UnresolvedAsset node
```
- URIs are always **lowercase**
- URIs are constructed at discovery time and must remain stable across runs

---

## Confidence & Origin Tracking

Every relationship carries `origin` and `confidence`:
- `origin`: `"DDL"` (1.0), `"HEURISTIC"` (0.8), `"ALATION"` (explicit)
- `confidence`: float 0.0–1.0
- Heuristic relationships must never silently overwrite DDL relationships

---

## UnresolvedAsset Pattern

When a SQL reference cannot be resolved to a known URI:
- Create an `UnresolvedAsset` node rather than silently dropping the relationship
- URI format: `unresolved/{script_name}/{asset_name}`
- Label as `:UnresolvedAsset:Transformation`
- Set `unresolved=true` property
- This is the "Data Debt" tracking mechanism — don't shortcut it

---

## Data Models (Pydantic)

- All models in `models/manifest.py` (or equivalent per project)
- Use `pydantic.BaseModel` with explicit field types — no untyped `dict` fields for core data
- Flexible/unknown fields go in `custom_properties: Dict[str, Any] = {}`
- `origins: List[str]` on both tables and columns — always a list, never a single string
- Sample data stored as `List[Dict[str, Any]]` — the 3:5 sampler ratio (3 dense rows, 5 diverse column values)
- Use `Literal["DDL", "HEURISTIC", "ALATION"]` for constrained string fields where applicable
- `Optional[str] = None` for nullable fields, not `str | None` (keep Pydantic v2 compat clean)

---

## TypeMapper Convention

- `TypeMapper.get_full_metadata(native_type, col_name)` returns `{"common_type", "semantic_type", "pii"}`
- Waterfall mapping: DDL native type → common type → semantic type (via column name regex)
- PII flagging is automatic via column name patterns (email, ssn, phone, etc.)
- Always pass both `native_type` AND `col_name` — semantic/PII detection depends on column name
- TypeMapper is injected as a dependency into engines, never instantiated deep in call stacks

---

## DataSampler Convention (3:5 Ratio)

- 3 "Golden Records" = densest rows (most non-null fields)
- 5 "Diverse Samples" per column = highest variance values
- `analyze_table_assets(df, t_samples=2, c_samples=5, max_rows=1000)` — standard call signature
- `max_rows=1000` default scan window — never load entire files into memory
- Output: `{"table_samples": [...], "columns": {col_name: {"samples": [...], "allowed_values": [...]}}}`

---

## What NOT to Do (Manifest Analyzer)

- **Don't** add live database connections to extractors or parsers
- **Don't** silently drop unresolved references — use the UnresolvedAsset pattern
- **Don't** hardcode URIs — always construct from `uri_prefix` + table/column name
- **Don't** let heuristic relationships overwrite DDL relationships
- **Don't** skip `origin` and `confidence` on any relationship
- **Don't** use a single string for `origins` — it's always a list
