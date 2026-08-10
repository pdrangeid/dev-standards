<!-- AUTO-GENERATED: base + modules[] -->
<!-- Do not edit above ## Project-Specific — run refresh-dev-standards.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->

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
---

## Project-Specific

> This section is maintained by Claude during coding sessions.
> Run `refresh-dev-standards.sh` to update the auto-generated sections above
> without touching anything below this line.

### Overview

dev-standards is a centralized scaffolding and standards repo for a Python/Neo4j graph analytics
ecosystem. Primary deliverables are two bash scripts and a set of modular AGENTS.md content files:

- `scripts/setup-project.sh` — scaffolds a new Python project (repo, venv, structure, `AGENTS.md` + `CLAUDE.md`)
- `scripts/refresh-dev-standards.sh` — re-fetches base+modules from GitHub and updates downstream `AGENTS.md` files (and self-migrates any legacy `claude.md` project it finds)
- `claude/base.md` + `claude/modules/*.md` — composable standards content fetched at scaffold time
- `project-templates/` — reference templates for pyproject.toml, config.yaml, ARCHITECTURE.md

The Python package (`dev_standards/`) is a stub generated by the scaffold template — it has no
real functionality and is not the actual product of this repo.

### Key Patterns

- `AGENTS.md` composition: `setup-project.sh` fetches base.md + selected modules, appends `## Project-Specific` stub, and generates a `CLAUDE.md` bridge stub (`@AGENTS.md` import) alongside it
- `<!-- AUTO-GENERATED: base + modules[...] -->` header encodes which modules to re-pull on refresh
- `refresh-dev-standards.sh` splits on `## Project-Specific` — everything above is replaceable, below is preserved
- Legacy-state detection: a project with `claude.md` but no `AGENTS.md` (or a `claude.md` header still naming `refresh-claude.sh`) is auto-migrated on the next `refresh-dev-standards.sh` run — see `## Migrating an Older Project` in README.md
- Module selection: interactive menu or `--modules neo4j,live-exporter` flag
- Both scripts default `DEV_STANDARDS_RAW` to the `develop` branch (a `main` URL is built but only used if the `develop` line is commented back out manually) — intentional for now so consumers get in-flight standards updates before they're merged to `main`; no `--branch` flag exists yet (see Recommendations)

### Technical Debt

- `scripts/setup-project.sh:710-716` — module fetch failures in setup-project.sh only warn but don't set `FETCH_FAILED`; scaffold completes with an incomplete `AGENTS.md` and exits 0
- `scripts/setup-project.sh:236` — `git clone ... 2>/dev/null` silently swallows errors; failure and dry-run produce the same message
- `pyproject.toml:38-39` — package name `dev_Standards` (mixed case) doesn't match actual directory `dev_standards/` (lowercase); breaks setuptools on Linux
- `pyproject.toml:18` — `rich>=13.0,<14.0` upper-bound pin contradicts base.md convention (use `>=` lower bounds only)
- `claude/HEADER.md:1` — contains a hardcoded example commit hash (`a3f2c1`) that gets copied literally into the example header shown in that file (not actually used by either script — both scripts build their header inline)
- `dev_standards/claude.md.monolith` and `dev_standards/claude-code-session-starter.md` — historical artifacts in the package directory, predate the `AGENTS.md` migration and still describe the old `claude.md`/`refresh-claude.sh` workflow; should be archived or deleted
- `coverage.xml` and `htmlcov/` are committed to the repo — generated test artifacts, should be gitignored
- `project-templates/ARCHITECTURE.md.template` — pre-fills manifest-analyzer directory structure (models/, parsers/, exporters/), too opinionated for a generic scaffold
- Two template systems exist with no sync mechanism: `project-templates/*.template` (Jinja-style `{{}}`) and heredocs in `setup-project.sh` (bash `${}`) — content has drifted between them
- `refresh-dev-standards.sh`'s migration path only knows about the `claude.md`/`AGENTS.md`/`CLAUDE.md` triplet — a project with an existing symlink pointing at `claude.md` (e.g. a hand-rolled `GEMINI.md -> claude.md`, seen in `datasource-graph-analyzer`) is left dangling after migration and must be repointed manually. Not generalized into the script; worth revisiting if this pattern recurs across more than one or two projects.

### Next Steps

1. **Fix package name casing** in `pyproject.toml` — `dev_Standards` → `dev_standards`; easy fix, prevents import failures on Linux
2. **Decide Python package fate** — either give `dev_standards/main.py` real functionality (e.g., `validate` command to check `AGENTS.md` staleness) or remove the Python scaffolding entirely
3. **Add `coverage.xml`, `htmlcov/`, `.coverage` to `.gitignore`** — already gitignored in generated projects but not here
4. **Move or delete historical artifacts** — `claude.md.monolith` and `claude-code-session-starter.md`
5. **Add bats/shellspec tests** for `--dry-run` mode — the flag exists precisely to enable testability; the migration and idempotency paths in `refresh-dev-standards.sh` were verified manually this session in a scratch sandbox and against `datasource-graph-analyzer` but have no automated coverage
6. **Verify AGENTS.md auto-discovery** in Cursor/Windsurf/Cline/Codex before creating any tool-specific bridge file beyond `CLAUDE.md` — deferred from the `AGENTS.md` migration session, still unverified
7. **Run the ADR/Review-Log handoff** (`.session/2026-08-08-adr-adoption-and-review-log-archiving.md`) — was blocked on `AGENTS.md` existing; unblocked now
8. **Migrate remaining downstream projects** off `claude.md` — only `datasource-graph-analyzer` has been migrated so far; every other project pulling from this repo still has a legacy `claude.md` until someone runs `refresh-dev-standards.sh` in it

### Architectural Notes

- **Migration is pull-based, not pushed**: `refresh-dev-standards.sh` only migrates a project when someone runs it there. There's no mechanism (and none was requested) to migrate every downstream project in one sweep — each one self-migrates the next time it refreshes.
- **Dual template system**: `project-templates/*.template` files and inline heredocs in `setup-project.sh` serve the same purpose but drift independently. Decision needed: make templates the source of truth and have the script read them, or document that heredocs are canonical and templates are reference-only.
- **Python package vs. scripts repo identity**: `dev_standards/` package, `typer`, `rich`, `pyproject.toml` CLI scaffold all exist because the scaffold template generates them — this repo isn't actually a Python CLI tool. The package is vestigial.
- **`ARCHITECTURE.md.template` is manifest-analyzer-biased** — the directory structure it suggests (models/, parsers/, exporters/) only fits one project type in the ecosystem. Consider making it more generic or providing type-specific variants.

### Recommendations

- Reconcile or document the two template systems — if `project-templates/` is authoritative, setup-project.sh should read from those files rather than embedding duplicate content as heredocs
- Consider adding a `--branch` flag to both scripts to make the `develop`-by-default behavior explicit and overridable, rather than requiring someone to hand-edit the script to point at `main`
- Remove the `rich` upper-bound pin (`<14.0`) from both pyproject.toml and the inline heredoc template in setup-project.sh
- Add shell tests (bats) covering at minimum: `setup-project.sh --dry-run` with all required args, `refresh-dev-standards.sh --dry-run` against both a known `AGENTS.md` fixture and a legacy `claude.md` fixture (migration path)

### Review Log

- 2026-03-19 — reviewed at eed77a4, 17 issues found (5 incomplete, 6 bugs/fragile, 3 test gaps, 4 architectural concerns)
- 2026-08-08 — added `claude/modules/llm.md` (two-pass pipeline, chunking discipline, config conventions, thinking-model handling, pre-filtering, optional producer/consumer pattern), distilled from `datasource-graph-analyzer`'s proven patterns per `.session/2026-08-07-llm-pipeline-standards.md`. Along the way, discovered and removed the long-broken `llm-amplifier` module entry (listed in `setup-project.sh`'s menu and this file's own Tech Debt, but the module file never existed) — replaced it with `llm` across `setup-project.sh`, `README.md`, and `docs/usage_instructions.md`. Application of the new module to `lifeos-mcp` is deferred to a separate session in that repo.
- 2026-08-10 — completed `.session/2026-08-08-agents-md-migration.md` (resumed after an earlier interruption): renamed `refresh-claude.sh` → `refresh-dev-standards.sh`, retargeted generation from `claude.md` to `AGENTS.md`, added idempotent legacy-migration mode with a three-way `CLAUDE.md` handling branch (create/preserve-user-additions/warn-on-unrecognized-content), and updated `setup-project.sh`, README.md, and `docs/usage_instructions.md` to match. Found and fixed a gap the interrupted session had left: `claude/base.md` and `claude/HEADER.md` — the actual content fetched into every generated file — still said `claude.md`/`refresh-claude.sh` throughout their body text, not just the header comment; fixed and re-synced this repo's own `AGENTS.md` to match. Verified the full migration + idempotency + all three `CLAUDE.md` branches in an isolated scratch sandbox, then ran the real end-to-end test against `datasource-graph-analyzer` per the handoff's step 9 — migration succeeded, `## Project-Specific` preserved byte-for-byte, second run took the normal-refresh path. Discovered and (with user sign-off) fixed a dangling-symlink edge case the handoff hadn't anticipated: that project's `GEMINI.md -> claude.md` symlink broke on migration and was repointed to `AGENTS.md` manually — not generalized into the script (see Tech Debt). The ADR/Review-Log handoff is now unblocked.
