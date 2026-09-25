## Precedence

A repo's own `AGENTS.md` governs code inside that repo. This file governs cross-repo coordination, graph access, and session protocol.

## Working in a repo

Before reading or changing code in any repo listed below, read `<repo>/AGENTS.md` and follow it.

## Graph access

{{ graph_access }}

## Session protocol

- Handoffs live in `.session/` (template: `.session/_template.md`).
- Every commit, in any repo, includes the trailer `Session: <handoff-file-stem>`.
- A decision that affects one repo is also recorded in that repo's `AGENTS.md`.
- Record decisions in the active handoff's `## Ledger` block as they are made.
- In a session file's frontmatter the workspace itself is the `primary` repo (its
  `name`); each repo the session changes is `secondary`. Commit refs are `<repo>@<sha>`.
- At session close, this workspace's Next Steps, Technical Debt and Review Log go in the
  hand-written Notes section at the end of this file. That is where the base standards'
  "Update `AGENTS.md`" step applies. Each repo the session changed also gets its own
  Review Log entry.
