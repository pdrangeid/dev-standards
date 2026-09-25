---
schema_version: 1
id: 2026-09-25-dev-standards-session-file-schema
title: Governed session-file schema (frontmatter + ledger) for dev-standards
status: complete
status_reason: null
created: 2026-09-25
repos:
  - {name: dev-standards, role: primary}
  - {name: codebase-graph-analyzer, role: reference}
  - {name: lifeos-core, role: reference}
branch: feature/session-ledger-schema
links:
  depends_on: [dev-standards/2026-08-08-adr-adoption-and-review-log-archiving]
  supersedes: []
  split_from: null
  references:
    - claude/base.md
    - claude/session-template.md
    - scripts/setup-project.sh
    - .session/specs/adr/0001-governed-graph-extractable-session-files.md
---
# Session: Governed session-file schema (frontmatter + ledger) for dev-standards

---

## Goal

Make every future `.session/` file machine-extractable by adding a versioned,
validated schema to `dev-standards`. Deliver: a Pydantic v2 model for a YAML
frontmatter header and a `## Ledger` YAML block (runs, outcome, decisions,
questions, findings, checks, debt, blockers, produced artifacts); committed JSON
Schema exports generated from that model; a `session-lint` CLI that enforces the
cross-field rules the JSON Schema can't express; an updated
`claude/session-template.md`; updated session-workflow text in `claude/base.md`;
and an ADR recording the decision. Done when `session-lint` passes on the fixture
corpus and on this file itself (converted to the new format at close), all tests
pass, and the committed JSON Schemas match what the model generates.

---

## Context & Constraints

### Why

A review of seven real session files (April–September 2026, six repos) found the
format drifting in two places. The header appears in five different forms (HTML
comment block, `Status:` above the H1, bold `**Status:**`, plain `Key: value`
lines, and multi-line prose status). "Decisions Made This Session" is a catch-all
holding six different kinds of content: actual decisions, verification results,
discovered bugs and invalid premises, work log, carried/not-done items, and
actions for Paul. Locked decisions also live in Context under at least four
different headings. This schema gives each of those a typed home.

### Locked decisions (from the 2026-09-25 strategy discussion)

- **One source of truth per session: the markdown file.** No separate YAML output
  for new sessions. Structured data lives in YAML frontmatter and one fenced ledger
  block inside the `.md`. (Legacy backfill will use sidecar files; that is a
  separate project.)
- **Regex locates, YAML parses.** Regex (or a heading scan) only finds the
  frontmatter and the ledger fence. Content is parsed with `yaml.safe_load` and
  validated with the Pydantic model. Never parse YAML with regex.
- **The schema lives in dev-standards** as a Pydantic model, exported to committed
  JSON Schema files stamped with a version. `codebase-graph-analyzer` stays
  standalone: it will consume the JSON Schema, not import this package.
  `lifeos-core` maps from the analyzer output as it does today.
- **A file is a plan; a sitting is a run.** Graph shape (for later sessions):
  `(:SessionPlan)-[:DOCUMENTED_IN]->(:MarkdownFile)`, with `(:SessionRun)` nodes
  per `runs` entry. Evidence: the 2026-08-08 file was implemented on 2026-09-20,
  and the Tableau file has an appended follow-up session.
- **Vocabulary borrowed, schema owned.** Runs and produced artifacts follow PROV-O
  (Activity / generated Entity), decisions follow the ADR lifecycle, questions and
  their answering decisions follow IBIS. The model itself is ours.
- **Links point backward in time. Never edit a closed file to record what happened
  later.** A newer file's decision `answers` or `supersedes` an item in an older
  file; the graph derives "resolved" / "superseded" from incoming edges. This keeps
  a single writer per fact. Consequence: decision status is only
  `proposed | accepted | rejected` — there is no stored `superseded` status.
- **Qualified IDs.** Items are `D1`, `Q1`, `F1`, `C1`, `T1`, `B1` within a file.
  Same-file references use `#Q1`. Cross-file references are always fully
  qualified: `<repo>/<session-id>#Q1`. Session references are `<repo>/<session-id>`.
- **Locked decisions move into the ledger.** Pre-session decisions are ledger
  entries with `origin: user` or `origin: carried` (with `carried_from`). Context
  prose refers to them by ID rather than restating them under ad-hoc headings.
- **YAML keys are snake_case with no aliases.** These blocks are hand- and
  agent-authored. camelCase conversion for graph properties is the job of the
  analyzer/`lifeos-core` mapping, not this model.
- **`schema_version: 1` in every conforming file**, so legacy and future versions
  can coexist. Files without frontmatter are treated as legacy by the linter.
- **Standard conventions apply:** `uv`, `typer`, `rich`, `black`, `ruff`,
  Python ≥3.11, Pydantic v2.

### Open questions — ask Paul before writing code, record answers in Decisions Made

1. **Heading name.** Rename "Decisions Made This Session" to `## Ledger` (proposed,
   since it now holds more than decisions), or keep the old heading and put the
   ledger block under it? Any tooling or prompts that reference the old heading
   need updating if renamed.
2. **Linter distribution.** How do consumer repos run `session-lint`?
   Proposed: `uvx --from git+https://github.com/pdrangeid/dev-standards@develop session-lint .session/`,
   with a local-path fallback (`uvx --from ~/Projects/dev-standards ...`) documented
   for hosts without GitHub access. Confirm whether the repo is reachable that way.
3. **Python packaging in dev-standards.** Confirm whether the repo already has a
   `pyproject.toml`. If not, this session adds a minimal one (package under `src/`).
   Do not run `setup-project.sh` against dev-standards itself — it could overwrite
   this repo's own generated `AGENTS.md`.

### Out of scope

- Rolling the new template out to other repos via `refresh-dev-standards.sh`
  (next session). Note that `session-template.md` is currently fetched from the
  `main` URL, so the new template won't reach projects until `develop` is merged
  to `main` — a deliberate human action.
- `codebase-graph-analyzer` parsing, manifest entities, and graph model.
- `lifeos-core` graph-side models and mapping.
- Legacy backfill (sidecars, LLM extraction, stale-status triage).
- Graph-as-governance: storing rules as graph nodes and diffing against them.
- Pre-commit hooks or CI wiring for `session-lint`.
- Resolving cross-file references for existence (syntax-only validation here).

### Reference files

- `claude/base.md` — "Session Files", "Starting a Claude Code Session",
  "Closing a Session" sections (session-workflow content lives here, not in a
  module; this repo's `AGENTS.md` is a generated copy re-synced from it).
- `claude/session-template.md` — current session template.
- `claude/adr-template.md`, `claude/adr-index-template.md` — ADR conventions.
- `scripts/setup-project.sh` Phase 3.5 — how templates are distributed.
- `scripts/refresh-dev-standards.sh` — refresh mechanism (read only).
- `.session/2026-08-08-adr-adoption-and-review-log-archiving.md` — contains the
  locked "graph-based agent-memory layer is out of scope for the foreseeable
  future" decision that this work partially reverses (see Instruction 11).

---

## Relevant Specs / Schemas / Examples

### Target package layout

```
dev-standards/
  pyproject.toml                         # new (or extended): package + console scripts
  src/session_schema/
    __init__.py                          # re-export models + validate_session
    models.py                            # Pydantic models (below)
    parse.py                             # locate frontmatter + ledger fence, safe_load
    lint.py                              # cross-block rules, LintIssue, validate_session
    cli.py                               # typer app: session-lint, session-schema export
  schemas/
    session-header.v1.schema.json        # generated, committed
    session-ledger.v1.schema.json        # generated, committed
  tests/
    fixtures/sessions/                   # see "Test fixtures" below
    test_models.py
    test_lint.py
    test_schema_drift.py
  claude/session-template.md             # updated
  claude/base.md                         # updated
```

`pyproject.toml` essentials:

```toml
[project]
name = "dev-standards-session-schema"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.6", "pyyaml>=6", "typer>=0.12", "rich>=13"]

[project.scripts]
session-lint = "session_schema.cli:lint_app"
session-schema = "session_schema.cli:schema_app"

[dependency-groups]
dev = ["pytest", "black", "ruff"]
```

### `models.py` — starting point (adjust freely, keep the semantics)

```python
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

REPO_NAME = r"[a-z0-9][a-z0-9._-]*"
SESSION_ID = r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*"

RepoName = Annotated[str, StringConstraints(pattern=rf"^{REPO_NAME}$")]
SessionId = Annotated[str, StringConstraints(pattern=rf"^{SESSION_ID}$")]
SessionRef = Annotated[str, StringConstraints(pattern=rf"^{REPO_NAME}/{SESSION_ID}$")]
# "#Q1" (same file) or "repo/session-id#Q1" (cross-file)
ItemRef = Annotated[
    str, StringConstraints(pattern=rf"^(?:{REPO_NAME}/{SESSION_ID})?#[DQFCTB]\d+$")
]
CommitRef = Annotated[str, StringConstraints(pattern=rf"^{REPO_NAME}@[0-9a-f]{{7,40}}$")]
Surface = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:claude-code-cloud|web|human|claude-code-(?:ide|cli)@[a-z0-9.-]+)$"
    ),
]
LabelName = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]*$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # typos in keys are errors


# ---------- enums ----------
class SessionStatus(StrEnum):
    draft = "draft"
    active = "active"
    blocked = "blocked"
    complete = "complete"
    superseded = "superseded"
    abandoned = "abandoned"

class RepoRole(StrEnum):
    primary = "primary"
    secondary = "secondary"
    reference = "reference"

class DecisionStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"

class Origin(StrEnum):
    user = "user"
    agent = "agent"
    carried = "carried"

class QuestionStatus(StrEnum):
    open = "open"
    resolved = "resolved"
    deferred = "deferred"

class FindingKind(StrEnum):
    bug = "bug"
    premise_invalid = "premise_invalid"
    confirmation = "confirmation"
    drift = "drift"

class CheckResult(StrEnum):
    pending = "pending"
    passed = "pass"
    failed = "fail"
    not_run = "not_run"

class DebtScope(StrEnum):
    this_repo = "this_repo"
    other_repo = "other_repo"
    platform = "platform"

class BlockerKind(StrEnum):
    human_action = "human_action"
    environment = "environment"
    dependency = "dependency"
    decision = "decision"

class BlockerStatus(StrEnum):
    open = "open"
    cleared = "cleared"

class OutcomeStatus(StrEnum):
    met = "met"
    partial = "partial"
    not_met = "not_met"
    abandoned = "abandoned"


# ---------- header (frontmatter) ----------
class RepoRef(_Strict):
    name: RepoName
    role: RepoRole

class Links(_Strict):
    depends_on: list[SessionRef] = []
    supersedes: list[SessionRef] = []
    split_from: SessionRef | None = None
    references: list[str] = []  # free-form paths/URLs, not validated

class SessionHeader(_Strict):
    schema_version: Literal[1]
    id: SessionId
    title: str = Field(min_length=1)
    status: SessionStatus
    status_reason: str | None = None
    created: date
    repos: list[RepoRef] = Field(min_length=1)
    branch: str | None = None
    links: Links = Field(default_factory=Links)

    @model_validator(mode="after")
    def _rules(self) -> "SessionHeader":
        if self.id[:10] != self.created.isoformat():
            raise ValueError("created must equal the date prefix of id")
        if sum(r.role == RepoRole.primary for r in self.repos) != 1:
            raise ValueError("exactly one repo must have role: primary")
        if self.status in (SessionStatus.blocked, SessionStatus.abandoned) and not self.status_reason:
            raise ValueError("status_reason is required when status is blocked or abandoned")
        return self


# ---------- ledger items ----------
class Run(_Strict):
    date: date
    surface: Surface
    model: str | None = None
    summary: str = Field(min_length=1)  # replaces free-form work-log bullets
    commits: list[CommitRef] = []

class Outcome(_Strict):
    status: OutcomeStatus
    note: str | None = None

class Decision(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^D\d+$")]
    text: str = Field(min_length=1)
    status: DecisionStatus
    origin: Origin
    carried_from: ItemRef | None = None
    signoff: bool = False  # a human explicitly approved an agent decision
    answers: list[ItemRef] = []
    supersedes: list[ItemRef] = []
    adr: Annotated[str, StringConstraints(pattern=r"^ADR-\d{4}$")] | None = None

    @model_validator(mode="after")
    def _carried(self) -> "Decision":
        if (self.origin == Origin.carried) != (self.carried_from is not None):
            raise ValueError("carried_from is required iff origin is carried")
        return self

class Question(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^Q\d+$")]
    text: str = Field(min_length=1)
    status: QuestionStatus
    resolution: str | None = None
    required_before: str | None = None

class Finding(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^F\d+$")]
    kind: FindingKind
    text: str = Field(min_length=1)
    resolved: bool = False
    refs: list[str] = []

class Check(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^C\d+$")]
    text: str = Field(min_length=1)
    command: str | None = None
    expected: str | None = None
    observed: str | None = None
    result: CheckResult = CheckResult.pending
    reason: str | None = None

    @model_validator(mode="after")
    def _reason(self) -> "Check":
        if self.result in (CheckResult.failed, CheckResult.not_run) and not self.reason:
            raise ValueError("reason is required when result is fail or not_run")
        return self

class Debt(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^T\d+$")]
    text: str = Field(min_length=1)
    scope: DebtScope
    target_repo: RepoName | None = None

    @model_validator(mode="after")
    def _target(self) -> "Debt":
        if self.scope == DebtScope.other_repo and not self.target_repo:
            raise ValueError("target_repo is required when scope is other_repo")
        return self

class Blocker(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^B\d+$")]
    text: str = Field(min_length=1)
    kind: BlockerKind
    owner: str = Field(min_length=1)  # "user", "agent", or a person's name
    status: BlockerStatus = BlockerStatus.open

class Artifact(_Strict):
    kind: LabelName  # intended graph label: ShellScript, MicroService, ADR, ...
    ref: str = Field(min_length=1)
    repo: RepoName | None = None


# ---------- ledger ----------
class SessionLedger(_Strict):
    runs: list[Run] = []
    outcome: Outcome | None = None
    decisions: list[Decision] = []
    questions: list[Question] = []
    findings: list[Finding] = []
    checks: list[Check] = []
    debt: list[Debt] = []
    blockers: list[Blocker] = []
    produced: list[Artifact] = []

    @model_validator(mode="after")
    def _ids_and_local_refs(self) -> "SessionLedger":
        items = [*self.decisions, *self.questions, *self.findings,
                 *self.checks, *self.debt, *self.blockers]
        ids = [i.id for i in items]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate item ids: {sorted(dupes)}")
        known = set(ids)
        local_refs = [r for d in self.decisions for r in (*d.answers, *d.supersedes)
                      if r.startswith("#")]
        missing = [r for r in local_refs if r[1:] not in known]
        if missing:
            raise ValueError(f"same-file refs do not resolve: {missing}")
        answered = {r[1:] for d in self.decisions for r in d.answers if r.startswith("#")}
        for q in self.questions:
            if q.status == QuestionStatus.resolved and not (q.resolution or q.id in answered):
                raise ValueError(
                    f"{q.id} is resolved but has no resolution text and no in-file decision answers it"
                )
        return self
```

### `parse.py` — locating the blocks

- Frontmatter: the file must start with `---\n` on line 1; the header is everything
  up to the next line that is exactly `---`. No frontmatter → classify the file as
  **legacy** (not an error unless `--strict`).
- Ledger: exactly one `## Ledger` heading, followed by exactly one fence whose info
  string is `yaml session-ledger`. Locate with a regex such as
  `re.compile(r"^```ya?ml session-ledger\n(.*?)^```", re.M | re.S)`, then
  `yaml.safe_load` the captured text. An empty block (`{}` or blank) is a valid
  empty ledger.
- Return a small dataclass: `path`, `is_legacy`, `header_raw`, `ledger_raw`,
  `body_text`, and line numbers of each block (for lint messages).

### `lint.py` — rules beyond the models

`validate_session(path) -> list[LintIssue]`, where `LintIssue` has `severity`
(`error` | `warning` | `info`), `rule`, `message`, `line`.

| Rule | Severity |
|---|---|
| Pydantic validation errors in header or ledger (one issue per error, with its field path) | error |
| `header.id` != filename stem | error |
| missing `## Ledger` heading or ledger fence, or more than one | error |
| `status: blocked` with no `open` blocker | error |
| `status: complete` with no runs, no `outcome`, any `pending` check, or any `open` blocker | error |
| `status: active` with no runs | warning |
| body still contains a legacy status line (`^Status:` or `^\*\*Status:\*\*`) | warning |
| body still contains a "Decisions Made This Session" heading | warning |
| cross-file refs (`repo/session-id#X`, `repo/session-id`) — syntax only, not existence | (covered by model) |
| file has no frontmatter | info (error with `--strict`) |

CLI:

```
session-lint PATH [PATH ...] [--strict] [--format text|json]
    PATH may be a file or a directory (recurses *.md, skips _template.md).
    Exit 1 if any error-severity issue; 0 otherwise. rich table for text output.

session-schema export [--out schemas/]
    Writes session-header.v1.schema.json and session-ledger.v1.schema.json
    from SessionHeader.model_json_schema() / SessionLedger.model_json_schema().
```

The JSON Schema captures shape and enums only; `model_validator` rules are not
expressible in it. Document that limitation in a `description` on each exported
schema and in `base.md`, so the analyzer knows JSON Schema validation is necessary
but not sufficient.

### New `claude/session-template.md` (proposed full text)

~~~markdown
---
schema_version: 1
id: YYYY-MM-DD-topic            # must equal the filename stem
title: One-line title
status: draft                   # draft | active | blocked | complete | superseded | abandoned
status_reason: null             # required when blocked or abandoned
created: YYYY-MM-DD             # must equal the id's date prefix
repos:
  - {name: repo-name, role: primary}   # exactly one primary; others secondary | reference
branch: develop
links:
  depends_on: []                # ["repo/YYYY-MM-DD-topic"]
  supersedes: []
  split_from: null
  references: []                # free-form paths/URLs
---
# <title>

## Goal

One paragraph. Specific deliverable and how "done" is judged (put the
checkable parts in the ledger as `checks`).

## Context & Constraints

Why this matters, out-of-scope items, reference files. Refer to locked
decisions by ledger ID (e.g. "see D1") instead of restating them here.

## Relevant Specs / Schemas / Examples

Actual data shapes, code fragments, commands.

## Instructions

1. Numbered, imperative steps.

## Ledger

<!--
Rules:
- Pre-session locked decisions: origin user or carried (carried needs carried_from).
- Add one runs entry per sitting; summary replaces free-form work-log bullets.
- Links point backward in time. Never edit a closed file to record later events;
  instead, a newer file's decision uses answers/supersedes with a qualified ref
  like repo/YYYY-MM-DD-topic#Q1.
- Same-file refs use "#Q1".
- Run `session-lint` on this file before closing.
-->

```yaml session-ledger
runs: []
outcome: null
decisions: []
questions: []
findings: []
checks: []
debt: []
blockers: []
produced: []
```
~~~

### Worked example — real content in the new shape (use as the main test fixture)

Header for `lifeos-hostops/.session/2026-09-18-cranston-live-known-hosts-merge-and-docker-null.md`:

```yaml
schema_version: 1
id: 2026-09-18-cranston-live-known-hosts-merge-and-docker-null
title: Land the known_hosts fix on cranston, then chase the docker:null gap
status: complete
status_reason: null
created: 2026-09-18
repos:
  - {name: lifeos-hostops, role: primary}
  - {name: lifeos-envprofiler, role: secondary}
branch: develop
links:
  depends_on: [lifeos-hostops/2026-09-18-lifeos-hostops-known-hosts-cron-cwd-bug]
  supersedes: []
  split_from: null
  references: [AGENTS.md, ARCHITECTURE.md]
```

Its ledger:

```yaml
runs:
  - date: 2026-09-18
    surface: claude-code-ide@cranston-llm
    summary: >-
      Confirmed the known_hosts fix was already on develop and pushed it; ran tests
      and manual host_profile_sync on both NAS hosts; fixed docker-nuc's stale
      allowlist; traced docker:null to PATH plus socket permissions and fixed the
      PATH cause in lifeos-envprofiler.
    commits: [lifeos-hostops@ed77f12, lifeos-envprofiler@84256db]
outcome: {status: partial, note: "Unattended midnight run not yet observed (C2)"}
decisions:
  - id: D1
    text: Don't redo the merge; fix commits are already linear on develop, push only
    status: accepted
    origin: agent
  - id: D2
    text: Record the DSM privilege gap as a Known Issue; don't fix it this session
    status: accepted
    origin: user
    answers: ["#Q1"]
questions:
  - id: Q1
    text: Fix the docker privilege gap now, or defer to a dedicated session?
    status: resolved
  - id: Q2
    text: docker-group membership vs scoped NOPASSWD sudo for lifeos-agent on DSM?
    status: open
    required_before: docker container inventory on NAS hosts
findings:
  - id: F1
    kind: premise_invalid
    text: Goal assumed the fix was never merged into develop; it already was
  - id: F2
    kind: bug
    text: docker-nuc allowed_jobs held leftover smoke-test content; every dispatch rc=64
    resolved: true
checks:
  - id: C1
    text: tests/run_tests.sh on cranston
    result: pass
    observed: 8/8
  - id: C2
    text: Unattended midnight cron succeeds on docker-nuc, dhb-nas, dh-nas
    result: not_run
    reason: Needs a real overnight run; carried to AGENTS.md Next Steps
debt: []
blockers: []
produced: []
```

Note that Q2 stays `open` in this file forever. A later file resolves it from its
own ledger, pointing backward:

```yaml
# in lifeos-hostops/.session/2026-09-21-synology-privileged-capture.md
decisions:
  - id: D1
    text: Privileged capture via a DSM Task Scheduler script; lifeos-agent stays unprivileged
    status: accepted
    origin: user
    answers: [lifeos-hostops/2026-09-18-cranston-live-known-hosts-merge-and-docker-null#Q2]
```

### Test fixtures (`tests/fixtures/sessions/`)

| Fixture | Expectation |
|---|---|
| `2026-09-18-cranston-live-known-hosts-merge-and-docker-null.md` (example above, prose sections abbreviated) | passes |
| `2026-09-25-minimal-draft.md` — template with placeholders filled, empty ledger | passes |
| blocked, no `status_reason` | error |
| blocked, reason given, no open blocker | error |
| complete with a `pending` check | error |
| duplicate item id (`D1` twice) | error |
| `origin: carried` without `carried_from` | error |
| `answers: ["#Q9"]` where Q9 doesn't exist | error |
| question `resolved` with no resolution and no answering decision | error |
| filename stem != `id` | error |
| unknown key (`decison:` typo) | error |
| two primary repos | error |
| legacy file with no frontmatter (copy the 2026-06-12 assess-log file's opening) | info; error with `--strict` |
| conforming file that still has a `Status:` line in the body | warning only |

`test_schema_drift.py`: regenerate both schemas in memory and assert they equal
the committed files in `schemas/`, so the model and the published schema can't
silently diverge.

---

## Instructions

1. Create `feature/session-ledger-schema` from `develop`.
2. Read `claude/base.md` (session-workflow sections), `claude/session-template.md`,
   `scripts/setup-project.sh` Phase 3.5, and `scripts/refresh-dev-standards.sh`.
   Check whether a `pyproject.toml` exists.
3. Ask Paul the three open questions in Context & Constraints. Record the answers
   in Decisions Made This Session before writing code.
4. Add or extend `pyproject.toml` per the spec, and create `src/session_schema/`.
   Do not run `setup-project.sh` against this repo.
5. Implement `models.py` from the starting point above. Keep the semantics; fix
   anything that doesn't compile or validate as intended, and record any
   deviation in Decisions Made.
6. Implement `parse.py` and `lint.py` per the spec, then `cli.py` with the two
   Typer apps.
7. Run `session-schema export --out schemas/` and commit both generated files.
8. Build the fixtures listed above and write `test_models.py`, `test_lint.py`, and
   `test_schema_drift.py`. Every fixture's expected outcome must be asserted.
9. Replace `claude/session-template.md` with the proposed template (adjusting the
   heading per open question 1).
10. Update `claude/base.md`:
    - "Session Files": describe frontmatter + ledger, the item types, qualified
      IDs, the backward-links rule, and the JSON Schema limitation.
    - "Starting a session": set `status: active` and append a `runs` entry.
    - "Closing a session": fill the run's `summary` and `commits`, set check
      results, set `outcome` and final `status`, run `session-lint` on the file
      (must pass), then the existing ADR promotion and Review Log steps. A
      ledger decision that gets an ADR carries an `adr: ADR-NNNN` pointer.
    - Show how to run `session-lint` (per open question 2's answer).
    Then re-sync this repo's own `AGENTS.md` from `base.md` the same way the
    2026-09-20 implementation did.
11. File an ADR in this repo's `.session/specs/adr/` (next number, using the ADR
    template) titled "Governed, graph-extractable session files". It records the
    decision and states that it partially reverses the 2026-08-08 locked decision
    that a graph-based history layer is out of scope for the foreseeable future.
    Revisit trigger: if more than 20% of new session files fail `session-lint` at
    close over a 30-day window, the schema is too strict or too complex. Add it to
    `index.md`.
12. Run `uv run black .`, `uv run ruff check .`, and `uv run pytest`. All must pass.
13. Stop before any rollout. Do not run `refresh-dev-standards.sh` against other
    repos and do not merge to `main`.
14. Close this session in the new format: add frontmatter and a `## Ledger` block
    to this file (decisions from step 3, a run entry, checks for steps 7, 8, 12
    and the lint of this file itself, outcome), then run `session-lint` on it. It
    must pass. Commit the session file closure together with the Review Log entry,
    per dev-standards.

---

## Ledger

```yaml session-ledger
runs:
  - date: 2026-09-25
    surface: claude-code-ide@cranston-llm
    model: claude-opus-5-5
    summary: >-
      Asked the three open questions (D1-D3). Added dev_standards/session_schema/
      (models, fence-aware parser, session-lint, JSON Schema export), committed v1
      schemas with a drift test, 14 fixtures and 75 tests. Replaced the session
      template and the setup-project.sh fallback stub, renamed the heading to
      '## Ledger' everywhere it was referenced, rewrote the session-workflow text in
      base.md and re-synced AGENTS.md, filed ADR-0001, and converted this file.
    commits: [dev-standards@cdba419, dev-standards@d82d9ff]
outcome:
  status: met
  note: >-
    Lint passes on the fixtures and this file, 159 tests pass, and the committed
    schemas match the models. Rollout to other repos stays out of scope.
decisions:
  - id: D1
    text: Rename 'Decisions Made This Session' to '## Ledger'; update base.md, modules/workspace.md and the setup-project.sh fallback stub
    status: accepted
    origin: user
    answers: ["#Q1"]
  - id: D2
    text: >-
      Consumers run 'uvx --from git+https://github.com/pdrangeid/dev-standards@develop
      session-lint .session/'; fallback 'uvx --from ~/develop/dev-standards ...'
    status: accepted
    origin: user
    answers: ["#Q2"]
  - id: D3
    text: >-
      Add dev_standards/session_schema/ as a subpackage of the existing dist; add the
      session-lint / session-schema console scripts to the existing pyproject; bump
      pydantic to >=2.6; tests stay in top-level tests/
    status: accepted
    origin: user
    answers: ["#Q3"]
  - id: D4
    text: >-
      Deviations from the spec's layout: schema generation lives in export.py (shared
      by the CLI and the drift test); test files are test_session_models.py /
      test_session_lint.py because tests/ is shared with the workspace and registry
      modules
    status: accepted
    origin: agent
  - id: D5
    text: >-
      Locate blocks with a fence-aware line scan, not a single regex: a '## Ledger'
      heading or ledger fence inside another fenced block (e.g. a quoted template,
      as in this file) is ignored, and the legacy body warnings skip fenced code too
    status: accepted
    origin: agent
  - id: D6
    text: >-
      In directory mode, session-lint skips _template.md plus the specs/ and archive/
      subtrees (ADRs, index, Review Log archives) instead of reporting them as legacy
      files; explicit file paths are always linted
    status: accepted
    origin: agent
  - id: D7
    text: >-
      Model fixes kept semantics: 'import datetime as dt' so Run.date doesn't shadow
      the type; a same-file carried_from ref must resolve like answers/supersedes;
      Pydantic error locations are mapped to file line numbers via yaml.compose
    status: accepted
    origin: agent
  - id: D8
    text: Governed, graph-extractable session files (partially reverses the 2026-08-08 graph out-of-scope decision)
    status: accepted
    origin: user
    adr: ADR-0001
questions:
  - id: Q1
    text: Rename 'Decisions Made This Session' to '## Ledger', or keep the old heading?
    status: resolved
  - id: Q2
    text: How do consumer repos run session-lint?
    status: resolved
  - id: Q3
    text: Does dev-standards already have a pyproject.toml, and where does the package go?
    status: resolved
findings:
  - id: F1
    kind: premise_invalid
    text: >-
      The handoff assumed pyproject.toml might not exist and proposed a src/ layout; it
      exists (dist 'dev-standards', flat dev_standards/ package, already depends on
      pydantic/pyyaml/typer/rich)
  - id: F2
    kind: premise_invalid
    text: The local fallback path is ~/develop/dev-standards, not ~/Projects/dev-standards
  - id: F3
    kind: confirmation
    text: github.com/pdrangeid/dev-standards is public; raw and API URLs both return 200
  - id: F4
    kind: drift
    text: >-
      This repo had no .session/specs/adr/ (listed in Technical Debt); created from
      the templates, so this ADR is 0001
    resolved: true
  - id: F5
    kind: drift
    text: >-
      base.md had no 'Session Files' section as the handoff said; added one as a
      subsection of Session Management
    resolved: true
checks:
  - id: C1
    text: session-schema export writes both schemas; committed files match the models
    command: uv run session-schema export --out schemas/ && uv run pytest tests/test_schema_drift.py
    result: pass
  - id: C2
    text: Every fixture's expected outcome is asserted
    command: uv run pytest tests/test_session_lint.py tests/test_session_models.py
    result: pass
    observed: 2 pass clean, 10 report exactly their one error, legacy info/strict-error, Status-line warning only
  - id: C3
    text: black, ruff and the full test suite pass
    command: uv run black --check . && uv run ruff check . && uv run pytest
    result: pass
    observed: 159 passed
  - id: C4
    text: session-lint passes on this file
    command: uv run session-lint .session/2026-09-25-dev-standards-session-file-schema.md
    result: pass
  - id: C5
    text: Local-path install works via uvx
    command: uvx --from . session-lint tests/fixtures/sessions/2026-09-25-minimal-draft.md
    result: pass
  - id: C6
    text: The GitHub-URL uvx invocation works from another repo
    result: not_run
    reason: feature/session-ledger-schema is not on GitHub develop yet; verify after it is merged and pushed
debt:
  - id: T1
    text: >-
      refresh-dev-standards.sh doesn't roll out the new template or seed
      specs/adr/, and setup-project.sh fetches session-template.md from main, so new
      projects keep the old template until develop is merged to main
    scope: this_repo
  - id: T2
    text: No pre-commit hook or CI runs session-lint; adherence relies on AGENTS.md
    scope: platform
produced:
  - {kind: PythonPackage, ref: dev_standards/session_schema, repo: dev-standards}
  - {kind: JsonSchema, ref: schemas/session-header.v1.schema.json, repo: dev-standards}
  - {kind: JsonSchema, ref: schemas/session-ledger.v1.schema.json, repo: dev-standards}
  - {kind: MarkdownTemplate, ref: claude/session-template.md, repo: dev-standards}
  - {kind: ADR, ref: .session/specs/adr/0001-governed-graph-extractable-session-files.md, repo: dev-standards}
```
