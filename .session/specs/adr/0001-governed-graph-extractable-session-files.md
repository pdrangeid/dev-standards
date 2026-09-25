---
tags: [session-files, schema, graph]
domain: dev-standards
scope: ecosystem
created: 2026-09-25
---
# ADR-0001: Governed, graph-extractable session files

Status: accepted
Deciders: Paul Drangeid

## Context

A review of seven real session files (April–September 2026, six repos) found the
format drifting. The header appeared in five different forms, and "Decisions Made
This Session" held six kinds of content: decisions, verification results,
discovered bugs and invalid premises, work log, carried items, and actions for
the user. Locked decisions sat under at least four different Context headings.
None of it could be extracted reliably, so `codebase-graph-analyzer` and
`lifeos-core` could not model session history without an LLM pass per file.

This partially reverses a locked decision in
`.session/2026-08-08-adr-adoption-and-review-log-archiving.md`: that a graph-based
agent-memory layer is "explicitly out of scope for the foreseeable future". This
ADR makes session files graph-*extractable* and defines the graph shape they map
to (`(:SessionPlan)-[:DOCUMENTED_IN]->(:MarkdownFile)`, a `(:SessionRun)` per
`runs` entry). It does not build the graph, store standards as graph nodes, or
gate a second LLM instruction step. Those parts of the 2026-08-08 decision stand.

## Options Considered

1. Keep free-form markdown and extract with an LLM — rejected because a
   non-deterministic extractor over a drifting format gives a graph nobody can
   trust. Structure has to be fixed at write time, where the author knows the facts.
2. A separate YAML sidecar per session — rejected because two files per session
   drift apart. Sidecars are kept only for legacy backfill, where the markdown
   must not be rewritten.
3. YAML frontmatter plus one fenced `yaml session-ledger` block inside the `.md`,
   validated by a Pydantic model that owns the schema — chosen.

## Decision

Every new session file carries `schema_version: 1` frontmatter and exactly one
`## Ledger` section with one `yaml session-ledger` fence, and it must pass
`session-lint` at close. The Pydantic models in `dev_standards/session_schema/`
are the single source of truth. `schemas/session-{header,ledger}.v1.schema.json`
are generated from them, committed, and guarded by a drift test. Consumers such as
`codebase-graph-analyzer` validate against the JSON Schema and do not import this
package. The JSON Schema is necessary but not sufficient, because cross-field
rules exist only in the models and `session-lint`. Links point backward in time:
never edit a closed session file to record what happened later. A newer file's
decision `answers` or `supersedes` a qualified `<repo>/<session-id>#X` ref instead.
Do not parse these blocks with regex beyond locating them, and do not add a stored
`superseded` decision status. Supersession is derived from incoming links.

## Consequences

- Work this creates: roll the template and `base.md` text out through
  `refresh-dev-standards.sh` (and merge `develop` → `main`, since
  `setup-project.sh` fetches the session template from `main`), owner Paul;
  analyzer parsing and graph model in `codebase-graph-analyzer` / `lifeos-core`,
  unassigned; legacy backfill via sidecars, unassigned.
- Writing a session file gets harder: authors (human or agent) maintain typed
  YAML, and closing a session requires a passing lint.
- Enforcement: `session-lint` (the Closing a Session step in `base.md`). No
  pre-commit hook or CI check enforces it yet. Adherence depends on the agent
  following `AGENTS.md`.
- A schema change is a versioned event: `schema_version: 2` means new exported
  schema files, and the linter must keep reading v1.

## Revisit Triggers

If more than 20% of new session files fail `session-lint` at close over any
30-day window, the schema is too strict or too complex. Reopen it.
