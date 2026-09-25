# Session Handoff: Strip `embedding` Field from Assess Prompt Logs

**Status:** complete
**Date:** 2026-06-12
**Topic:** assess-log-strip-embeddings

---

## Goal

Fix the `## Raw run_history (pre-filter, as returned by get_facts_about)`
section of the `cpg assess --log-prompt` output (implemented in the
`2026-06-12-assess-prompt-logging` session) so it never includes the
`embedding` field from Fact records. Each fact's 768-dim vector is currently
being dumped in full, making the section enormous and useless for the
human-review purpose the log file exists for.

---

## Context & Constraints

### Locked decisions

- This is a filtering fix only — applied wherever the prompt-logging session
  serialized `run_history` to JSON for the log file (likely a
  `json.dumps([dict(f) for f in run_history], default=str, indent=2)` or
  similar, inside `run_assess()` in `assess.py`).
- Strip `embedding` (and any other vector-shaped fields, if `neo4j_agent_memory`
  Fact objects expose more than one — check the actual object/dict keys at
  runtime) before serialization. Do not modify `run_history` itself or
