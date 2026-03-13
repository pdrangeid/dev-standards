# Claude Module: Neo4j / Graph Standards

Cypher generation conventions, node/relationship vocabulary, MERGE patterns, and
constraint management for all projects that write to or read from Neo4j.

---

## Cypher Generation Standards

- All MERGE statements must be **idempotent** — use `MERGE`, never `CREATE` for nodes that may already exist
- Property setting pattern:
  ```cypher
  MERGE (n:Label {uri: 'uri_value'})
  ON CREATE SET n.name = 'name', n.first_seen = datetime('...')
  ON MATCH SET n.last_verified = datetime('...')
  SET n.property = 'value';
  ```
- All string values escaped via `_escape()` — never f-string raw user data directly into Cypher
- Timestamps: always use `datetime('ISO8601_STRING')` format, UTC
- Session timestamp passed into exporter at construction time — never generated mid-export
- Constraint file (`01_constraints.cypher`) always runs first and is idempotent
- Use `IF NOT EXISTS` on all `CREATE CONSTRAINT` and `CREATE INDEX` statements

### Cypher File Sequencing
Cypher output files are numbered and sequenced:
```
01_constraints.cypher
02_nodes.cypher
03_relationships.cypher
```

---

## Node Labels (Layer-Aware)

Tables and Columns carry a layer label in addition to their base label:
```
:Table:DWElement, :Table:SourceElement, :Table:BIElement
:Column:DWElement, etc.
```
Layer map: `DW` → `DWElement`, `SOURCE` → `SourceElement`, `BI` → `BIElement`, `LINEAGE` → `LineageElement`

---

## Relationship Types (Standard Vocabulary)

```
HAS_COLUMN, ORIGINATED_FROM, BELONGS_TO, MANAGED_BY, CLASSIFIED_AS
REFERENCES, JOINS_TO, INPUT_TO, PRODUCES
HAS_DATATYPE, REPRESENTS (column → SemanticType or BusinessTerm)
```
Do not invent new relationship types without documenting them here.

---

## What NOT to Do (Neo4j)

- **Don't** use `CREATE` for nodes that may already exist — always `MERGE`
- **Don't** f-string user data directly into Cypher — always use `_escape()`
- **Don't** generate timestamps inside loops — pass session timestamp in at construction time
- **Don't** run constraint files out of order — `01_constraints.cypher` must always run first
- **Don't** add new relationship types without updating the vocabulary above
