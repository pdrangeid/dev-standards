---
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
---
# Land the known_hosts fix on cranston, then chase the docker:null gap

## Goal

Confirm the known_hosts CWD fix reaches cranston and runs unattended on every
ssh host, then find out why the NAS manifests carry `"docker": null`.

## Context & Constraints

Carried decisions from the 2026-09-16/17 sessions still apply. Merging to `main`
is out of scope.

## Relevant Specs / Schemas / Examples

(abbreviated for the fixture)

## Instructions

1. Verify the fix is on `develop`; push it.
2. Run tests and a manual `host_profile_sync` on both NAS hosts.

## Ledger

```yaml session-ledger
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
