# Claude Module: Neo4j / Graph Standards

Cypher generation conventions, MERGE patterns, CALL {} rules, APOC conventions,
and constraint management for all projects that write to or read from Neo4j.

---

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
- Session timestamp passed into exporter at construction time — never generated mid-export
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
