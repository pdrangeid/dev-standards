## Precedence

A repo's own `AGENTS.md` governs code inside that repo. This file governs cross-repo coordination, graph access, and session protocol.

## Working in a repo

Before reading or changing code in any repo listed below, read `<repo>/AGENTS.md` and follow it.

## Graph access

Database: `{{ graph_database }}`. Ad-hoc Cypher is read-only. Graph writes happen only by running pipeline tools.

## Session protocol

- Handoffs live in `.session/` (template: `.session/_template.md`).
- Every commit, in any repo, includes the trailer `Session: <handoff-file-stem>`.
- A decision that affects one repo is also recorded in that repo's `AGENTS.md`.
- Record decisions in the active handoff's `## Ledger` block as they are made.
