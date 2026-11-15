# Claude Standards: Base Python Conventions

This file encodes universal patterns and conventions for all Python projects
in this ecosystem. It is auto-fetched by `setup-project.sh` and `refresh-dev-standards.sh`.

---

## Language & Runtime

- **Python ≥ 3.11** (use match statements, `X | Y` union types, `tomllib`, etc. freely)
- **Project config**: `pyproject.toml` only — no `setup.py`, no `setup.cfg`
- **Formatter**: `black` (line length 88)
- **Linter**: `ruff` (rules: E, F, W, I, UP, B)
- **Testing**: `pytest` with `pytest-cov`; test files in `tests/`, named `test_*.py`

---

## Package Management

- `uv` is the preferred package manager and script runner for all projects
- Always document `uv` invocations first in README and usage docs:
  ```sh
  # Preferred
  uv run python -m <package>.main <command> --debug

  # Fallback (traditional venv activated)
  python -m <package>.main <command> --debug
  ```
- Install dependencies with `uv pip install -e .[dev]` — not bare `pip install`
- Use `uv venv` for environment creation — not `python -m venv`
- `uv run` does not require activating the venv — prefer it for one-off execution
- Legacy projects using `argparse` should migrate to `typer` when next significantly touched

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
  - `⚠️` warning (via `logger.warning`)

Example invocation pattern (always document in README):
```sh
uv run python -m <package>.main <command> --flag value --debug
```

---

## Logging

- Use `logging.getLogger(__name__)` at module level for all modules
- Use `logging.getLogger("ClassName")` inside classes
- `--debug` flag sets `logging.DEBUG`; default is `logging.INFO`
- `logger.info()` for significant discoveries and milestones
- `logger.debug()` for detail-level tracing and fallback logic
- `logger.warning()` for skipped entries, unresolved references, non-fatal issues
- `logger.error()` for failures — always include context: `f"Failed to process {item}: {e}"`
- Never use `print()` for logging — use rich console for user output, logger for diagnostics

---

## Logging Contract (Inter-Tool)

Any tool whose stdout/stderr is captured to a log file that another tool parses
must satisfy these five rules. They are a **machine-parse contract, not a style
guide** — `lifeos-jobwatch` reads the four nightly cron logs into a run/issue
model and its parser depends on them. Rules 1 and 5 exist because of specific
measured fragility; see
`lifeos-jobwatch/.session/2026-09-02-jobwatch-pre-freeze-golden-census-logging-contract.md`.

1. **Root logger name equals the distribution package name, with underscores.**
   `logging.getLogger(__name__)` from a module inside `lifeos_synaptex/` satisfies
   this. The root segment is a durable identifier — renaming it is a breaking
   change requiring a graph migration, the same as renaming a node label.
   The procedure (re-key job telemetry in place with jobwatch's
   `scripts/migrate_package_rename.py` before the next nightly emit) is in
   `lifeos-jobwatch/.session/specs/adr/0001-rekey-telemetry-on-package-rename.md`.
2. **Every scheduled job runs under the `run_uv_script.sh` wrapper**, so its log
   carries `>>> Executing <script> at <when>` and
   `<<< Finished <script> rc=<n> duration_sec=<n> at <when>`. The footer is
   authoritative for run status and makes per-job terminator markers unnecessary.
3. **Level semantics.** `WARNING` = degraded but the run continues.
   `ERROR` = a unit of work failed. `CRITICAL` / uncaught = the run is dead.
   These drive `warn_count` / `error_count` and downstream event caps (ERROR is
   never capped), so inflating a warning to an error has direct graph cost.
4. **Timestamp format is `%Y-%m-%d %H:%M:%S,%f`, host-local**, matching the
   current `PYLOG` grammar. Structured / JSON logging is a welcome future change
   but is a new parse branch, not a drop-in — coordinate it with the consuming
   tool.
5. **Any rich summary table must be accompanied by a plain log line carrying the
   same values**, e.g.
   `[INFO] lifeos_synaptex.tools.ingest: SUMMARY nodes=412 rels=1180 status=partial`.
   Box-drawing table parsing is the most fragile path in a log reader and is
   often the only structured-data path out of these tools — a redundant text
   line demotes it from load-bearing to convenience. This is the single
   highest-value rule in the list.

---

## Error Handling

- Never let a single bad record crash the whole run — catch, log, continue
- Collect and surface skipped/failed items at the end of a run — never silently drop them
- Fallback chains: try clean path first, then defensive fallbacks; log each fallback at `debug` level
- Defensive attribute access on objects with variable structure:
  prefer `getattr(obj, 'attr', None)` over direct attribute access

---

## File & Directory Structure

```
<project_name>/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md              # Required for all projects
├── AGENTS.md                    # Auto-generated standards + Project-Specific section
├── CLAUDE.md                    # Bridge stub — `@AGENTS.md` import + Claude Code section
├── requirements.txt             # Pinned runtime deps (generated)
├── requirements-dev.txt         # Points to pyproject.toml dev extras
├── <package_name>/
│   ├── __init__.py
│   └── main.py                  # CLI entry point (typer app)
├── config/
│   └── config.yaml              # Primary project config
├── docs/
│   └── usage_instructions.md
├── tests/
│   └── data/                    # Test fixtures
└── output/                      # Generated artifacts (gitignored)
```

---

## Configuration Conventions

- All project configuration lives in `config/` — never hardcode paths,
  credentials, or environment-specific values in source code
- Credentials exclusively via `.env` (gitignored) — always provide `.env.example`
- A `config.yaml` (or project-named equivalent) is the primary config file,
  loaded at startup via a dedicated `config.py` module
- Never load config inline in business logic — always via `config.py`
- `config.py` is the only module that reads `.env` and YAML —
  everything else receives config as parameters
- Config should be loaded once at startup and passed down —
  not re-read on every function call

---

## Documentation Standards

- Every project must have:
  - `README.md` with Quick Start showing the core workflow with example CLI invocations
  - `ARCHITECTURE.md` explaining design philosophy, data flow, and component responsibilities
- `ARCHITECTURE.md` must include a component table: Component | Responsibility | Key Logic
- Inline docstrings on all public methods — one-liner minimum, full docstring for complex logic
- Complex fallback logic should have inline `logger.debug()` comments explaining
  *why* each fallback exists, not just what it does

