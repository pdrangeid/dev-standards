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
| `typer` | CLI entry points |
| `rich` | Console output, progress, logging display |

- Always pin with `>=` lower bounds, not `==` exact pins (unless a breaking change requires it)
- Dev extras in `[project.optional-dependencies] dev = [...]` — never in main `dependencies`

---

## CLI Conventions (Typer)

- One `typer.Typer()` app per project, in `main.py`
- Commands should be named for their action (verbs: `run`, `export`, `analyze`, `scan`)
- Use `--debug` flag on all commands; wire it to `logging.setLevel(logging.DEBUG)`
- Use `rich` console for all user-facing output — not bare `print()`
- Register all commands in `pyproject.toml` under `[project.scripts]`
- Emoji status indicators in console output:
  - `✅` success / completion
  - `🔍` discovery / scanning
  - `✨` new discovery / heuristic match
  - `🔗` relationship found
  - `🌿` enrichment
  - ⚠️ warning (via `logger.warning`)
  

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

- Never let a single bad record crash the whole run — catch, log, continue
- Log failures at `logger.error()` with context: `f"Failed to process {item}: {e}"`
- Collect and surface skipped/failed items at the end of a run — never silently drop them
- Fallback chains: try clean path first, then defensive fallbacks; log each fallback at `debug` level
- Defensive attribute access on objects with variable structure: prefer `getattr(obj, 'attr', None)` over direct access

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
├── tests/
├── output/                  # Generated manifests or other exports or results (gitignored)
└── test/data/               # Test fixtures (DDL, CSV, JSON)
```

---

## Documentation Standards

- Every project must have:
  - `README.md` with Quick Start showing all three pipeline stages with example CLI invocations
  - `ARCHITECTURE.md` explaining the design philosophy, data-flow and component responsibilities
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
3. Have we added any modules that should be added to requirements.txt or requirements-dev.txt or pyproject.toml
4. Is there anything that should be committed that hasn't been?

Keep this lightweight — one short prompt, not an interrogation.

---

## Working Conventions (Claude Collaboration)

### Tooling
- **Preferred**: Claude Code (CLI) for active coding sessions — direct filesystem access, no upload/download cycle
- **Fallback**: Upload files to this chat for review/analysis; produce complete ready-to-save files in response
- **VSCode** is the primary editor; GitHub for all repos
- Always produce complete files, not diff-style patches, for any change larger than ~10 lines

### Testing Environment
- Never hardcode connection details — always use the profiles system in a relevant yaml file in /config

### Session Continuity
- This `claude.md` is the shared contract across sessions — reference it at the start of any new coding session
- If a parallel session (e.g., schema mapper overhaul) produces new conventions, update this file before continuing in other sessions

### GitHub Workflow
- Standard branch-per-feature workflow assumed
- `main` / `master` is stable; feature branches for all active work
- Update `ARCHITECTURE.md` when module boundaries change significantly — don't let it drift from reality

---

## Configuration Conventions

- All project configuration lives in `config/` — never hardcode paths, 
  credentials, or environment-specific values in source code
- Credentials exclusively via `.env` (gitignored) — always provide `.env.example`
- A `config.yaml` (or project-named equivalent) is the primary config file,
  loaded at startup via a dedicated `config.py` module (if required)
- Never load config inline in business logic — always via a dedicated `config.py`
- `config.py` is the only module that reads `.env` and YAML — 
  everything else receives config as parameters
- Config should be loaded once at startup and passed down — 
  not re-read on every function call
---

## What NOT to Do (Base Rules)

**All analyzers / datasource-graph-analyzer:**

- Don't use `print()` — use logger or rich console
- Don't hardcode paths, credentials, or environment values in source code
- Don't re-read config on every function call — load once at startup