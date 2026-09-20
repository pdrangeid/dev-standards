Status: complete

# Session Handoff: ADR Adoption + Review Log Archiving for `dev-standards`

**Date:** 2026-08-08
**Topic:** adr-adoption-and-review-log-archiving

---

## Goal

Replace the current freeform `.session/specs/[topic]-baseline.md` convention with a numbered Architecture Decision Record (ADR) format, and fix the `claude.md`/`AGENTS.md` Review Log so that truncation archives overflow entries into dated files that mirror the live entry structure, instead of flattening them into a growing `CHANGELOG.md`. Both changes land in the `dev-standards` repo's base module (the session-workflow conventions section, not the `llm` or `neo4j` modules), so every project that pulls `dev-standards` inherits the new structure on its next refresh.

---

## Context & Constraints

**Why this matters:** The current session-close workflow writes durable decisions into both `specs/` (freeform prose) and the `claude.md` Review Log (a growing list), with no template discipline on the former and an ad hoc 10-entries-then-archive-to-CHANGELOG rule on the latter. Neither gives a future agent (or you, six months from now) a fast way to find "what did we decide about X and why" without reading prose top to bottom. ADRs fix the first problem; a structure-preserving archive fixes the second.

**Locked decisions (from discussion):**
- Adopt the ADR format for `specs/` — one file per decision, sequentially numbered, plus an index. This is a well-established format (Nygard, 2011), with a 2026 adaptation specifically for agent-written codebases that this session's template is based on: rejection reasons must generalize (not just "we didn't pick this"), the Decision section explicitly names the anti-pattern to avoid, and a Revisit Triggers section gives a measurable condition for reopening the question — all details a freeform prose spec tends to omit.
- **Explicitly out of scope for the foreseeable future:** a graph-based agent-memory layer (history + codified standards as graph relationships, gating a second LLM instruction step). This is a deliberate long-term direction, not something to partially build now — don't reach for graph structures, embeddings, or a "memory bank" pattern in this session. Keep ADRs as plain numbered markdown files.
- Also out of scope for **this** session specifically: the `refresh-claude.sh` → `refresh-dev-standards.sh` rename, the migration-mode behavior, and the `.claude/rules/` symlink distribution model discussed earlier. Those are real, agreed-upon next steps but are a separate unit of work — don't fold them into this handoff's instructions.
- The Review Log stays in `AGENTS.md` (its post-rename home) as a **bounded, recent-entries-only** list — not the full project history. Keeping it short is not just tidiness: Anthropic's own guidance for these files is to target under 200 lines total, because longer files consume more context and measurably reduce instruction adherence. A growing, unbounded Review Log works directly against that.
- Archived Review Log entries must **keep the same per-entry shape they had live** (dated heading + one paragraph) — the fix is relocation, not reformatting into `CHANGELOG.md`'s categorized Added/Changed/Fixed structure. A `CHANGELOG.md` is a different artifact for a different audience (humans scanning release notes); don't conflate the two.
- ADR numbers are global and permanent within a project — never reused, never renumbered, even when an ADR is later superseded. Supersession is a status change (`Status: superseded by ADR-0012`) on the old file, not a deletion.

**Out of scope:**
- Retroactively converting the existing `.session/specs/[topic]-baseline.md` files in already-running projects into the new ADR format — this session designs and documents the new convention; a separate pass (per project, when convenient) does the migration.
- Any change to the `llm` module content added in the prior two sessions.
- Tooling to auto-generate ADR numbers or auto-update the index (e.g. a script) — start with a manually maintained index; revisit if the manual step becomes a real friction point.

**Reference files:**
- The base `claude.md` module's "Session Files" / "Closing a Session" section (content already reviewed via project knowledge search — reproduced in the spec below) — exact file path within `dev-standards` not confirmed; locate it (likely `modules/base.md` or wherever the non-`neo4j`/non-`llm` conventions live) before editing.
- `.session/_template.md` — the canonical session-file template; needs a corresponding `.session/specs/adr/_template.md` counterpart added.
- The current freeform `specs/[topic]-baseline.md` convention, and the "if Review Log exceeds 10 entries, archive all but 5 most recent to `/CHANGELOG.md`" rule — both being replaced by this session.

---

## Relevant Specs / Schemas / Examples

### New directory structure

```
.session/
├── _template.md
├── specs/
│   └── adr/
│       ├── index.md                    # table: number, title, status, date
│       ├── _template.md                # ADR template (below)
│       ├── 0001-example-decision.md
│       └── 0002-...
├── archive/
│   └── review-log-2026.md              # one file per calendar year, created on demand
└── YYYY-MM-DD-[topic].md
```

### ADR template (`specs/adr/_template.md`)

```markdown
---
tags: []
domain: ""
scope: ""
created: YYYY-MM-DD
---
# ADR-NNNN: <Title>

Status: proposed | accepted | superseded by ADR-NNNN | deprecated
Deciders: <name(s)>

## Context

What forced this decision. Constraints that were already fixed before it.

## Options Considered

1. <Option A> — rejected because <reason that generalizes to future similar cases,
   not just "didn't fit this instance">
2. <Option B> — rejected because <...>
3. <Option C> — chosen, see Decision below

## Decision

One paragraph, imperative, no hedging. Name the anti-pattern explicitly where
relevant — e.g. "Do not introduce a second chunking mechanism outside
`llm.<role>.*` config; extend the existing one."

## Consequences

- Work this creates: <named item>, owner <name or "unassigned">
- What gets harder, stated plainly
- Which gate enforces this (code review checklist item, lint rule, CI check),
  and where it lives — if nothing enforces it yet, say so explicitly rather
  than implying one exists

## Revisit Triggers

<Measurable condition that reopens this question — e.g. "if pass2_chunk_size
sub-chunking is needed for a table over 200 columns", not "if this stops
working">
```

### ADR index (`specs/adr/index.md`)

```markdown
# Architecture Decision Records — Index

| # | Title | Status | Date |
|---|---|---|---|
| 0001 | Example decision | accepted | 2026-08-08 |
```

New rows are appended in numeric order; the index is the fast lookup path — an agent or human should be able to find "did we already decide this?" from this table alone, without opening individual files, for anything but the full rationale.

### Review Log — bounded live section + structure-preserving archive

Current entry shape (unchanged — this is what gets preserved on archive, not reformatted):

```markdown
**2026-06-22 — Parallel LLM Pipeline + Split Chunk Sizes**
Refactored `infer-mappings` to run Pass 1 ... [prose] ...
```

Archive destination when the live section exceeds the cap — same shape, just relocated to a yearly file:

```markdown
<!-- .session/archive/review-log-2026.md -->
# Review Log Archive — 2026

**2026-06-15 — LLM-Assisted Lineage Mapping Pipeline**
Built the complete `datasource_graph_analyzer/modeling/` package ... [prose, verbatim] ...

**2026-06-16 — Lineage Graph Model Redesign**
Replaced 1:1 Column→Transformation node model ... [prose, verbatim] ...
```

### Proposed cap (adjust if it doesn't feel right in practice)

- Keep the **8 most recent** Review Log entries live in `AGENTS.md`.
- When adding a new entry pushes the count over 8, move the oldest entries out — not just the single overflow one — to `.session/archive/review-log-<year>.md`, appending in chronological order, verbatim.
- If `review-log-<year>.md` doesn't exist yet, create it with a one-line `# Review Log Archive — <year>` header.
- An entry that straddles a year boundary archives to the year it was originally written, not the year it's archived in.

---

## Instructions

1. Locate the actual file in `dev-standards` that generates the "Session Files" / "Starting a Claude Code Session" / "Closing a Session" content (confirm the path — don't assume `modules/base.md`; check the module structure first).

2. In that file, replace the current `specs/` description (`durable, promoted decisions (always tracked)` / `[topic]-baseline.md`) with the new `specs/adr/` structure from the spec above. Update the directory tree diagram shown in that section to match.

3. Add the ADR template as its own file at the `dev-standards` source location that gets copied to `.session/specs/adr/_template.md` in consuming projects (mirror however `_template.md` for session files is currently distributed — likely the same mechanism, just a second template file).

4. Add the ADR index format (`specs/adr/index.md`) as a second template file, seeded with just the header row on first creation.

5. Update the "Closing a Session" checklist:
   - Keep step 2 ("Identify any decisions that should be promoted to `specs/` or `claude.md`") but change the promotion target: durable/architectural decisions get a new numbered file in `specs/adr/` using the template, not a freeform addition to a baseline doc.
   - Add a step: "Append the new ADR to `specs/adr/index.md`."
   - Change the Review Log update step to write a **short pointer entry** when the underlying decision has its own ADR — e.g. `"See ADR-0012 for the two-pass split rationale."` — rather than re-describing the decision in prose in both places. Prose-only Review Log entries remain fine for changes that don't rise to ADR-worthy (routine bug fixes, minor refactors).

6. Replace the existing Review Log truncation rule ("if the Review Log exceeds 10 entries, archive all but the 5 most recent to `/CHANGELOG.md`") with the new rule from the spec above: cap at 8 live entries, archive overflow verbatim (same per-entry format, no reformatting) to `.session/archive/review-log-<year>.md`, created on demand.

7. Update whatever generates a fresh project's `.session/` scaffold (if `dev-standards` has a project-init script) to create `specs/adr/` (with `_template.md` and an empty `index.md`) and `archive/` alongside the existing `.session/_template.md` on first setup.

8. Do not touch `CHANGELOG.md` conventions in this session — if a project's `dev-standards`-derived docs currently reference `CHANGELOG.md` as the Review Log archive target, that reference should be corrected to point at `.session/archive/review-log-<year>.md` instead, but `CHANGELOG.md`'s own format/purpose (release-facing) is unchanged and out of scope here.

9. After editing, verify by hand-tracing one existing overflow scenario against the new rule (e.g., using the sample Review Log entries in the spec above) to confirm the archive file would end up correctly formatted before rolling this out to real projects.

---

## Decisions Made This Session

_(none yet — pending session execution; the 8-entry cap and yearly-archive-file naming above are proposed defaults, not locked — confirm or adjust during implementation and record the final call here)_

**Implementation (2026-09-20):**
- Session-workflow content lives in `claude/base.md` (not a module); this repo's own `AGENTS.md` is a generated copy and was re-synced from it. That sync also pulled in the Logging Contract section from d17ee1c, which had never been propagated to this repo's `AGENTS.md`.
- Templates added as `claude/adr-template.md` and `claude/adr-index-template.md`, distributed by `setup-project.sh` Phase 3.5 the same way `session-template.md` is (curl, with a local fallback for the index). The ADR template has no inline fallback — on fetch failure the script warns with the manual-copy path.
- Phase 3.5 fetches the ADR templates from the `develop` URL (same default as `AGENTS.md`), not `main` like `session-template.md`; the `DEV_STANDARDS_RAW*` definitions were hoisted above Phase 3.5 to allow this. The session-template `main` URL was left as-is (out of scope).
- **Cap semantics — confirmed:** 8 live entries; on overflow, archive the oldest until 8 remain. Read "not just the single overflow one" as "drain *all* overflow in one pass" (a log already over the cap, e.g. a legacy 14-entry log, is fixed in one rotation) rather than a hysteresis trim-to-5. Trade-off: in steady state each session close archives exactly one entry.
- **Archive file naming — confirmed:** `review-log-<year>.md`, year taken from the entry's own date; a batch spanning years splits across files.
- Archive is verbatim regardless of entry shape. New shape is `**YYYY-MM-DD — Title**` + paragraph; this repo's own Review Log still uses `- date — text` bullets (3 entries, under the cap) and was not reformatted.
- `.session/archive/` is seeded with `.gitkeep` by the scaffold so the dir is tracked; the rotation rule still creates the year file on demand.
- Verified: `bash -n` + `--dry-run` on `setup-project.sh`; Phase 3.5 block executed for real against local `file://` sources (correct tree, template copied, index seeded); rotation rule simulated on a 10-entry fixture (incl. 2025→2026 boundary, spec sample entries, idempotent second run).
- Not done / known gaps: existing projects only get the new text on refresh — `refresh-dev-standards.sh` doesn't create `specs/adr/` or `archive/` (base.md tells the agent to create `specs/adr/` from the dev-standards templates if missing). Legacy `[topic]-baseline.md` files are untouched (out of scope). Templates aren't on GitHub `develop` until pushed, so a live scaffold before then hits the fallback path.
