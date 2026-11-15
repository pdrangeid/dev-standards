---
schema_version: 1
id: 2026-11-15-ops-base-and-infra-ops-module
title: Selectable ops base, infra-ops module, and optional workspace graph
status: complete
status_reason: null
created: 2026-11-15
repos:
  - {name: dev-standards, role: primary}
  - {name: infra-dirthaven, role: reference}
branch: claude/sharp-hamilton-sqtfw9
links:
  depends_on: [dev-standards/2026-09-20-dev-standards-workspace-module]
  supersedes: []
  split_from: null
  references:
    - claude/base-src/
    - claude/modules/infra-ops.md
    - dev_standards/bases.py
    - scripts/refresh-dev-standards.sh
    - "infra-dirthaven session ledger: D13 (proposed this work), T4 (dev-standards debt)"
---
# Selectable ops base, infra-ops module, and optional workspace graph

## Goal

Let dev-standards produce `AGENTS.md` files for repos and workspaces that are not
Python projects, starting with infra-dirthaven (shell scripts, Pi-hole, network
config). Deliver a selectable base (`python`, the default, or `ops`) used by both
`refresh-dev-standards.sh` and `dev-standards workspace render`; a
`claude/modules/infra-ops.md` module for working on live hosts; and an optional
`graph:` section in `workspace.yaml`. Done when existing Python repos and
workspaces keep refreshing and rendering unchanged apart from two generalized
common lines, an ops header and an ops workspace produce Python-free standards with
no Graph access section, and the checks in the ledger pass.

## Context & Constraints

- Raised from the infra-dirthaven layout-audit session. There, the repo and
  workspace `AGENTS.md` carried uv / typer / `config.py` / Neo4j logging rules and
  a Graph access section with no graph behind it. Both are generated, so the fix
  belongs here (see D1).
- Existing Python repos must not need a migration (D2), and stale local checkouts
  of the refresh script must not produce a broken `AGENTS.md` (D3).
- Out of scope: applying the change on the user's machine (re-header and refresh
  infra-dirthaven, re-render its workspace). The cloud session can't reach it.
  Also out of scope: an ops path in `setup-project.sh` (T1).
- Host-specific rules (e.g. Synology DSM's sudo password prompt, `pihole-configs`
  being a separate repo) belong in infra-dirthaven, not in the module (D5).

## Relevant Specs / Schemas / Examples

Repo opt-in (first line of `AGENTS.md`):

```
<!-- AUTO-GENERATED: base:ops + modules[infra-ops] -->
```

Workspace opt-in (`workspace.yaml`):

```yaml
standards:
  base: ops            # default: python
  modules: [infra-ops]
# graph: omitted -> no Graph access section; required if a Neo4j MCP server is listed
```

Base build: `claude/base-src/<name>.md` + `"\n\n---\n\n"` + `claude/base-src/common.md`
→ `claude/base.md` (python) / `claude/base-<name>.md`, via `dev-standards bases build`.

## Instructions

1. Split `claude/base.md` into `base-src/python.md` and `base-src/common.md`; verify
   the concatenation is byte-identical before any edit.
2. Write `base-src/ops.md` and `modules/infra-ops.md`; generalize the two
   Python-only common lines.
3. Add `dev_standards/bases.py` (`bases build|check`) and a drift test.
4. Teach `refresh-dev-standards.sh` the `base:<name>` header token on both paths.
5. Add `standards.base` and optional `graph` to the workspace model and render.
6. Update README, usage docs, ARCHITECTURE, the workspace template, and this repo's
   `AGENTS.md`; run the checks below.

## Ledger

```yaml session-ledger
runs:
  - date: 2026-11-15
    surface: claude-code-cloud
    summary: >-
      Split base.md into base-src/{python,common}.md (byte-identical rebuild
      verified first), added base-src/ops.md, modules/infra-ops.md, and
      dev_standards/bases.py with bases build/check plus a drift test. The refresh
      script now reads base / base@sha / base:<name> from the header and aborts
      on a malformed base. Added workspace standards.base and optional graph.
      Updated docs, re-synced this repo's AGENTS.md, and rotated one Review Log
      entry. 27 new tests (207 total).
    commits: [dev-standards@93a3b35]
outcome:
  status: met
  note: >-
    dev-standards side done. Applying it to infra-dirthaven (re-header + refresh,
    workspace standards/graph edit + render) is AGENTS.md Next Step 8, on the
    user's machine.
decisions:
  - id: D1
    status: accepted
    origin: user
    text: >-
      Non-Python repos and workspaces get their own standards option in
      dev-standards. The generated AGENTS.md files aren't hand-edited.
  - id: D2
    status: accepted
    origin: agent
    text: >-
      Make the base selectable, defaulting to python, rather than moving Python
      rules out of base.md into a module. A module move would strip Python rules
      from every repo whose header lists no modules.
  - id: D3
    status: accepted
    origin: agent
    text: >-
      Bases are built from base-src/<name>.md + common.md and committed as
      claude/base.md and claude/base-<name>.md. base.md keeps its name and stays
      complete, so a stale refresh-script checkout that only fetches base.md still
      gets the session rules. A drift test guards the build.
  - id: D4
    status: accepted
    origin: agent
    text: >-
      Header syntax is base:<name> (plain base and legacy base@<sha> mean python).
      A malformed base token aborts the refresh before writing, and an unknown
      base fails the fetch and writes nothing.
  - id: D5
    status: accepted
    origin: agent
    text: >-
      Split by concern: the ops base covers repo conventions (shell, layout,
      config/secrets, docs), and infra-ops covers acting on live hosts. Facts about
      specific hosts stay in the consuming repo's Project-Specific / workspace
      Notes.
  - id: D6
    status: accepted
    origin: agent
    text: >-
      workspace.yaml graph is optional. It is still required when a configured MCP
      server has a known graph profile (neo4j-mcp-server). Without it, the Graph
      access section is omitted and write-tool deny rules still apply.
questions: []
findings:
  - id: F1
    kind: drift
    text: >-
      This repo's own GEMINI.md was a dangling symlink to claude.md, and
      .session/_template.md had never been created. The refresh run in this
      session repaired both, as designed.
    resolved: true
  - id: F2
    kind: confirmation
    text: >-
      Splitting base.md at the Documentation Currency heading rebuilds it
      byte-for-byte, so the only Python-repo change is the two deliberate
      common-section edits.
    resolved: true
checks:
  - id: C1
    text: Full test suite passes
    command: uv run pytest -q --no-cov
    expected: all pass
    observed: 207 passed
    result: pass
  - id: C2
    text: Built bases match sources
    command: uv run dev-standards bases check
    expected: exit 0
    observed: All bases up to date
    result: pass
  - id: C3
    text: ruff and black clean on dev_standards/ and tests/
    command: uv run ruff check dev_standards tests && uv run black --check dev_standards tests
    expected: no findings
    observed: All checks passed; black unchanged
    result: pass
  - id: C4
    text: No new shellcheck warnings in refresh-dev-standards.sh
    command: uvx --from shellcheck-py shellcheck -S warning scripts/refresh-dev-standards.sh
    expected: only the pre-existing SC2034 (DEV_STANDARDS_RAW_MAIN unused)
    observed: only SC2034, same as before the change
    result: pass
  - id: C5
    text: This session file passes session-lint
    command: uv run session-lint .session/2026-11-15-ops-base-and-infra-ops-module.md
    expected: exit 0
    result: pass
  - id: C6
    text: infra-ops Pi-hole v6 commands verified on a live Pi-hole
    result: not_run
    reason: No Pi-hole reachable from the cloud session; the module tells agents to confirm with pihole -v / pihole -h.
debt:
  - id: T1
    scope: this_repo
    text: setup-project.sh has no --base ops path; a new ops repo is hand-started then refreshed.
  - id: T2
    scope: this_repo
    text: >-
      An old refresh-script checkout rewrites a base:ops header back to plain base
      (Python). Pull dev-standards before refreshing an ops repo.
  - id: T3
    scope: other_repo
    target_repo: infra-dirthaven
    text: >-
      Apply the ops base: header base:ops + modules[infra-ops] and refresh; set
      workspace standards to ops, drop graph:, then render and check. Clean up the
      Python leftovers in README / ARCHITECTURE.
blockers: []
produced:
  - {kind: MarkdownFile, ref: claude/base-ops.md, repo: dev-standards}
  - {kind: MarkdownFile, ref: claude/modules/infra-ops.md, repo: dev-standards}
  - {kind: PythonModule, ref: dev_standards/bases.py, repo: dev-standards}
```
