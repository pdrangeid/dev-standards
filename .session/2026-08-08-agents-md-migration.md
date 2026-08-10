Status: complete

# Session Handoff: Migrate `claude.md` → `AGENTS.md` + Rename `refresh-claude.sh`

**Date:** 2026-08-08
**Topic:** agents-md-migration

---

## Goal

In the `dev-standards` repo, rename `refresh-claude.sh` to `refresh-dev-standards.sh`, change its generation target from `claude.md` to `AGENTS.md` (same module-concatenation logic, new filename and header wording), and give the renamed script a self-migration mode so that running it against an already-existing project automatically converts that project's legacy `claude.md` into `AGENTS.md` plus a `CLAUDE.md` bridge stub — without touching that project's hand-authored `## Project-Specific` content. This is the prerequisite for the ADR/Review-Log handoff (`2026-08-08-adr-adoption-and-review-log-archiving.md`), which assumes the `AGENTS.md` structure already exists — run this session first.

---

## Context & Constraints

**Why this matters:** `dev-standards` currently generates and distributes `claude.md` per project via `refresh-claude.sh`. Every project that pulls the standards has a `claude.md` with an auto-generated header block plus a hand-authored `## Project-Specific` tail. Migrating to `AGENTS.md` as the cross-tool canonical file means changing what the script writes, what it's called, and — since existing projects already have a `claude.md` with real content in it — how already-migrated-once projects get moved over without data loss or manual per-project surgery across four machines.

**Locked decisions (from discussion):**
- `AGENTS.md` becomes the canonical generated file. Content and generation logic (module concatenation from `dev-standards`) are unchanged — only the output filename and the header/footer marker text change.
- The `CLAUDE.md` bridge uses Claude Code's documented `@AGENTS.md` import syntax, **not a symlink**. This was already decided earlier in this project: the import allows a Claude-specific tail section to coexist below it, and creating a symlink on Windows requires Administrator privileges or Developer Mode while the import works everywhere with no setup. The stub is exactly:
  ```markdown
  @AGENTS.md

  ## Claude Code
  ```
  (Claude-specific additions, if any, go below that header — see Instructions for how migration must preserve any that already exist.)
- **Do not** create `.cursorrules`, `GEMINI.md`, or any other tool-specific bridge file in this session. Most current tools (Cursor, Windsurf, Cline, Codex) already auto-discover `AGENTS.md` at the repo root natively — manufacturing redundant bridge files without first verifying each tool's current behavior would just be more files to keep in sync for no benefit. That verification, if any bridge turns out to be needed, is separate future work.
- The centralized-checkout `.claude/rules/` symlink distribution model (single `~/dev-standards` checkout linked into every project) is **out of scope for this session**. This session only changes what the generation script produces and what it's named — it does not change how projects currently pull `dev-standards` in the first place (whatever fetch/copy mechanism `refresh-claude.sh` uses today stays as-is). That's a separate, larger future session.
- Migration must be **idempotent**: running the renamed script a second time against an already-migrated project must not duplicate content, re-trigger migration logic, or clobber a hand-edited `CLAUDE.md` tail — it should fall through to the normal (non-migration) refresh path.
- The `## Project-Specific` section in an existing `claude.md` is user-authored, per-project content and must survive the rename to `AGENTS.md` byte-for-byte.
- If a project's `CLAUDE.md` already exists with content that doesn't match the known generated-stub pattern (i.e., someone hand-wrote something else there), the migration must **not** silently overwrite it — abort just that step and warn, rather than guessing.

**Out of scope:**
- The ADR/Review-Log content changes (separate handoff, already written, run after this one).
- The `.claude/rules/` centralized checkout/symlink model.
- Creating any non-Claude tool-specific bridge files.
- Retroactively renumbering or restructuring anything inside the module content itself (`llm`, `neo4j`, base) — this session only touches the delivery mechanism (filename, script name, migration), not the standards content.

**Reference files:**
- `refresh-claude.sh` and `setup-project.sh` in `dev-standards` — **not reviewed in this session**, I don't have this repo's files in front of me. The instructions below describe the required behavior; confirm the actual current implementation before changing it, rather than assuming it matches the pseudocode in this handoff.
- The current generated-file header/footer convention (confirmed from a project that already pulls `dev-standards`):
  ```markdown
  <!-- AUTO-GENERATED: base + modules[neo4j] -->
  <!-- Do not edit above ## Project-Specific — run refresh-claude.sh to update -->
  <!-- dev-standards: https://github.com/pdrangeid/dev-standards -->
  ```
- `setup-project.sh` is the separate bootstrap script for brand-new projects (per existing `dev-standards` docs: "auto-fetched by `setup-project.sh` and `refresh-claude.sh`") — it also needs updating so new projects get the `AGENTS.md`/`CLAUDE.md` structure from the start, with no migration logic needed there since there's no legacy file to detect.

---

## Relevant Specs / Schemas / Examples

### Target header/footer wording (post-migration)

```markdown
<!-- AUTO-GENERATED: base + modules[neo4j] -->
<!-- Do not edit above ## Project-Specific — run refresh-dev-standards.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->
```

(Only the script name in the second line changes; module list and everything else stays the same format.)

### `CLAUDE.md` stub (generated, both for migration and for new projects)

```markdown
@AGENTS.md

## Claude Code
```

If migration finds an *existing* `CLAUDE.md` whose content is exactly this stub (with or without additional lines below `## Claude Code`), treat everything from `## Claude Code` onward as user content to preserve verbatim — only the `@AGENTS.md` import line itself is guaranteed to be regenerated identically.

### Legacy-state detection (for migration mode)

A project is in "legacy state" if:
- `claude.md` exists, **and**
- either `AGENTS.md` does not exist, **or** `claude.md`'s header still contains the string `refresh-claude.sh` (i.e., it was generated by the old script name)

A project is in "already migrated" state if `AGENTS.md` exists with a header referencing `refresh-dev-standards.sh` — in that state, skip migration entirely and run the normal refresh.

### Migration steps (pseudocode)

```bash
if legacy_state_detected; then
  # 1. Split out the Project-Specific section
  project_specific=$(extract_after_marker "claude.md" "## Project-Specific")

  # 2. Regenerate the auto-generated portion under the new name/header
  generate_module_content > AGENTS.md.new
  rewrite_header_wording AGENTS.md.new  # refresh-claude.sh -> refresh-dev-standards.sh
  echo "$project_specific" >> AGENTS.md.new
  mv AGENTS.md.new AGENTS.md
  rm claude.md   # only after AGENTS.md is confirmed written

  # 3. Handle CLAUDE.md
  if [ ! -f CLAUDE.md ]; then
    write_claude_stub > CLAUDE.md
  elif matches_known_stub_pattern CLAUDE.md; then
    preserve_user_additions_below_header CLAUDE.md
  else
    warn "CLAUDE.md exists with unrecognized content — not touching it. Add '@AGENTS.md' manually if desired."
  fi

  log "Migrated: claude.md -> AGENTS.md; CLAUDE.md created/updated (see above)"
else
  run_normal_refresh   # existing module-pull + regenerate logic, unchanged
fi
```

---

## Instructions

1. Open `dev-standards` and locate `refresh-claude.sh` and `setup-project.sh`. Read their current implementation in full before changing anything — confirm the actual module-fetch and header-generation logic matches (or note where it differs from) the pseudocode above.

2. Rename `refresh-claude.sh` to `refresh-dev-standards.sh` using `git mv` (preserve file history). Search the repo for any other references to the old filename — README, other scripts, module docs, code comments — and update them. Do not rely on the generated header text alone to "self-heal"; hardcoded mentions elsewhere won't update themselves.

3. Inside the renamed script, change the generation target from `claude.md` to `AGENTS.md`. The module-concatenation logic itself (fetching `base` + whichever modules a project's header lists) is unchanged — only the output filename and the two lines of header/footer wording shown in the spec above.

4. Add legacy-state detection to the script per the spec above (`claude.md` exists AND (no `AGENTS.md` OR old script name in header)).

5. Implement the migration path:
   - Extract the `## Project-Specific` section from `claude.md` verbatim before regenerating anything.
   - Regenerate the auto-generated portion fresh (same as a normal refresh would), append the preserved Project-Specific section, write to `AGENTS.md`, then remove `claude.md` — only after confirming `AGENTS.md` was written successfully. Don't delete `claude.md` first.
   - Handle `CLAUDE.md` per the three-way branch in the spec (create stub / preserve existing stub's user additions / warn-and-skip on unrecognized content).
   - Log a one-line summary of what was migrated, so the migration is auditable in the commit that results from running it.

6. Make the migration idempotent: after migration, the project is in "already migrated" state (per the detection logic above) and a second run must take the normal refresh path, not re-run migration logic. Test this explicitly — run the script twice in a row against a freshly migrated project and confirm the second run makes no unexpected changes.

7. Update `setup-project.sh` so brand-new projects get `AGENTS.md` + the `CLAUDE.md` stub generated directly — no migration branch needed there, since there's no legacy file for a new project to have.

8. Update `dev-standards`' own top-level README (and any other docs that describe the workflow) to reflect the new script name and the `AGENTS.md` + `CLAUDE.md`-stub structure. Remove or update any remaining `claude.md`-centric language so new readers aren't following stale instructions.

9. Test end-to-end against at least one real, already-existing project (e.g. `datasource-graph-analyzer`, which is already reviewed in this project's context) by running the renamed script's migration path against it and confirming:
   - `AGENTS.md` content matches the old `claude.md` content except for the header wording change
   - `CLAUDE.md` contains exactly the two-line stub (assuming no prior `CLAUDE.md` existed)
   - The `## Project-Specific` section is byte-for-byte unchanged
   - Running the script a second time produces no migration-specific output — just a normal refresh

10. Do not start the ADR/Review-Log handoff (`2026-08-08-adr-adoption-and-review-log-archiving.md`) until step 9 passes on at least one real project — that handoff's instructions assume `AGENTS.md` already exists and reference it by name throughout.

---

## Decisions Made This Session

- Session resumed after an earlier interruption; found the core work (script rename/rewrite,
  migration logic, `setup-project.sh`, README, `docs/usage_instructions.md`, this repo's own
  `AGENTS.md`/`CLAUDE.md`) already implemented and matching the spec. Verified rather than
  re-did it, then completed the remaining gaps below.
- Found `claude/base.md` and `claude/HEADER.md` — the actual module content fetched into every
  generated file — still said `claude.md`/`refresh-claude.sh` throughout their body text (not
  just the header comment, which was already correct). Instruction #2/#8 explicitly call out
  updating "module docs," and this is a reference update (filenames/script names), not the
  content restructuring the handoff put out of scope — so fixed it: `claude.md` → `AGENTS.md`,
  `refresh-claude.sh` → `refresh-dev-standards.sh` throughout, and added `CLAUDE.md` to the
  File & Directory Structure tree since `setup-project.sh` now always generates it.
- Re-synced this repo's own `AGENTS.md` (generated by a prior migration pass before the
  `base.md` fix above) so its auto-generated portion matches the corrected `base.md` exactly.
- Ran the full test matrix from the spec in an isolated scratchpad sandbox before touching any
  real project: dry-run migration (no files written), real migration (Project-Specific
  preserved byte-for-byte, `claude.md` removed, `CLAUDE.md` stub created), a second run
  (idempotent — took the normal-refresh path, byte-identical output, no `claude.md`
  resurrection), and all three `CLAUDE.md` branches (create-new / preserve-existing-stub's
  user additions / warn-and-skip on unrecognized content).
- Ran the real end-to-end test (step 9) against `datasource-graph-analyzer`
  (`/home/pdrangeid/Projects/datasource-graph-analyzer`), the project named in the handoff.
  Confirmed: `AGENTS.md` content matches old `claude.md` except header wording,
  `## Project-Specific` preserved byte-for-byte, `CLAUDE.md` stub created, and a second run
  took the normal refresh path with no migration output. Left the result uncommitted in that
  repo — it already had unrelated uncommitted changes in flight, so committing there wasn't
  this session's call to make.
- Discovered mid-test that `datasource-graph-analyzer` had a pre-existing (untracked)
  `GEMINI.md` symlink pointing at `claude.md`; migration deleting `claude.md` left it dangling.
  This wasn't anticipated by the handoff (which explicitly scoped out *creating* new
  tool-specific bridge files, but said nothing about *existing* ones breaking). Asked the user;
  they chose to repoint it to `AGENTS.md` rather than leave it dangling or leave it out of
  scope. Not generalized into script logic — this session's migration script still only
  handles `claude.md`/`AGENTS.md`/`CLAUDE.md`; any future project with a similar dangling
  symlink needs the same manual fix until/unless that's promoted into the script.
- `claude/modules/llm.md` has unrelated in-progress, uncommitted changes from a different,
  separately-interrupted session (`.session/2026-08-08-llm-module-json-extraction-hardening.md`).
  Left untouched and unstaged — not part of this session's commit.
