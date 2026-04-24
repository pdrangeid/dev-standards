# Claude Module: Neo4j / Graph Standards

Cypher generation conventions, MERGE patterns, CALL {} rules, APOC conventions,
and constraint management for all projects that write to or read from Neo4j.

---

## Shared Neo4j Library — lifeos-neo4j

All lifeos projects that require a Neo4j connection must import from
`lifeos-neo4j` rather than implementing their own connection management.
This is the single source of truth for driver creation, profile loading,
capability detection, and ConnectionContext.

### Adding the dependency

In `pyproject.toml`:
```toml
[project]
dependencies = [
    "lifeos-neo4j @ file://../../packages/lifeos-neo4j",
    # adjust relative path based on project location
]
```

For projects outside the lifeos monorepo structure, use an absolute path
or a git reference once lifeos-neo4j is published:
```toml
"lifeos-neo4j @ git+https://github.com/pdrangeid/lifeos-neo4j@main"
```

### Public API
```python
from lifeos_neo4j.connection import (
    get_driver,           # raw Driver for simple cases
    get_context,          # ConnectionContext — preferred for most use
    get_default_kg_context,   # reads schemata.default_kg_profile
    get_default_meta_context, # reads schemata.default_meta_profile
)
from lifeos_neo4j.capability_detector import detect_capabilities, CapabilityProfile
from lifeos_neo4j.profiles import load_profiles
```

### ConnectionContext

Prefer `get_context()` over `get_driver()` — it carries `driver`,
`database`, and `profile_name` together so callers don't have to
track them separately:
```python
ctx = get_context("lifeos-kg", config_path)

# Capability detection is explicit and optional — not forced at construction
ctx.capabilities = detect_capabilities(ctx.driver, ctx.database)

# Use in session
with ctx.driver.session(database=ctx.database) as session:
    ...
```

### close_driver_after pattern

Any function that accepts an optional ConnectionContext must follow
this pattern — never close a context you didn't create:
```python
def my_operation(ctx: ConnectionContext | None = None) -> None:
    close_ctx_after = ctx is None
    if ctx is None:
        ctx = get_context("lifeos-kg", config_path)
    try:
        with ctx.driver.session(database=ctx.database) as session:
            ...
    finally:
        if close_ctx_after:
            ctx.driver.close()
```

### Integration testing

All projects using lifeos-neo4j follow the same integration test convention:

- Config: `~/.lifeos/test-profiles.yaml` — machine-local, never committed
- Credentials: `.env` in project root — `NEO4J_USER_TEST_NEO4J` / `NEO4J_PASSWORD_TEST_NEO4J`
- Skip condition: test skips gracefully if config or credentials absent
- `conftest.py` must call `load_dotenv()` before collection to ensure
  env vars are available at skipif evaluation time
```python
# tests/conftest.py
from dotenv import load_dotenv
load_dotenv()
```

## Cypher Generation Standards

- All MERGE statements must be **idempotent** — use `MERGE`, never `CREATE` for nodes that may already exist
- Property setting pattern:
  ```cypher
  WITH $session_timestamp AS now
  MERGE (n:Label {id: 'uid_value'})
  ON CREATE SET n.name = 'name', n.createdEpochMillis = now, n.createdDatetime = datetime(now)
  ON MATCH SET n.modifiedEpochMillis = now, n.modifiedDatetime = datetime(now)
  SET n.property = 'value';
  ```
- All string values escaped via `_escape()` — never f-string raw user data directly into Cypher
- Timestamps: use `datetime('ISO8601_STRING')` format, UTC by default
- Ensure consistant timestamps (by generating in python when practical - or top of cypher if inline) avoid generated transactionally (unless context demands granularity)
- Use `IF NOT EXISTS` on all `CREATE CONSTRAINT` and `CREATE INDEX` statements
- Use `ON CREATE SET` / `ON MATCH SET` to separate immutable and updateable fields
- Always use `WITH` between `MERGE` → `MATCH` transitions to preserve scope
- When using multiple `WITH` clauses inside a subquery, carry forward all required
  external variables through every transition
- Semicolon-separate multi-statement blocks — variables do not carry between them
- All nodes should contain `createdEpochMillis` and `createdDatetime`; on update also
  `modifiedEpochMillis` and `modifiedDatetime` — omit only when a downstream importer
  handles timestamp assignment (e.g., manifest-style Cypher output)
- Use `IS NULL` instead of `exists(n.prop)` — `exists()` is deprecated in Neo4j 5.x
- If `"parameterized": false` is present in the request, use literal values instead of
  `$parameters` — enables compatibility with Neo4j Browser and schema illustration.
  Default is parameterized unless explicitly disabled.
- Never MERGE on nullable or optional properties — use a reduced stable key set in the
  MERGE predicate; apply optional/nullable fields via `SET` after the MERGE
- When setting string properties, do not use Python-style triple quotes (`"""`).
  Escape line breaks using `\n` within a standard quoted string.
- Never use bare `print()` — always wrap Cypher output in triple backticks.
  Do not add explanation or preamble unless asked.

---

## CALL {} Subquery Rules

- Never use `CALL () {}` at the top level — embed inside a parent query or eliminate entirely
- Use `CALL () {}` only when variable continuity across semicolons is genuinely required
- Pass external variables explicitly in the call signature: `CALL (var1, var2) { ... }`
- Semicolons are not allowed inside a `CALL () {}` block
- After `CALL () {procedure} YIELD ...`, you must `RETURN` yielded variables before `ORDER BY`
- Never place a `WITH` clause immediately after a semicolon outside a `CALL {}` block —
  this throws a syntax error. Always restart as a valid standalone query or use `WITH *`

---

## Relationship Type Governance

- Never invent new relationship types ad hoc — define them explicitly before use
- Relationship type names: `SCREAMING_SNAKE_CASE`, verb-phrase describing direction
  (e.g. `HAS_COLUMN`, `BELONGS_TO`, `LEARNED_DURING`)
- Document all relationship types used by this project in `## Project-Specific`
- Document all node labels used by this project in `## Project-Specific`

---

## APOC Conventions

### Date Math
- `apoc.date.add` requires epochMillis input — convert native `date()` types first
  using `datetime().epochMillis` before passing to any APOC date math
- Supported units: `ms`, `s`, `m`, `h`, `d` — weeks and months are **not** supported
- On Aura, native date types must be explicitly converted before any APOC date operation

### Export Strategy
- Use `stream: true` with a null file path for all APOC exports — Python captures
  the stream via the driver and writes locally
- This pattern works across local, Docker, and Aura — no server filesystem dependency
- Use `format: plain` to avoid `:begin` / `:commit` markers that break import scripts
- Always prepend `CREATE CONSTRAINT UNIQUE_IMPORT_NAME IF NOT EXISTS` before import data
- Always append `CALL db.awaitIndexes(300)` after all schema statements
- When splitting multi-statement Cypher for import, never use simple `split(';')` —
  use regex to avoid false splits inside string literals:
  ```python
  re.split(r';(?=\s*($|\n|--|//))', data)
  ```

### Dynamic Queries
- Cypher does not support inline label parameterization — use `apoc.cypher.run()`
  with string interpolation for dynamic label queries:
  ```cypher
  CALL apoc.cypher.run("MATCH (n:" + label + ") RETURN n", {}) YIELD value
  ```
- Before dynamic label loops: `COLLECT(DISTINCT label)` then `UNWIND` — prevents
  scanning the same label multiple times and eliminates downstream duplicates
- Always carry outer loop variables through every `WITH` clause inside nested
  `apoc.cypher.run()` calls — scope is not inherited automatically
- When `CALL apoc.cypher.run(...) YIELD value` returns aliased fields, access them
  via the outermost alias: `WITH value.bar AS myBar` — not `record.get('value.myBar')`

### Data Structures
- Dynamic property names are not supported in literal maps — use `apoc.map.fromPairs()`
  with alternating key-value pairs:
  ```cypher
  apoc.map.fromPairs([key1, val1, key2, val2])
  ```
- Maps cannot be stored directly as node properties — encode as JSON strings and
  parse at runtime:
  ```cypher
  apoc.convert.fromJsonMap(n.property_types)
  ```

---

## What NOT to Do (Neo4j)

- **Don't** use `CREATE` for nodes that may already exist — always `MERGE`
- **Don't** f-string user data directly into Cypher — always use `_escape()`
- **Don't** generate timestamps inside loops — pass session timestamp at construction time
- **Don't** run constraint files out of order — `01_constraints.cypher` must always run first
- **Don't** use `CALL () {}` at the top level of a query
- **Don't** place a `WITH` clause immediately after a semicolon outside a `CALL {}` block
- **Don't** MERGE on nullable properties — use a reduced stable key set
- **Don't** use `exists(n.prop)` — use `n.prop IS NULL` / `n.prop IS NOT NULL`
- **Don't** store maps as node properties — encode as JSON strings
- **Don't** add new relationship types or node labels without documenting them in `## Project-Specific`
- **Don't** implement your own `get_driver()` or profile loader — import from lifeos-neo4j
- **Don't** hardcode Neo4j URIs or credentials anywhere — always profiles + .env
- **Don't** call `detect_capabilities()` inside `get_context()` — capability
  detection is explicit, callers opt in
- **Don't** close a ConnectionContext you didn't create
- **Don't** share sessions across major operations — one session per logical unit of work
- **Don't** store `ConnectionContext` as a module-level global — 
  construct at CLI parse time and pass down
