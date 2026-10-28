---
schema_version: 1
id: 2026-10-28-workspace-agent-skills
title: Pinned Agent Skills in dev-standards workspaces, plus neo4j-mcp-server 2.0.0 readiness
status: draft
status_reason: null
created: 2026-10-28
repos:
  - {name: dev-standards, role: primary}
  - {name: lifeos-reporting, role: secondary}
  - {name: lifeos-jobs, role: secondary}
branch: feature/workspace-skills
links:
  depends_on: [dev-standards/2026-09-20-dev-standards-workspace-module]
  supersedes: []
  split_from: null
  references:
    - https://github.com/neo4j-field/neo4j-mcp-workspace-template (9ed5a3b, 2026-07-17)
    - https://github.com/neo4j-contrib/neo4j-skills (39247b9, 2026-10-21)
    - https://github.com/neo4j/mcp/blob/main/CHANGELOG.md (v2.0.0, 2026-10-28)
    - https://agentskills.io/specification
    - dev_standards/workspace/models.py
    - dev_standards/workspace/render.py
    - claude/modules/neo4j.md
    - claude/modules/workspace.md
---
# Pinned Agent Skills in dev-standards workspaces, plus neo4j-mcp-server 2.0.0 readiness

## Goal

Add a `skills:` section to `workspace.yaml` so `dev-standards workspace render`
puts a pinned, reviewed set of Agent Skills (SKILL.md folders) into a workspace's
`.claude/skills/`, and `workspace check` reports drift in them. The skills come from
`neo4j-contrib/neo4j-skills` and from house skills kept in this repo. Done means:
`lifeos-reporting` renders with the D1 skill set, a second render is a no-op,
`check` flags a hand-edited skill file, and a smoke session in that workspace
picks up `neo4j-cypher-skill` for a Cypher-writing task. Separately, the
workspace tool is ready for `neo4j-mcp-server` 2.0.0, which shipped today, but
both workspaces stay on 1.6.0 until C5 passes.

## Context & Constraints

**Why not adopt the neo4j-field template's skills directly (F1).** The template
has one real workflow skill, `.agents/skills/develop-neo4j-graph/`. It builds a
new graph from CSV/PDF and is wired to five bespoke MCP servers (`neo4j-ingest`,
`neo4j-lexical-graph`, `neo4j-entity-graph`, `neo4j-graphrag`,
`neo4j-data-modeling`). Your workspaces analyse an existing graph through the
official read-only server, so its steps would call tools that don't exist here.
What carries over is the packaging pattern, not the content:

- The canonical skill lives in `.agents/skills/<name>/SKILL.md` (the Agent Skills
  standard). Each tool-specific directory (`.claude/skills/<name>`) points at it, so
  Cursor, Codex and Gemini read the same file. This matches your `AGENTS.md` +
  `CLAUDE.md` bridge decision.
- A `/setup-workspace` validation skill checks `.env` keys (without printing their
  values), confirms each MCP server's tools are loaded, runs `RETURN 'ok'`, and
  prints a readiness table. `workspace check` covers files but not the live server.
- `/dev:evaluate-pipeline` is a meta-skill that rebuilds the session's tool-call
  timeline and grades it against the skill. It's interesting, but it's out of
  scope here (T1).

**What the official Neo4j catalog offers (F2).** `neo4j-contrib/neo4j-skills` has
30 MIT-licensed skills (~300–580 lines each, with `references/` loaded on
demand). The ones that fit read-mostly analysis over lifeos-kg are
`neo4j-cypher-skill`, `neo4j-query-tuning-skill` and `neo4j-modeling-skill`, plus
`neo4j-gds-skill` if GDS is installed. Their upstream install paths are a Claude
Code plugin (`/plugin install neo4j-skills@neo4j-skills-marketplace`) and
`npx skills add`. Both are unpinned, per machine and invisible to
`workspace check`, which conflicts with the "workspace.yaml is the source of truth;
a hand edit is a missing yaml option" rule. Hence D2.

**The upstream `neo4j-mcp-skill` is stale (F3).** It configures the server with
`NEO4J_URI` / `NEO4J_DATABASE` / `NEO4J_READ_ONLY`, the aliases that v2.0.0
removed. Leave it out (D1), or replace it with a house skill.

**Precedence.** These skills are generic Neo4j advice. `claude/modules/neo4j.md`
(Cypher Generation Standards, `CALL {}` rules, relationship-type governance, APOC
conventions) and each repo's `AGENTS.md` win on any conflict. The workspace rules
must say this (step 6).

**neo4j-mcp-server 2.0.0 (F4).** It is on PyPI as of today. Breaking changes that
affect this repo:
- STDIO no longer defaults `NEO4J_MCP_DATABASE`. `render.py:148` already always
  emits it from `graph.database`, so this is safe.
- Initialize now fails if connectivity can't be verified or APOC is missing.
- The un-prefixed `NEO4J_*` aliases were removed. The profile already uses
  `NEO4J_MCP_*`, but check each workspace's `.env`.
- `list-gds-procedures` is exposed only when GDS is present.
- `NEO4J_MCP_TOOLS` (`--tools`) is a server-side tool allowlist. It could back up
  the `permissions.deny` rule for `write-cypher` (Q3).

**Out of scope:** `setup-project.sh` / single-repo projects (no skills section
there yet; T2); the neo4j-field bespoke MCP servers; Aura, driver, Spark, Kafka,
GraphQL and Spring skills; Claude Desktop `.skill` packaging; and the
`lifeos-mcp` strategic-review fix already listed in Next Steps.

## Relevant Specs / Schemas / Examples

Proposed `workspace.yaml` addition (D2/D3; field names are open to change in-session):

```yaml
skills:
  sources:
    - name: neo4j-skills
      checkout: /home/YOUR_USERNAME/develop/neo4j-skills   # local clone; absolute, no '~'
      ref: 39247b9                                          # exact commit; render uses `git archive <ref>`
    - name: house
      checkout: /home/YOUR_USERNAME/develop/dev-standards
      ref: develop                                          # house skills track the fragments' branch (Q2)
      root: skills
  include:
    - {source: neo4j-skills, skill: neo4j-cypher-skill}
    - {source: neo4j-skills, skill: neo4j-query-tuning-skill}
    - {source: neo4j-skills, skill: neo4j-modeling-skill}
    - {source: house, skill: setup-workspace}
```

Rendered layout (D4):

```
<workspace>/
├── .agents/skills/<skill>/...        # copied tree, generated, tracked
├── .agents/skills/.manifest.json     # {skill: {source, ref, sha256 per file}} for check
└── .claude/skills/<skill> -> ../../.agents/skills/<skill>
```

SKILL.md frontmatter shape (Agent Skills standard, as used upstream):

```yaml
---
name: neo4j-cypher-skill
description: Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x and 2026.x. Use when ...
---
```

Existing pattern to mirror: `ServerProfile` / `KNOWN_SERVERS` in
`dev_standards/workspace/models.py`. Fragments are read from a local editable
checkout, never from the network at render time.

The neo4j-field `/setup-workspace` readiness table (to adapt for the
`neo4j` server and `NEO4J_MCP_*` keys):

```
║  Configuration files    OK / MISSING           ║
║  Neo4j connection       OK / FAILED            ║
║  <server>               online / not loaded    ║
```

## Instructions

1. Read `AGENTS.md` and this file, then set `status: active` and add a `runs` entry.
   Ask Q1–Q4 before writing code and record the answers as decisions.
2. Clone `neo4j-contrib/neo4j-skills` to `~/develop/neo4j-skills`. Read the SKILL.md
   and `references/` of each D1 skill in full. Record any rule that contradicts
   `claude/modules/neo4j.md` as a finding. Contradictions are expected for
   `CALL {}` and the APOC conventions.
3. Add `Skills`, `SkillSource` and `SkillInclude` Pydantic models to
   `dev_standards/workspace/models.py` with `extra="forbid"`. Require absolute paths
   (`_require_absolute`), a non-empty `ref`, unique skill names, and that each
   `include.source` names a declared source.
4. In `render.py`, add the skills to the shared desired-state plan. For each include,
   read the tree with `git -C <checkout> archive <ref> <root>/<skill>` (no network,
   independent of the checkout's working state). Write it under
   `.agents/skills/<skill>/`, write `.manifest.json`, and create the `.claude/skills`
   symlink. Remove skills that are no longer listed only when the manifest shows
   render created them.
5. Make `workspace check` report a missing skill, an extra one, a modified file
   (manifest hash mismatch) and a ref mismatch, all reusing the plan. Exit codes
   should match the existing drift reporting.
6. Add to `claude/modules/workspace.md` a `## Skills` paragraph, rendered only when
   skills are configured. It lists each skill and states the precedence rule:
   repo `AGENTS.md` > `modules/neo4j.md` > skills.
7. Write the house `skills/setup-workspace/SKILL.md` in this repo, adapted from
   neo4j-field's version. Generate the server list from `.mcp.json`, report the
   `NEO4J_MCP_*` keys as set/missing (never their values), and test with `RETURN 'ok'`
   through `read-cypher`. Point the user to `dev-standards workspace check` /
   `render` for fixes.
8. Add tests to `tests/test_workspace_*.py` with a local git fixture repo as the
   source: render, idempotent re-render, check on a modified file, check on ref
   drift, a stale skill removed, and a hand-added skill left alone with a warning.
   Run `ruff`, `black --check` and `pytest`.
9. Update `project-templates/workspace.yaml.template` (commented `skills:` block),
   the README `## Multi-Repo Workspaces` section, `docs/usage_instructions.md` and the
   `ARCHITECTURE.md` component table.
10. Prepare for neo4j-mcp-server 2.0.0 without bumping either workspace:
    - Add a `KNOWN_SERVERS` note or test asserting that `NEO4J_MCP_DATABASE` is always
      emitted.
    - Grep both workspaces' `.env` for un-prefixed `NEO4J_*` keys.
    - Implement the Q3 decision on `NEO4J_MCP_TOOLS`.
    - Run C5 against a scratch render pinned to 2.0.0. If C5 passes, record that in
      the ledger. Change the pins only if the user says so.
11. Add the D1 skills to `~/workspaces/lifeos-reporting/workspace.yaml`, render,
    check, and run the C4 smoke session. Commit in that repo with the
    `Session: 2026-10-28-workspace-agent-skills` trailer. Do the same for
    `lifeos-jobs` only if Q4 says to.
12. Close per `AGENTS.md`: ledger, `session-lint`, and Review Log. Offer an ADR for
    D2–D4: vendoring pinned skills is a durable decision that rules out the plugin
    route.

## Ledger

```yaml session-ledger
runs: []
outcome: null
decisions:
  - id: D1
    text: >-
      Initial upstream skill set: neo4j-cypher-skill, neo4j-query-tuning-skill,
      neo4j-modeling-skill (neo4j-gds-skill only if GDS is installed on the target
      instance). Exclude neo4j-mcp-skill (stale env vars, see #F3) and every
      driver/Aura/framework skill
    status: proposed
    origin: agent
    answers: ["#Q1"]
  - id: D2
    text: >-
      Vendor skills through workspace.yaml (pinned commit, read with git archive
      from a local checkout), not through the Claude Code plugin marketplace or
      npx skills add: pinned, reviewable, visible to workspace check, and in line
      with the hand-edit-is-a-missing-yaml-option rule
    status: proposed
    origin: agent
  - id: D3
    text: >-
      Skills are workspace-level only in this session; setup-project.sh and
      refresh-dev-standards.sh are unchanged
    status: proposed
    origin: agent
  - id: D4
    text: >-
      Canonical copy in .agents/skills/<name>/ with a .claude/skills/<name> symlink
      (the neo4j-field pattern), tracked in the workspace repo, with a manifest of
      file hashes for drift checks
    status: proposed
    origin: agent
    answers: ["#Q2"]
questions:
  - id: Q1
    text: Is the D1 skill set right? Is GDS installed on the lifeos-kg instance?
    status: open
  - id: Q2
    text: >-
      Copy skill trees into the workspace (D4, tracked, works on any machine) or
      symlink into the local checkout (smaller diff, but breaks on another machine)?
      Should house skills follow the develop branch or a pinned ref?
    status: open
  - id: Q3
    text: >-
      Also emit NEO4J_MCP_TOOLS (server-side allowlist) when graph.allow_writes is
      false, as defence in depth behind the permissions.deny rule? This needs its
      value syntax confirmed in neo4j/mcp internal/config/config.go
    status: open
  - id: Q4
    text: Roll skills into lifeos-jobs too, or lifeos-reporting only for now?
    status: open
findings:
  - id: F1
    kind: premise_invalid
    text: >-
      neo4j-field/neo4j-mcp-workspace-template's develop-neo4j-graph skill is a
      greenfield CSV/PDF-to-graph workflow bound to five bespoke MCP servers; it
      cannot run against the official read-only server these workspaces use. Only
      its packaging pattern (.agents/skills + .claude/skills symlink,
      /setup-workspace) transfers
  - id: F2
    kind: confirmation
    text: >-
      neo4j-contrib/neo4j-skills (30 skills, MIT, Agent Skills format) is the
      official catalog; its install routes (plugin marketplace, npx skills add) are
      unpinned and per-machine
  - id: F3
    kind: drift
    text: >-
      Upstream neo4j-mcp-skill and mcp_config.json document NEO4J_URI /
      NEO4J_DATABASE / NEO4J_READ_ONLY, which neo4j-mcp-server 2.0.0 removed
  - id: F4
    kind: drift
    text: >-
      neo4j-mcp-server 2.0.0 released 2026-10-28 (workspaces pin 1.6.0; 1.6.1 also
      exists). STDIO database default removed (render already sets it), Initialize
      fails without APOC or connectivity, legacy NEO4J_* aliases removed,
      list-gds-procedures conditional on GDS
checks:
  - id: C1
    text: Render twice on a fixture workspace with skills; the second run changes nothing
    command: uv run pytest tests/ -k skills
    result: pending
  - id: C2
    text: check reports a hand-modified skill file and a ref mismatch as drift
    command: uv run pytest tests/ -k skills
    result: pending
  - id: C3
    text: Lint, format and full test suite pass
    command: uv run ruff check . && uv run black --check . && uv run pytest
    result: pending
  - id: C4
    text: >-
      In lifeos-reporting, a fresh Claude Code session lists the vendored skills and
      invokes neo4j-cypher-skill for a Cypher-writing prompt; /setup-workspace prints
      the readiness table with the neo4j server online
    result: pending
  - id: C5
    text: >-
      A scratch render pinned to neo4j-mcp-server 2.0.0 passes initialize, tools/list
      and read-cypher against lifeos-kg
    result: pending
debt:
  - id: T1
    text: >-
      Consider an evaluate-session meta-skill (after neo4j-field's
      /dev:evaluate-pipeline) that grades a session's tool calls against the skill
      it followed
    scope: this_repo
  - id: T2
    text: >-
      Single-repo projects have no way to get pinned skills; decide whether
      setup-project.sh / refresh-dev-standards.sh should gain one
    scope: this_repo
blockers: []
produced: []
```
