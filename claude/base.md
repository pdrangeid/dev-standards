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
   `logging.getLogger(__name__)` from a module inside `lifeos_mcp/` satisfies
   this. The root segment is a durable identifier — renaming it is a breaking
   change requiring a graph migration, the same as renaming a node label.
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
   `[INFO] lifeos_mcp.tools.ingest: SUMMARY nodes=412 rels=1180 status=partial`.
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

---

## Documentation Currency

Claude should treat `README.md` and `ARCHITECTURE.md` as live artifacts,
not one-time scaffolding. After any session that produces:

- A working new module or command
- A validated MVP or end-to-end flow
- A significant refactor that changes how components interact
- A new CLI argument, config key, or output format

...Claude should pause before closing the session and ask:

  "We just got X working. Want me to update README.md / ARCHITECTURE.md
   to reflect this before we close out?"

### What to check when updating
- README Quick Start — does the example command still work as written?
- README Workflow section — does it reflect current pipeline steps?
- ARCHITECTURE.md Data Flow — does the diagram match current reality?
- ARCHITECTURE.md Component table — any new modules to add?
- `docs/usage_instructions.md` — any new flags, args, or config keys?

### What NOT to do
- Don't prompt after every small change — only after validated, working functionality
- Don't rewrite sections that are still accurate
- Don't update docs speculatively for features not yet working
- Don't ask mid-session — wait until the user signals something is working

---

## Session Close Checklist

When a user signals they're done for the session (e.g. "ok that's good for now",
"let's stop here", "committing this"), Claude should quickly check:

1. Were any docs updated to match what was built? If not, offer to do it now.
2. Are there any deferred decisions or known issues worth noting somewhere?
3. Have any new dependencies been added that need updating in `pyproject.toml`?
4. Is there anything that should be committed that hasn't been?

Keep this lightweight — one short prompt, not an interrogation.

---

## Working Conventions (Claude Collaboration)

### Tooling
- **Preferred**: Claude Code (CLI) for active coding sessions — direct filesystem
  access, no upload/download cycle
- **Fallback**: Upload files to chat for review; produce complete ready-to-save
  files in response (not diffs) for any change larger than ~10 lines
- **VSCode** is the primary editor; GitHub for all repos

### Session Continuity
- `AGENTS.md` is the shared contract across sessions — read it at the start of
  every new coding session before touching any code
- If a parallel session produces new conventions, update `AGENTS.md` before
  continuing in other sessions to prevent drift

### GitHub Workflow
- Standard branch-per-feature workflow
- `main` is stable; `develop` is integration; feature branches for all active work
- Update `ARCHITECTURE.md` when module boundaries change significantly —
  don't let it drift from reality
- Claude Code commits freely on feature/* and develop branches
- Merge to main is always a deliberate human action — never ask
  Claude Code to merge or push to main
- Use --no-ff merges to preserve branch history
- Tag main after merging a completed feature or version
- Claude Code should always commit before ending a session

---

## What NOT to Do (Base Rules)

- **Don't** use `print()` — use logger or rich console
- **Don't** hardcode paths, credentials, or environment values in source code
- **Don't** re-read config on every function call — load once at startup
- **Don't** produce diff-style patches for changes — always produce complete files
- **Don't** let `README.md` or `ARCHITECTURE.md` drift from what the code actually does

---

## Session Management

### The `.session/` Directory

Every project contains a `.session/` directory for structured Claude Code session files.
This is the bridge between architecture/planning sessions (Claude web) and
implementation sessions (Claude Code).

```
.session/
├── _template.md                  # canonical template — do not edit, copy to create sessions
├── specs/                        # durable, promoted decisions (always tracked)
│   └── [topic]-baseline.md       # locked architectural decisions, schemas, contracts
└── YYYY-MM-DD-[topic].md         # active or archived session files (tracked)
```

### Starting a Claude Code Session

At the start of every session, before touching any code:

1. Read `AGENTS.md` (always)
2. Check for a session file: `ls .session/` — if a dated `.md` file exists and is `Status: active`, read it
3. Read any `specs/` files referenced in the session file
4. Confirm your understanding of the **Goal** and **Constraints** before proceeding

If no session file exists, ask the user if there's a session to load or proceed with
their in-chat instructions.

### During a Session

- Append decisions, discoveries, and deviations to `## Decisions Made This Session`
- If a constraint or out-of-scope boundary is hit, surface it explicitly rather than silently working around it
- Do not modify `_template.md` — copy it, rename it, then edit the copy

### Closing a Session

When the user signals the session is complete:

1. Update `Status:` to `complete` in the session file
2. Identify any decisions that should be promoted to `specs/` or `AGENTS.md`
3. Offer to move durable decisions to the right location
4. **Update `AGENTS.md`:**
   - Append a one-paragraph entry to the **Review Log** covering what was built,
     what changed, and any bugs fixed
   - Update **Next Steps** to reflect current state — remove completed items,
     add newly unblocked ones
   - Update **Technical Debt** if new deferred items were identified
5. Follow the standard Session Close Checklist (docs, deps, commit)
6. if the  `### Review Log` section of `AGENTS.md` exceeds 10 entries, archive all but the 5 most recent to `/CHANGELOG.md` (append, don't overwrite), then remove the archived entries from `AGENTS.md`

> `AGENTS.md` must be updated in the same commit as the session file closure.
> It is the living contract read at the start of every future session — if it
> drifts, every subsequent session starts with stale context.

### Authoring Workflow

Session files are typically drafted in Claude web and dropped into `.session/` before
a Claude Code session begins. The standard handoff:

1. Claude web session → produces `.session/YYYY-MM-DD-topic.md`
2. File dropped into repo
3. Claude Code session: `"Read .session/2025-04-24-topic.md and proceed"`

This keeps planning and implementation cleanly separated while maintaining a full
decision audit trail in version control.