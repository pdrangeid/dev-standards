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