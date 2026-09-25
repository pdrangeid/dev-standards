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
├── specs/
│   └── adr/                      # durable decisions, one numbered ADR per file (always tracked)
│       ├── index.md              # table: number, title, status, date — the fast lookup path
│       ├── _template.md          # ADR template — do not edit, copy to create ADRs
│       └── NNNN-short-title.md   # e.g. 0001-two-pass-llm-split.md
├── archive/
│   └── review-log-YYYY.md        # Review Log entries rotated out of AGENTS.md (created on demand)
└── YYYY-MM-DD-[topic].md         # active or archived session files (tracked)
```

**ADR rules**
- One decision per file, numbered sequentially. Numbers are permanent — never reused,
  never renumbered. Supersession is a status change on the old file
  (`Status: superseded by ADR-0012`), never a deletion.
- `index.md` is the lookup path: an agent should be able to answer "did we already
  decide this?" from the table alone, and open an ADR only for its full rationale.
- Copy `_template.md` to create an ADR. If `specs/adr/` is missing (older project),
  create it from `claude/adr-template.md` and `claude/adr-index-template.md` in
  dev-standards.
- ADRs are for durable/architectural decisions. Routine fixes and minor refactors
  belong in the Review Log only.

### Session Files

A session file is one markdown file with two machine-readable parts, validated by
`session-lint` against the schema in dev-standards (`dev_standards/session_schema/`):

- **YAML frontmatter** (`schema_version: 1`, `id` = filename stem, `title`, `status`,
  `status_reason`, `created`, `repos` with exactly one `primary`, `branch`, `links`).
  `status` is `draft | active | blocked | complete | superseded | abandoned`;
  `blocked`/`abandoned` need a `status_reason`. A file with no frontmatter, or with
  older frontmatter that has no `schema_version`, is legacy.
- **One `## Ledger` section** holding exactly one ` ```yaml session-ledger ` fence with
  typed lists (IDs in brackets):

  | Key | Holds |
  |---|---|
  | `runs` | one entry per sitting: `date`, `surface`, `summary`, `commits` (`repo@sha`) |
  | `outcome` | `met \| partial \| not_met \| abandoned`, plus a note |
  | `decisions` [D] | `proposed \| accepted \| rejected`; `origin: user \| agent \| carried` (`carried` needs `carried_from`); `answers`, `supersedes`, `adr` |
  | `questions` [Q] | `open \| resolved \| deferred`; resolved needs `resolution` or an answering decision |
  | `findings` [F] | `bug \| premise_invalid \| confirmation \| drift` |
  | `checks` [C] | `pending \| pass \| fail \| not_run`; `fail`/`not_run` need a `reason` |
  | `debt` [T] | `this_repo \| other_repo \| platform` (`other_repo` needs `target_repo`) |
  | `blockers` [B] | `kind`, `owner`, `open \| cleared` |
  | `produced` | artifacts created: `kind` (graph label, e.g. `ShellScript`), `ref`, `repo` |

- **IDs and references.** Items are `D1`, `Q1`, `F1`, `C1`, `T1`, `B1` within a file.
  Same-file refs are `#Q1`; cross-file refs are always qualified
  `<repo>/<session-id>#Q1`, and session refs are `<repo>/<session-id>`.
- **Links point backward in time. Never edit a closed file to record what happened
  later.** A newer file's decision `answers` or `supersedes` an item in an older
  file; "resolved"/"superseded" is derived from those incoming links. That is why a
  decision has no `superseded` status.
- **Locked decisions live in the ledger**, as `origin: user` or `origin: carried`
  entries. Context prose refers to them by ID rather than restating them.
- YAML keys are snake_case. Never parse these blocks with regex. Locate them, then
  `yaml.safe_load` them.
- The published JSON Schemas (`schemas/session-header.v1.schema.json`,
  `schemas/session-ledger.v1.schema.json` in dev-standards) capture shape and enums
  only. Cross-field rules (id/date match, one primary repo, same-file refs, status
  vs. ledger contents) are enforced only by `session-lint`, so JSON Schema
  validation is necessary but not sufficient.

Run the linter from any repo (exit 1 on any error):

```sh
uvx --from git+https://github.com/pdrangeid/dev-standards@develop session-lint .session/
# No GitHub access: use a local checkout
uvx --from ~/develop/dev-standards session-lint .session/
```

It lints `*.md` recursively, skipping `_template.md`, `specs/` and `archive/`.
Legacy files are reported as info (`--strict` makes them errors).

### Starting a Claude Code Session

At the start of every session, before touching any code:

1. Read `AGENTS.md` (always)
2. Check for a session file: `ls .session/`. If a dated `.md` file has `status: draft`
   or `active` in its frontmatter (legacy files: a `Status:`/`status:` line), read it
3. For a conforming file, set `status: active` and append a `runs` entry (`date`,
   `surface`, a placeholder `summary`)
4. Skim `specs/adr/index.md` if it exists; open only the ADRs the session file
   references or that the index shows are relevant (skip `superseded`/`deprecated`)
5. Confirm your understanding of the **Goal** and **Constraints** before proceeding

If no session file exists, ask the user if there's a session to load or proceed with
their in-chat instructions.

### During a Session

- Record decisions, questions, findings, checks, debt and blockers in the `## Ledger`
  block as they happen, with the next free ID of each kind (legacy files: append to
  `## Decisions Made This Session`)
- If a constraint or out-of-scope boundary is hit, surface it explicitly rather than silently working around it
- Do not modify `_template.md` — copy it, rename it, then edit the copy

### Closing a Session

When the user signals the session is complete:

1. Close the ledger: fill this run's `summary` and `commits`, set every check's
   `result`, set `outcome`, and set the final `status` (`complete`, or `blocked` /
   `abandoned` with a `status_reason`). Then run `session-lint` on the file; it must
   pass. (Legacy file: update its `Status:` line instead.)
2. Identify any decisions that should be promoted to an ADR (durable/architectural)
   or to `AGENTS.md` (conventions every session must know)
3. Offer to write them: each durable decision gets a new numbered file in
   `specs/adr/` copied from `_template.md` — not a freeform addition to a baseline doc
4. Append each new ADR to `specs/adr/index.md`; if it supersedes an earlier ADR,
   update that ADR's `Status:` line and its index row. A ledger decision that gets
   an ADR carries an `adr: ADR-NNNN` pointer
5. **Update `AGENTS.md`:**
   - Append an entry to the **Review Log**. Shape: `**YYYY-MM-DD — Title**` followed
     by one paragraph covering what was built, what changed, and any bugs fixed.
     When the underlying decision has its own ADR, write a short pointer instead of
     re-describing it (e.g. "See ADR-0012 for the two-pass split rationale.");
     prose-only entries remain right for routine fixes and minor refactors
   - Update **Next Steps** to reflect current state — remove completed items,
     add newly unblocked ones
   - Update **Technical Debt** if new deferred items were identified
6. Rotate the Review Log (see below) if it now exceeds 8 entries
7. Follow the standard Session Close Checklist (docs, deps, commit)

#### Review Log rotation

The Review Log in `AGENTS.md` is a bounded, recent-entries-only list — not the
project history. Keep it short: `AGENTS.md` is loaded into every session, and
longer files reduce instruction adherence.

- Cap: **8** most recent entries live in `AGENTS.md`.
- If adding an entry leaves more than 8, move the oldest entries out until 8
  remain (all of the overflow, not just one — a log that was already over the cap
  drains in one pass).
- Move entries **verbatim** — same heading, same paragraph, no reformatting — by
  appending them, oldest first, to `.session/archive/review-log-<year>.md`.
- `<year>` is the year in the entry's own date, not the year of archiving; a batch
  that spans years is split across the matching files.
- If that file doesn't exist, create it with the header `# Review Log Archive — <year>`.
- Never archive Review Log entries to `CHANGELOG.md`. It is a release-facing
  artifact in a different format for a different audience, and is not touched here.

> `AGENTS.md` must be updated in the same commit as the session file closure
> (including any ADR, index, and archive-file changes from the steps above).
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
- `scripts/refresh-dev-standards.sh` — re-fetches base+modules from GitHub and updates downstream `AGENTS.md` files (and self-migrates any legacy `claude.md` project it finds), then syncs the `.session/` scaffold (templates replaced, `specs/adr/index.md` and `archive/` created only if missing)
- `claude/base.md` + `claude/modules/*.md` — composable standards content fetched at scaffold time
- `project-templates/` — reference templates for pyproject.toml, config.yaml, ARCHITECTURE.md, workspace.yaml
- `dev_standards/workspace/` + `dev-standards workspace new|render|check` — Python CLI that scaffolds and maintains multi-repo Claude Code workspaces from a `workspace.yaml` (see README `## Multi-Repo Workspaces`)
- `dev_standards/registry/` + `dev-standards registry generate|add|refresh|rollup|check` — generates each repo's `<repo>_registry.yaml` via an LLM CLI and maintains the machine-local `~/.repository_registry/` hub; schema in `docs/registry-schema.md`, consumed by `workspace/registry.py` (see README `## Repo Registry`)
- `dev_standards/session_schema/` + `session-lint` / `session-schema export` — Pydantic model for session-file frontmatter + `## Ledger` block, the linter, and the committed `schemas/session-{header,ledger}.v1.schema.json` (see ADR-0001)

The bash scripts remain the canonical mechanism for project `AGENTS.md`. The Python package is
otherwise a scaffold-generated stub; the `workspace`, `registry` and `session_schema` modules are its real
functionality and are additive — they do not replace or wrap the scripts.

### Key Patterns

- `AGENTS.md` composition: `setup-project.sh` fetches base.md + selected modules, appends `## Project-Specific` stub, and generates a `CLAUDE.md` bridge stub (`@AGENTS.md` import) alongside it
- `<!-- AUTO-GENERATED: base + modules[...] -->` header encodes which modules to re-pull on refresh
- `refresh-dev-standards.sh` splits on `## Project-Specific` — everything above is replaceable, below is preserved
- Legacy-state detection: a project with `claude.md` but no `AGENTS.md` (or a `claude.md` header still naming `refresh-claude.sh`) is auto-migrated on the next `refresh-dev-standards.sh` run — see `## Migrating an Older Project` in README.md
- Module selection: interactive menu or `--modules neo4j,live-exporter` flag
- Registry: an LLM only *describes* a repo (prompt on stdin, run from an empty temp dir); Python validates and writes. Idempotency is a `generated_from` source-doc hash, not LLM determinism, so unchanged repos cost no LLM call. The workspace consumer contract in `workspace/registry.py` (per-repo dict with `purpose`, aggregate list of `{repo, purpose}`) is locked; the hub needs no consumer changes because symlinks resolve transparently
- Workspaces: `workspace.yaml` is the source of truth; `render`/`check` share one desired-state plan (`workspace/render.py`), so re-render is idempotent and drift reporting matches render. `render` is a workspace's `refresh`: it also syncs the `.session/` scaffold with the same rules as `refresh-dev-standards.sh`. A hand edit to a generated file is a missing yaml option; add the option instead (that is how `graph.profile`, `graph.allow_writes` and the `settings.json` merge came about). `graph.database` is the Neo4j database the MCP server opens (`neo4j` on CE), never a lifeos-neo4j profile name. The workspace `AGENTS.md` is marker-delimited (`<!-- BEGIN/END GENERATED: name -->`), reads the same `claude/` fragments from a local editable checkout, and must not be run through `refresh-dev-standards.sh`. `claude/modules/workspace.md` is deliberately absent from `setup-project.sh`'s module menu
- Session schema: the Pydantic models are the source of truth; `schemas/*.json` are generated (`uv run session-schema export --out schemas/`) and `tests/test_schema_drift.py` fails if they're stale — regenerate and commit both after any model change. Parsing locates blocks with a fence-aware line scan, then `yaml.safe_load`; a schema change means `schema_version: 2` and new files, never an edit to v1
- Both scripts default `DEV_STANDARDS_RAW` to the `develop` branch — intentional for now so consumers get in-flight standards updates before they're merged to `main`. It can be overridden from the environment (any branch URL, or `file://…/claude` for a local checkout, which `tests/test_refresh_script.py` uses); no `--branch` flag exists yet (see Recommendations)

### Technical Debt

- `scripts/setup-project.sh:710-716` — module fetch failures in setup-project.sh only warn but don't set `FETCH_FAILED`; scaffold completes with an incomplete `AGENTS.md` and exits 0
- `scripts/setup-project.sh:236` — `git clone ... 2>/dev/null` silently swallows errors; failure and dry-run produce the same message
- `pyproject.toml:17` — `rich>=13.0,<14.0` upper-bound pin contradicts base.md convention (use `>=` lower bounds only)
- `claude/HEADER.md:1` — contains a hardcoded example commit hash (`a3f2c1`) that gets copied literally into the example header shown in that file (not actually used by either script — both scripts build their header inline)
- `dev_standards/claude.md.monolith` and `dev_standards/claude-code-session-starter.md` — historical artifacts in the package directory, predate the `AGENTS.md` migration and still describe the old `claude.md`/`refresh-claude.sh` workflow; should be archived or deleted
- `project-templates/ARCHITECTURE.md.template` — pre-fills manifest-analyzer directory structure (models/, parsers/, exporters/), too opinionated for a generic scaffold
- Two template systems exist with no sync mechanism: `project-templates/*.template` (Jinja-style `{{}}`) and heredocs in `setup-project.sh` (bash `${}`) — content has drifted between them
- `.mcp.json` rendered by `dev-standards workspace` embeds the absolute workspace path (for `uvx --env-file`), so re-rendering on another machine changes a committed file; a relative `.env` would avoid it but is unverified against Claude Code's MCP working directory
- `dev_standards/workspace/models.py` `KNOWN_SERVERS` holds the MCP env/tool contract for exactly one package (`neo4j-mcp-server`); adding another server means adding a profile
- `dev_standards/main.py`'s `run` stub is still a placeholder command
- The user's existing `~/Projects/*_registry.yaml` data has not been migrated into the repos or the hub (misnamed `lkifeos_schemata_registry.yaml`; `lifeos-embeddings`/`lifeos-jobwatch` aggregate-only; `datasource-graph-analyzer` per-repo only), and their hand-run `gemini` scripts fail because the CLI rejects their account tier (see `.session/2026-09-20-repo-registry-generator.md`)
- This repo's own Review Log entries before 2026-09-20 are `- date — text` bullets, not the `**date — Title**` shape `base.md` prescribes; harmless under the 8-entry cap but will archive verbatim in the old shape
- This repo's older `.session/` files are legacy (no frontmatter); `session-lint .session/` reports them as info. Converting them is the separate legacy-backfill project (sidecars), not a hand edit
- `lifeos-mcp/lifeos_mcp/services/strategic_review.py` `_PROJECT_CONTEXT_CYPHER` matches the project doc by `toLower(claude.name) = 'claude.md'`; once the migrated repos are committed and re-ingested the graph holds `AGENTS.md`, so `claudeContent` goes null for every migrated project. Fix belongs in `lifeos-mcp` (match `agents.md`, falling back to `claude.md`)
- Workspaces are only as current as their last `dev-standards workspace render`; nothing re-renders `~/workspaces/*` after dev-standards changes (the same pull model as `refresh-dev-standards.sh`)
- Nothing enforces `session-lint` at close (no pre-commit hook or CI); adherence relies on the Closing a Session step

### Next Steps

1. **Finish the session-format rollout** — `refresh-dev-standards.sh` has been run in all 13 downstream repos (2026-09-25); the results are uncommitted there. Merge `feature/workspace-parity` (it contains `feature/rollout-fixes`), re-run refresh in `lifeos-core`, `lifeos-envprofiler`, `lifeos-ingestor`, `lifeos-mcp` and `lifeos-neo4j` to repoint their dangling `GEMINI.md -> claude.md` symlinks, then commit + push each repo (`lifeos-collector` is on a `claude/…` branch, not `develop`). Then fix the `lifeos-mcp` strategic-review query (see Technical Debt)
2. **Move or delete historical artifacts** — `claude.md.monolith` and `claude-code-session-starter.md`
3. **Remove the `rich<14` upper-bound pin** from `pyproject.toml` and the `setup-project.sh` heredoc (see Recommendations)
4. **Adopt the registry on real repos and schedule it** — `dev-standards registry add <repo>` per repo (this regenerates via the LLM; decide whether to seed from the existing `~/Projects` files instead), point `registry_dir` at `~/.repository_registry`, then schedule a weekly `registry refresh` under `run_uv_script.sh`. Point the Mermaid flowchart script at the hub's `registry.yaml`
5. **Add automated tests for `setup-project.sh`** — `refresh-dev-standards.sh` is now covered by `tests/test_refresh_script.py` (pytest driving the real script with a `file://` `DEV_STANDARDS_RAW`); the same pattern should cover `setup-project.sh --dry-run` and Phase 3.5
6. **Verify AGENTS.md auto-discovery** in Cursor/Windsurf/Cline/Codex before creating any tool-specific bridge file beyond `CLAUDE.md` — deferred from the `AGENTS.md` migration session, still unverified
7. **Convert legacy `[topic]-baseline.md` specs to ADRs** per downstream project, when convenient — deliberately not done in the ADR adoption session

### Architectural Notes

- **Migration is pull-based, not pushed**: `refresh-dev-standards.sh` only migrates a project when someone runs it there. There's no mechanism (and none was requested) to migrate every downstream project in one sweep — each one self-migrates the next time it refreshes.
- **Dual template system**: `project-templates/*.template` files and inline heredocs in `setup-project.sh` serve the same purpose but drift independently. Decision needed: make templates the source of truth and have the script read them, or document that heredocs are canonical and templates are reference-only.
- **Python package vs. scripts repo identity**: the repo's primary product is still bash scripts plus markdown fragments. `dev_standards/` began as a scaffold-generated stub and now holds one real feature, the `workspace` module (2026-09-20), chosen because workspace rendering is structured-data work (yaml validation, JSON merge, marker regions) that is fragile in bash. It is additive: the scripts were not ported, and the two paths share the `claude/` fragment content, not code.
- **`ARCHITECTURE.md.template` is manifest-analyzer-biased** — the directory structure it suggests (models/, parsers/, exporters/) only fits one project type in the ecosystem. Consider making it more generic or providing type-specific variants.

### Recommendations

- Reconcile or document the two template systems — if `project-templates/` is authoritative, setup-project.sh should read from those files rather than embedding duplicate content as heredocs
- Consider adding a `--branch` flag to both scripts to make the `develop`-by-default behavior explicit and overridable, rather than requiring someone to hand-edit the script to point at `main`
- Remove the `rich` upper-bound pin (`<14.0`) from both pyproject.toml and the inline heredoc template in setup-project.sh
- Add shell tests covering `setup-project.sh --dry-run` with all required args, following `tests/test_refresh_script.py` (which already covers refresh, dry run, and the legacy `claude.md` migration path)

### Review Log

- 2026-08-10 — completed `.session/2026-08-08-agents-md-migration.md` (resumed after an earlier interruption): renamed `refresh-claude.sh` → `refresh-dev-standards.sh`, retargeted generation from `claude.md` to `AGENTS.md`, added idempotent legacy-migration mode with a three-way `CLAUDE.md` handling branch (create/preserve-user-additions/warn-on-unrecognized-content), and updated `setup-project.sh`, README.md, and `docs/usage_instructions.md` to match. Found and fixed a gap the interrupted session had left: `claude/base.md` and `claude/HEADER.md` — the actual content fetched into every generated file — still said `claude.md`/`refresh-claude.sh` throughout their body text, not just the header comment; fixed and re-synced this repo's own `AGENTS.md` to match. Verified the full migration + idempotency + all three `CLAUDE.md` branches in an isolated scratch sandbox, then ran the real end-to-end test against `datasource-graph-analyzer` per the handoff's step 9 — migration succeeded, `## Project-Specific` preserved byte-for-byte, second run took the normal-refresh path. Discovered and (with user sign-off) fixed a dangling-symlink edge case the handoff hadn't anticipated: that project's `GEMINI.md -> claude.md` symlink broke on migration and was repointed to `AGENTS.md` manually — not generalized into the script (see Tech Debt). The ADR/Review-Log handoff is now unblocked.
- 2026-09-20 — completed `.session/2026-08-08-adr-adoption-and-review-log-archiving.md`: replaced the freeform `specs/[topic]-baseline.md` convention with numbered ADRs (`.session/specs/adr/` with `_template.md` + `index.md`; numbers permanent, supersession by status) and replaced the "10 entries → archive to `CHANGELOG.md`" rule with a bounded Review Log (8 live entries; overflow drained in one pass, moved verbatim to `.session/archive/review-log-<year>.md` by each entry's own year). Content lives in `claude/base.md`; added `claude/adr-template.md` and `claude/adr-index-template.md`; `setup-project.sh` Phase 3.5 now scaffolds `specs/adr/` and `archive/` (ADR templates fetched from `develop`, `DEV_STANDARDS_RAW*` hoisted above the phase). Re-synced this repo's `AGENTS.md` from `base.md`, which also pulled in the Logging Contract section from d17ee1c that had never propagated here. Verified via `bash -n`, `--dry-run`, a real run of the Phase 3.5 block against local `file://` sources, and a simulated rotation on a 10-entry fixture spanning a year boundary. Known gap: `refresh-dev-standards.sh` does not seed the new directories in existing projects (see Next Steps).

**2026-09-20 — Multi-repo workspace module**

Completed `.session/2026-09-20-dev-standards-workspace-module.md` except its steps 9–11, which the user will run on `cranston-llm` (the workspace folder and `lifeos-hostops`/`lifeos-logwatch` were not on the session's machine). Added `dev-standards workspace new|render|check` (`dev_standards/workspace/`, Pydantic model for `workspace.yaml`, marker-region `AGENTS.md`, merge-rendered `.claude/settings.local.json`, drift check sharing one plan with render), `claude/modules/workspace.md`, `project-templates/workspace.yaml.template`, and 37 pytest tests. The handoff's assumption that a Python composition mechanism already existed was wrong — composition was bash-only — so the module reads the same `claude/` fragments from a local checkout; the bash scripts stay canonical and nothing was migrated (confirmed with the user). Verified the Neo4j MCP details against PyPI and neo4j/mcp v1.6.0: package `neo4j-mcp-server` pinned at 1.6.0, canonical `NEO4J_MCP_*` env vars, write tool `write-cypher` (deny rule `mcp__neo4j__write-cypher`); registry YAMLs live beside the repos in `~/Projects/` with a `purpose` field, so `workspace.yaml` gained an optional `registry_dir`. Also fixed `pyproject.toml` (`dev_Standards` casing, entry point, deps). Removed a stale Tech Debt item: `coverage.xml`/`htmlcov/` are already untracked and gitignored.

**2026-09-20 — Repo registry generator**

Completed `.session/2026-09-20-repo-registry-generator.md`. Added `dev-standards registry generate|add|refresh|rollup|check` (`dev_standards/registry/`), `docs/registry-schema.md`, and 47 tests (84 total). It builds the missing producer side of the registry that `workspace/registry.py` consumes: per-repo files are overwritten (never appended), a `generated_from` hash of the source docs makes a re-run a true no-op without an LLM call, and LLM output is validated before anything is written. The machine-local `~/.repository_registry/` symlink hub (confirmed with the user) makes every repo's registry discoverable in one place with no change to the locked consumer contract; the hub's symlinks are the repo list and `refresh` (the weekly job; schedule documented, not installed) continues past per-repo failures. Smoke-tested with a real LLM on a scratch copy of this repo's docs; a smoke test also found that headless `gemini` refuses untrusted directories, so the LLM now runs from an empty temp dir, and that the `gemini` CLI is rejected for the user's account tier, so the default LLM command is `claude -p` (override via `--llm-cmd`). Also fixed the earlier workspace CLI's logger name to satisfy Logging Contract rule 1. Existing `~/Projects` registry data was not migrated (see Tech Debt).

**2026-09-25 — Governed session-file schema**

Completed `.session/2026-09-25-dev-standards-session-file-schema.md`, the first session file written in the new format. Added `dev_standards/session_schema/`: Pydantic models for the frontmatter header and the `## Ledger` block, a fence-aware parser, `session-lint` (exit 1 on error, `--strict`, `--format json`, a plain `SUMMARY` log line) and `session-schema export`. Also added committed `schemas/session-{header,ledger}.v1.schema.json` behind a drift test, and 14 fixtures and 75 tests (159 total). Replaced `claude/session-template.md` and the `setup-project.sh` fallback stub, renamed "Decisions Made This Session" to `## Ledger` everywhere it was referenced, rewrote `base.md`'s session-workflow text (new Session Files subsection, run entries at start, lint at close) and re-synced this file. See ADR-0001, the first ADR in this repo (`.session/specs/adr/` created), for the decision and its partial reversal of the 2026-08-08 graph out-of-scope rule. Two handoff premises were wrong: `pyproject.toml` already existed (so the code is a subpackage, not a `src/` dist), and the checkout is `~/develop/`, not `~/Projects/`. README (`## Session Files and session-lint`), `docs/usage_instructions.md` and `ARCHITECTURE.md` document the new CLI. Rollout to other repos was out of scope.

**2026-09-25 — Refresh syncs the `.session/` scaffold**

`refresh-dev-standards.sh` now brings each project's `.session/` up to date on both the refresh and the migration path, so a refreshed repo can't end up with new `AGENTS.md` text next to an old session template. `_template.md` and `specs/adr/_template.md` are replaced when they differ; `specs/adr/index.md` and `archive/.gitkeep` are only created if missing; session files are never touched. The templates are fetched together with `base.md` before any write, so a failed fetch changes nothing. `DEV_STANDARDS_RAW` can now be overridden from the environment in both scripts, and `setup-project.sh` fetches the session template from the same branch as everything else (it was hardcoded to `main`, clearing that Tech Debt item and the former "seed `specs/adr/`" Next Step). Added `tests/test_refresh_script.py` (6 tests running the real script against `file://` sources: full scaffold, replace-vs-preserve, idempotent second run, dry run, failed fetch, legacy migration), the first automated coverage of either bash script.

**2026-09-25 — Rollout fixes: legacy frontmatter, dangling symlinks**

Checking the first downstream rollout (13 repos) turned up three problems, all fixed. `session-lint` reported 5 pre-schema files in `lifeos-collector`, `lifeos-ingestor` and `lifeos-mcp` as errors. They carry their own older YAML frontmatter (`Status:`/`Date:` or `title:`/`date:`), a sixth header form the original review missed. A file is now legacy unless its frontmatter has `schema_version`, with fixtures copied from both styles. Five repos had a `GEMINI.md -> claude.md` symlink left dangling by migration, the pattern the old Tech Debt note said to handle in the script if it recurred. Refresh now repoints any symlink aimed at a missing `claude.md` to `AGENTS.md`, on both paths, including repos migrated earlier. Refresh also dropped trailing blank lines from `## Project-Specific`, because `$(...)` strips them; it now copies that section byte-for-byte with `tail`. Added 7 tests (172 total). Found but not fixed (other repo): `lifeos-mcp`'s strategic-review Cypher looks up `claude.md` by name (see Technical Debt). First Review Log rotation: the 2026-03-19 entry moved to `.session/archive/review-log-2026.md`.

**2026-09-25 — Workspace parity**

Brought the two real multi-repo workspaces, `~/workspaces/lifeos-jobs` and `~/workspaces/lifeos-reporting`, up to the single-repo standard. Every change that had made them work lived in a hand-edited generated file, so the next render would have wiped it. The workspace tool now gives each one a place in `workspace.yaml`. `graph.database` defaults to `neo4j`, the real database on CE: `lifeos-kg` had been passed to the MCP server as a database name, but it is a lifeos-neo4j profile and now goes in the rules-only `graph.profile`. `graph.allow_writes` opts in to `write-cypher` (reporting's sessions create `:QueryTemplate`/`:Report` nodes). `.claude/settings.json` is merge-rendered. `render` syncs the `.session/` scaffold like refresh does, the Notes stub seeds Next Steps / Technical Debt / Review Log, and the workspace rules say where session close-out goes (the workspace is the frontmatter's `primary` repo). In each workspace, a snapshot commit kept the hand-edited state before the edits moved into the yaml and `.env` and the files were re-rendered. Both show no drift, and their MCP servers were verified live (initialize, tools/list, `read-cypher`). Both were local-only git repos. They are now private GitHub repos (`pdrangeid/lifeos-jobs`, `pdrangeid/lifeos-reporting`) with `master` renamed to `develop`, the default branch. Removed with sign-off: stray `uv init` files, an empty report file, and three leftover pre-tool workspace artifacts (no unique content; the one `.env` was byte-identical to `lifeos-jobs/.env`). Added 7 tests (178 total). Rotated the 2026-08-08 entry to the archive.
