# Claude Standards: Base Python Conventions

This file encodes universal patterns and conventions for all Python projects
in this ecosystem. It is auto-fetched by `setup-project.sh` and `refresh-claude.sh`.

---

## Project Ecosystem Overview

These tools form a **Manifest-First, graph-generation pipeline**:

```
[Analyzers / Parsers]
    ↓  JSON Manifest (Source of Truth)
[Strategic Exporter / Schema Mapper]
    ↓  Cypher (.cypher files) + LLM-ready analysis
[Neo4j Knowledge Graph]
```

Each project is a **connectionless, file-in / file-out utility**. No live DB connection is
ever required during extraction or export. This is a core architectural constraint — preserve it.

---

## Language & Runtime

- **Python ≥ 3.11** (use match statements, `X | Y` union types, `tomllib`, etc. freely)
- **Package manager**: `uv` preferred for running scripts (`uv run python -m ...`); `pip` acceptable
- **Project config**: `pyproject.toml` only — no `setup.py`, no `setup.cfg`
- **Formatter**: `black` (line length 88)
- **Linter**: `ruff` (rules: E, F, W, I, UP, B)
- **Testing**: `pytest` with `pytest-cov`; test files in `tests/`, named `test_*.py`

---

## Dependencies (Core Stack)

| Library | Role |
|---|---|
| `pydantic >= 2.x` | All data models / manifests |
| `typer` | CLI entry points |
| `rich` | Console output, progress, logging display |
| `sqlglot` | SQL parsing (DDL, lineage, transformations) |
| `pandas` | CSV/Parquet sampling and profiling |
| `numpy` | Sampling math |

- Always pin with `>=` lower bounds, not `==` exact pins (unless a breaking change requires it)
- Dev extras in `[project.optional-dependencies] dev = [...]` — never in main `dependencies`

---

## CLI Conventions (Typer)

- One `typer.Typer()` app per project, in `main.py`
- Commands: `discover`, `lineage`, `export` (follow this naming convention)
- Use `--debug` flag on all commands; wire it to `logging.setLevel(logging.DEBUG)`
- Use `rich` console for all user-facing output — not bare `print()`
- Emoji status indicators in console output:
  - `✅` success / completion
  - `🔍` discovery / scanning
  - `✨` new discovery / heuristic match
  - `🔗` relationship found
  - `🌿` enrichment
  - ⚠️ warning (via `logger.warning`)
- CLI entry point registered in `pyproject.toml` under `[project.scripts]`

Example invocation pattern (always document in README):
```sh
PYTHONPATH=. uv run python -m <package>.main <command> --flag value --debug
```

---

## Logging

- Use `logging.getLogger(__name__)` at module level for all parsers/engines
- Use `logging.getLogger("ClassName")` inside classes
- `--debug` flag sets `logging.DEBUG`; default is `logging.INFO`
- `logger.info()` for significant discoveries and milestones
- `logger.debug()` for AST node walks, column-level detail, fallback logic
- `logger.warning()` for orphaned entries, unresolved references, skipped nodes
- `logger.error()` for parse failures (always include the exception: `f"Failed to parse {file}: {e}"`)
- Never use `print()` for logging — use rich console for user output, logger for diagnostic output

---

## Error Handling

- Wrap all SQL parse calls in `try/except` — log error and `continue`, never crash the whole run
- Defensive attribute access on AST nodes: always use `hasattr()` or `getattr(node, 'attr', None)` — sqlglot nodes vary by SQL dialect
- Orphaned/unmatched entries (e.g., Alation entries for unknown tables) are collected in `_alation_orphans` and surfaced on the manifest — never silently dropped
- Fallback chains: try the clean path first, then progressively more defensive fallbacks, log each fallback at `debug` level

---

## File & Directory Structure

```
<project_name>/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md          # Required for all projects
├── requirements.txt         # Pinned runtime deps (generated)
├── requirements-dev.txt     # Points to pyproject.toml dev extras
├── <package_name>/
│   ├── __init__.py
│   ├── main.py              # CLI entry point (typer app)
│   ├── models/
│   │   └── manifest.py      # All Pydantic models
│   ├── parsers/             # or services/ — ingestion logic
│   ├── exporters/           # Cypher/output generation
│   └── utils/
│       ├── type_mapper.py   # TypeMapper (waterfall mapping)
│       └── sampling.py      # DataSampler (3:5 ratio)
├── tests/
├── output/                  # Generated manifests and cypher (gitignored)
└── test/data/               # Test fixtures (DDL, CSV, JSON)
```

---

## Documentation Standards

- Every project must have:
  - `README.md` with Quick Start showing all three pipeline stages with example CLI invocations
  - `ARCHITECTURE.md` explaining the manifest-first philosophy and component responsibilities
- ARCHITECTURE.md must include a component table: Component | Responsibility | Key Logic
- Inline docstrings on all public methods — one-liner minimum, full docstring for complex logic
- Complex fallback logic (e.g., AST node extraction) should have inline `logger.debug()` comments explaining *why* each fallback exists, not just what it does

## Documentation Currency

Claude should treat README.md and ARCHITECTURE.md as live artifacts,
not one-time scaffolding. After any session that produces:

- A working new module or command
- A validated MVP or end-to-end flow
- A significant refactor that changes how components interact
- A new CLI argument, config key, or output format

...Claude should pause before closing the session and ask:

  "We just got X working. Want me to update README.md / ARCHITECTURE.md
   to reflect this before we close out?"

### What to check when updating:
- README Quick Start — does the example command still work as written?
- README Workflow section — does it reflect current pipeline steps?
- ARCHITECTURE.md Data Flow — does the diagram match current reality?
- ARCHITECTURE.md Component table — any new modules to add?
- docs/usage_instructions.md — any new flags, args, or config keys?

### What NOT to do:
- Don't prompt after every small change — only after validated, working functionality
- Don't rewrite sections that are still accurate
- Don't update docs speculatively for features not yet working
- Don't ask mid-session — wait until the user signals something is working

---

## Session Close Checklist

When a user signals they're done for the session (e.g. "ok that's good for now",
"let's stop here", "committing this"), Claude should quickly check:

1. Were any docs updated to match what was built? If not, offer to do it now.
2. Are there any known bugs or deferred decisions worth logging to a Lesson node?
3. Is there anything that should be committed that hasn't been?

Keep this lightweight — one short prompt, not an interrogation.

---

## Working Conventions (Claude Collaboration)

### Tooling
- **Preferred**: Claude Code (CLI) for active coding sessions — direct filesystem access, no upload/download cycle
- **Fallback**: Upload files to this chat for review/analysis; produce complete ready-to-save files in response
- **VSCode** is the primary editor; GitHub for all repos
- Always produce complete files, not diff-style patches, for any change larger than ~10 lines

### Testing Environment
- **Local Neo4j**: development and rapid iteration
- **Aura (cloud)**: staging / validation before committing schema or data changes
- Connection profile names to use by convention: `pc_desktop` or `bluegraph` for local, `lifeos` / `auratestgraph` for Aura
- Never hardcode connection details — always use the named profile system in `strategicexporter.yaml`

### Session Continuity
- This `claude.md` is the shared contract across sessions — reference it at the start of any new coding session
- If a parallel session (e.g., schema mapper overhaul) produces new conventions, update this file before continuing in other sessions

### GitHub Workflow
- Standard branch-per-feature workflow assumed
- `main` / `master` is stable; feature branches for all active work
- Update `ARCHITECTURE.md` when module boundaries change significantly — don't let it drift from reality

---

## Cross-Project Standards Summary

| Convention | datasource-graph-analyzer | strategic-exporter | codebase-graph-analyzer |
|---|---|---|---|
| Live DB connection | ❌ Never | ✅ Required | ❌ Never |
| CLI framework | `typer` | `argparse` → migrate to `typer` | `argparse` → migrate to `typer` |
| Config loading | `pyproject.toml` + YAML | YAML + `.env` | YAML + `.env` |
| Output format | JSON manifest + `.cypher` | JSON payload + ZIP | JSON package (nodes + rels) |
| Entity ID separator | `/` (URI-style) | N/A (live graph) | `::` (path::symbol) |
| Python floor | `>=3.11` | `>=3.8` → align to 3.11 | `>=3.11` |
| Logging | `logging` + `rich` | `logging` | `logging` (no rich yet) |

---

## What NOT to Do (Base Rules)

**All analyzers / datasource-graph-analyzer:**
- **Don't** add live database connections to extractors or parsers
- **Don't** use `print()` — use logger or rich console
- **Don't** silently drop unresolved references — use the UnresolvedAsset pattern
- **Don't** hardcode URIs — always construct from `uri_prefix` + table/column name
- **Don't** generate Cypher with unescaped string interpolation — always use `_escape()`
- **Don't** use module-level mutable state for Cypher accumulation (e.g., `nodes_cypher = []` at module level is a known bug — keep state on the instance)
- **Don't** create new relationship type names without adding them to the standard vocabulary
