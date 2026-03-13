# Claude Module: Strategic Exporter (Live Exporter)

Conventions for the strategic exporter — the only tool in the ecosystem with a
live Neo4j connection. Driver management, config architecture, export profiles,
amplifier payload, GraphSchema/SchemaElement, backup/restore, tier detection,
and Lesson logging.

---

## Strategic Exporter Overview

The strategic exporter differs from the analyzer tools in one critical way: **it has a live Neo4j connection**. It is the only tool in the ecosystem that does. All conventions below apply specifically to this project.

---

## Driver & Session Management

- Use `get_driver()` from `utils.py` — never instantiate `GraphDatabase.driver()` directly in business logic
- Pass the driver into functions; let them manage their own sessions with `with driver.session() as session:`
- Never share sessions across major operations — open a new session per logical unit of work
- Always close drivers that are opened locally: use the `close_driver_after` pattern
  ```python
  close_driver_after = False
  if driver is None:
      driver = get_driver()
      close_driver_after = True
  try:
      ...
  finally:
      if close_driver_after and driver:
          driver.close()
  ```
- `diagnostic_mode.py` anti-pattern: calling `driver.close()` at the end of `run_diagnostic_export()` when the driver was passed in — **don't close drivers you didn't open**

---

## Configuration Architecture

- All config loaded from `config/strategicexporter.yaml` via `config.py` — never hardcode paths or connection strings
- DB credentials exclusively from `.env` via `python-dotenv` — key pattern: `NEO4J_USER_{PROFILE_NAME_UPPER}` / `NEO4J_PASSWORD_{PROFILE_NAME_UPPER}`
- Multi-environment support via named connection profiles in YAML (`lifeos`, `sandbox_bethegraph`, `pc_desktop`, etc.)
- `SELECTED_DB_CONNECTION_NAME` is a module-level global set at CLI parse time via `set_selected_db_connection()` — this is intentional for the single-process CLI model
- `make_output_path(filename, subdir_key=None)` resolves all output paths — never construct output paths manually

---

## Export Profile System

- Export behavior is driven by JSON operation profiles in `export-profiles/`
- Profile fields: `profile_name`, `profile_mode` (`amplifier` | `diagnostic` | `snapshots`), `filters`, `sections`, `description`
- Export types: `Amplifier` (full payload for LLM), `diagnostic` (section-scoped node query), `snapshots` (static Cypher queries)
- `--operation-profile` CLI arg loads the profile; `--export-type` can override the inferred type
- Profile `filters` keys: `node_labels` (list), `relationship_types` (list) — used to scope schema generation

---

## Amplifier Payload Structure

The `amplifier_payload.json` is the core LLM-consumable artifact. Its schema must remain stable:
```json
{
  "schema": {
    "node_labels": [],
    "relationship_types": [],
    "property_keys": [],
    "label_property_map": {},
    "graph_schema_contract": [],
    "schema_element_has_schema_links": [],
    "node_counts": [],
    "indexes": [],
    "constraints": []
  },
  "sample_queries": {},
  "agent_behavior_map": {},
  "environment": { "inferred_tier": "", "platform_source": "" },
  "meta": { "export_date": "", "notes": "" }
}
```
- `graph_schema_contract` = records from `:GraphSchema` nodes — the binding schema contract for agents
- `sample_queries` = `{label_lower}_summary` keys with up to 250 representative node display values
- `agent_behavior_map` = built from `:SchemaElement` nodes — do not generate ad hoc

---

## GraphSchema & SchemaElement Pattern

This is the schema governance layer — understand it before modifying schema-related code:
- `:GraphSchema` nodes are the **schema contract** — one per node label and relationship type
  - Key properties: `labelName`, `elementType` ('label'|'relationship'), `displayProperty`, `primaryKeyProperty`, `isPrimaryKeyConstrained`
  - Default `displayProperty`: `"name"`, default `primaryKeyProperty`: `"uuid"`
- `:SchemaElement` nodes are the **live registry** of what actually exists in the graph
  - Linked to `:GraphSchema` via `[:HAS_SCHEMA]`
  - Created/managed by `schema_linker.main()`
- Run order matters: `schema_generator.main()` → `schema_linker.main()` → `build_amplifier_payload()`
- `patch_graphschema_integrity()` is a safety net — fills in null `displayProperty`/`primaryKeyProperty` — run it as part of schema generation, not as a workaround

---

## Backup & Restore

- APOC-based export — requires APOC plugin on Neo4j instance
- Always prepend `CREATE CONSTRAINT UNIQUE_IMPORT_NAME IF NOT EXISTS...` before restored data
- Always append `CALL db.awaitIndexes(300);` after schema statements
- Stub pattern: labels listed in `stub_node_and_properties` config are converted to lightweight stub nodes rather than fully exported — preserves graph connectivity without exporting large/complex payloads (e.g., `_Neodash_Dashboard`)
- `excluded_node_labels`: completely omitted from export — no stubs
- Path templates use `${backup_dir}`, `${source_profile}`, `${timestamp}` substitutions

---

## Tier Detection

- `tier_detector.detect_tier(session)` infers Neo4j environment (aura_free / aura_professional / aura_enterprise_or_self_hosted)
- Uses memory config heuristics; falls back gracefully when `dbms.listConfig()` is restricted (Aura Free)
- Always inject tier info into `payload["environment"]` — agents use this to calibrate query complexity

---

## LLM Prompt Management

- Prompts stored as `.txt` files in `prompts/agent_bootstrap/` and `prompts/operational/`
- Prompts are versioned via SHA-256 hash (`PromptHash`) tracked in the graph as `:Prompt` nodes
- `meta_injector.py` handles registering/updating prompt nodes — don't bypass it for prompt updates
- Prompt drift detection: if a prompt file's hash doesn't match the graph-recorded hash, it's flagged
- The `llm_amplifier_prompt.txt` and `python_dev_prompt.txt` are always written to the export bundle

---

## Lesson Logging Protocol (Graph-Native)

When a meaningful architectural or process insight occurs during a session, it should be logged to the graph. This is a first-class convention, not optional:
```cypher
WITH date() AS today, datetime().epochMillis AS nowMillis
MERGE (s:Session {date: today})
MERGE (l:Lesson {
    title: "<Short Lesson Title>",
    domain: "<Domain>",
    created: today,
    createdEpochMillis: nowMillis
})
SET l.description = "<Single-line description with \\n for breaks>"
MERGE (l)-[:LEARNED_DURING]->(s)
```
- Domain values follow agent/module names: `"Strategic Exporter"`, `"Cypher Authoring"`, `"GraphOps"`, `"Agent Orchestration"`
- Always prompt: *"Shall I log a Lesson?"* when a non-trivial insight emerges
- Session node should also be updated with `actionsTaken` and `achievements` arrays

---

## Additional Node Labels (Strategic Exporter Graph)

Beyond the datasource-analyzer labels, this graph uses:
```
:GraphSchema, :SchemaElement, :Prompt, :Session, :Lesson
:AgentSession, :BackupSession, :BusinessTerm
```
Relationship types specific to this project:
```
HAS_SCHEMA (SchemaElement → GraphSchema)
LEARNED_DURING (Lesson → Session)
USED_DURING (Prompt → AgentSession)
USES_PROMPT, HASHED_AS
```

---

## Module Structure (Target Refactor)

The refactor drives modularity and clear separation of concerns:
```
strategic_exporter/
├── export_runner.py          # Orchestrator ONLY — wiring, no business logic
├── amplifier_builder.py      # build_amplifier_payload() lives here
├── schema/
│   ├── schema_generator.py   # Ensures :GraphSchema nodes exist
│   ├── schema_linker.py      # SchemaElement ↔ GraphSchema linking
│   └── schema_mapper.py      # NEW — semantic schema mapping
├── graph_management/
│   └── backup_restore.py
├── diagnostics/
│   └── diagnostic_mode.py
├── meta_injector.py
├── tier_detector.py
├── queries.py
├── config.py
└── utils.py
```

Key refactor rules:
- `export_runner.py` must import and call — never define logic inline
- Each module owns one concern and can be tested independently
- Module-level mutable state (`nodes_cypher = []`) must be eliminated — all state on instances
- `build_amplifier_payload()` should accept a fully-built `schema_dict` rather than re-running discovery internally

---

## What NOT to Do (Strategic Exporter)

- **Don't** close a driver you didn't open — check `close_driver_after` pattern
- **Don't** hardcode Neo4j URIs or credentials — always use YAML config + `.env`
- **Don't** construct output paths manually — always use `make_output_path()`
- **Don't** modify `:GraphSchema` nodes ad hoc — use `schema_generator` and `schema_linker` modules
- **Don't** skip the `schema_generator.main()` → `schema_linker.main()` sequence before building amplifier payloads
- **Don't** add new agent behavior logic to `export_runner.py` — it's an orchestrator only; logic belongs in dedicated modules
- **Don't** add new keys to `amplifier_payload.json` schema without updating the structure doc above
- **Don't** bypass `meta_injector.py` when updating prompt files — hash drift will be flagged
- **Don't** write Cypher directly into `export_runner.py` — Cypher belongs in `queries.py` or a dedicated module
