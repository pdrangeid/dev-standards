Status: complete

# Session Handoff: LLM Pipeline Standards (from datasource-graph-analyzer → dev-standards → lifeos-mcp)

**Date:** 2026-08-07
**Topic:** llm-pipeline-standards

---

## Goal

Distill the two-pass LLM pipeline, chunking, and config-handling patterns proven in `datasource-graph-analyzer` into a new reusable **`llm` module** in the `dev-standards` repo (parallel in structure to the existing `neo4j` module referenced in `claude.md`), then apply that module to `lifeos-mcp` — updating its LLM-calling code, config schema, and `claude.md` module list — so that any future lifeos project doing multi-pass or chunked LLM work inherits these patterns automatically instead of re-deriving them.

---

## Context & Constraints

**Why this matters:** `datasource-graph-analyzer` iterated through several real failure modes (reasoning-model JSON refusal, chunk truncation, non-deterministic chunk boundaries, thinking-model timeouts, silent config drift) and converged on patterns that worked. Those patterns currently live only in one project's code and session history — they aren't yet captured anywhere `lifeos-mcp` or other lifeos projects would inherit them from.

**Locked decisions:**
- The distillation target is a **new dev-standards module**, following the same convention as the existing `neo4j` module (see `claude.md` header: `<!-- AUTO-GENERATED: base + modules[neo4j] -->`). This session adds `llm` to that module list.
- Standards are written **generically** — no SAP/Neo4j/graph-mapping-specific language. `datasource-graph-analyzer` is the *source example*, not the audience.
- This session does not touch `datasource-graph-analyzer` itself — it is the reference implementation, already working, out of scope for changes.
- `lifeos-mcp`'s current LLM-handling code has **not been reviewed in this session** — I don't have that repo's files in front of me. Instructions below are written to be executed inside a `lifeos-mcp` Claude Code session, where the actual current state can be inspected before changes are made.
- Two distinct pattern classes are both in scope, and the module should separate them clearly:
  1. **Two-pass pipeline design** (reasoning model → prose → extraction model → structured output)
  2. **Chunking discipline** (bounded input size, independent pass-specific chunk sizes, deterministic ordering)
- Config conventions build on top of the base standards' existing "Configuration Conventions" section (config.yaml + .env, `config.py` as sole reader) — this session adds LLM-specific sub-conventions, not a replacement.

**Out of scope:**
- Producer/consumer threading (the parallel pipeline in `2026-06-22-parallel-pipeline-and-split-chunk-sizes.md`) is a *candidate* pattern but not yet proven as a general standard — only one data point (5–10% wall-clock gain on a single table, per your own notes) exists. Document it as an "optional/advanced pattern" in the module, not a requirement.
- Model gap / graph-specific persistence patterns (`ModelGapProposal`) — these are domain-specific to the mapping tool, not general LLM pipeline standards.
- Any changes to `dev-standards`' `refresh-claude.sh` tooling itself, unless it turns out module addition requires a script change (flag if so, don't assume).
- Rewriting `lifeos-mcp`'s MCP protocol handling, tool registration, or anything unrelated to LLM call structure.

**Reference files (source project, already reviewed):**
- `llm_mapper.py` — two-pass split (`run_pass1`/`run_pass2`), never-raises error handling, thinking-token stripping
- `config.py` — `get_reasoning_params()`, `get_chat_params()`, `get_mapping_params()`, deprecation-warning pattern for renamed config keys
- `context_builder.py` — `prefilter_columns()`, `build_source_context_chunk()`
- `config.yaml` — `llm.reasoning`, `llm.chat`, `llm.mapping` blocks
- `claude.md` (this project's) — existing "Neo4j / Graph Standards" module, to use as the structural template for the new `llm` module

---

## Relevant Specs / Schemas / Examples

### Existing module convention to mirror (from this project's `claude.md`)

```markdown
<!-- AUTO-GENERATED: base + modules[neo4j] -->
<!-- Do not edit above ## Project-Specific — run refresh-claude.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->
```

The `llm` module should be addable the same way: a project's `claude.md` header becomes
`modules[neo4j, llm]` (or `modules[llm]` alone for non-graph projects), pulled in by
`setup-project.sh` / `refresh-claude.sh`.

### Config schema pattern to standardize (proven in this project)

```yaml
llm:
  reasoning:                     # Pass 1 — large/remote model, prose or long-form output
    base_url: "http://localhost:11434"
    model: "gemma3:4b"
    api_key: "ollama"
    timeout_seconds: 600
    extra_params: {}

  chat:                          # Pass 2 — small/local model, structured extraction
    base_url: "http://localhost:11434"
    model: "gemma3:4b"
    api_key: "ollama"
    timeout_seconds: 120
    max_tokens: 4096
    extra_params:
      think: false               # required for thinking-capable extraction models
      temperature: 0.0

  <domain>:                      # e.g. "mapping" — task-specific chunk sizing
    pass1_chunk_size: 25
    pass2_chunk_size: 12
```

### `config.py` accessor pattern (deprecation-safe key migration)

```python
def get_chunk_params(cfg: dict, section: str) -> dict:
    """Read pass1/pass2 chunk sizes for a given llm.<section> block.

    Falls back to a legacy single `chunk_size` key with a deprecation warning
    if the split keys are absent. Enforces a minimum floor.
    """
    m = cfg.get("llm", {}).get(section, {})
    old_chunk = m.get("chunk_size")
    pass1_raw = m.get("pass1_chunk_size")
    pass2_raw = m.get("pass2_chunk_size")

    if pass1_raw is None and pass2_raw is None and old_chunk is not None:
        logger.warning(
            "llm.%s.chunk_size is deprecated — replace with pass1_chunk_size / pass2_chunk_size",
            section,
        )
        pass1_chunk_size = pass2_chunk_size = int(old_chunk)
    else:
        pass1_chunk_size = int(pass1_raw or 25)
        pass2_chunk_size = int(pass2_raw or 12)

    MIN_CHUNK = 10
    for label, val in (("pass1_chunk_size", pass1_chunk_size), ("pass2_chunk_size", pass2_chunk_size)):
        if val < MIN_CHUNK:
            logger.warning("llm.%s.%s %d is below minimum %d — using %d", section, label, val, MIN_CHUNK, MIN_CHUNK)

    return {
        "pass1_chunk_size": max(pass1_chunk_size, MIN_CHUNK),
        "pass2_chunk_size": max(pass2_chunk_size, MIN_CHUNK),
    }
```

### Two-pass caller shape (never-raises contract)

```python
class Pass1Result(BaseModel):
    prompt_tokens: int
    generated_at: str
    prose: str                 # or other intermediate representation
    extraction_prompt: str
    error: bool = False

class TwoPassMapper:
    def run_pass1(self, prompt: str, ...) -> Pass1Result:
        """Reasoning model call. Strips <think> blocks. Never raises —
        returns Pass1Result(error=True) on any failure."""

    def run_pass2(self, item: Pass1Result) -> StructuredResult:
        """Extraction model call against Pass 1 output. Never raises —
        returns StructuredResult(parse_error=True) on any failure.
        Skips the call entirely and returns an error result if item.error is True."""

    def run(self, prompt: str, ...) -> StructuredResult:
        """Backward/simple-compatible wrapper: run_pass1() then run_pass2() in sequence."""
```

### Chunk-boundary determinism gotcha (must be called out explicitly in the module)

Any query or iteration that feeds a chunking loop **must** have a stable, explicit order.
`collect()` (or any language's unordered-aggregation equivalent) without `ORDER BY`
produces non-deterministic ordering, which silently shifts chunk boundaries across
re-runs and breaks resumability / retry logic. Always sort before chunking.

### Error-logging shape

- Never let a chunk failure crash the whole run — catch at the chunk boundary, log, continue.
- Thread the chunk index/label through every log line inside a chunked loop
  (`"chunk %d/%d"` in every warning/error), so failures are traceable without re-running.
- Cap raw-output error logging length at ERROR (e.g. first 1000 chars); log full raw output at DEBUG only.

---

## Instructions

### Part A — Author the `dev-standards` `llm` module

1. In the `dev-standards` repo, create `modules/llm.md` (confirm actual modules directory name against the existing `neo4j` module's file path before creating — do not assume the path; if `neo4j`'s module file lives elsewhere, mirror that location instead).

2. Structure `modules/llm.md` with these sections, in this order:
   - **Two-Pass Pipeline Pattern** — when to use it (a large/remote reasoning model fights structured-output instructions, e.g. emits chain-of-thought inside JSON; solution is to let Pass 1 respond in free-form prose/analysis, then delegate structured extraction to a second, smaller/faster model built for it). Include the `Pass1Result` / `run_pass1()` / `run_pass2()` shape from the spec above. State the never-raises contract as a hard rule.
   - **Chunking Discipline** — bounded chunk sizes are mandatory for any LLM call over a variable-length collection (columns, records, files, etc.); pass-specific chunk sizes are independent config values, not derived from each other; document the minimum-floor guard pattern; document the chunk-boundary determinism gotcha (`ORDER BY` / stable sort before chunking) as a named pitfall.
   - **Config Conventions for LLM Calls** — the `llm.<role>.*` YAML shape (`reasoning`, `chat`, or other role names as needed per project), the deprecation-safe key-migration accessor pattern, and the rule that `max_tokens` must always be set explicitly for extraction-role calls to prevent silent truncation on wide/large inputs.
   - **Thinking-Model Handling** — models that emit internal `<think>` blocks must have that suppressed for extraction-role calls (`think: false` in `extra_params`, or equivalent), because a thinking model doing structured extraction risks producing an incomplete JSON payload before its token budget frees up for the actual answer, or timing out mid-thought. Document how to strip `<think>...</think>` from output defensively even when suppression is requested, in case the model ignores the flag.
   - **Pre-filtering Before LLM Calls** — heuristically excluding provably-irrelevant items before they reach an LLM call reduces cost and noise; keep pre-filter logic separate from and prior to chunking; log every pre-filter exclusion with its reason at DEBUG.
   - **Optional/Advanced: Producer/Consumer Parallel Pipeline** — mark this section explicitly as *optional*, not a default requirement. Summarize the pattern (bounded `queue.Queue`, sentinel-based shutdown, one producer/one consumer thread, state files for resumability) and note the measured trade-off (single-table test showed only ~5–10% wall-clock gain; worth it mainly when Pass 1 and Pass 2 run on genuinely separate compute so they can overlap). Cite it as a follow-on pattern to reach for only after the two-pass + chunking basics are in place and proven insufficient.

3. Add a short "When NOT to use two-pass" note: single small/fast models that reliably emit valid structured output directly don't need a second extraction pass — this is an optimization for the specific failure mode of large reasoning models resisting structured output, not a universal requirement for all LLM calls.

4. Update the module-loading documentation (wherever `modules[neo4j]` is explained, likely in `dev-standards`' own README or a top-level `claude.md`) to list `llm` as an available module and give a one-line description matching the "Neo4j / Graph Standards" entry's format.



## Decisions Made This Session

### Part A — complete (dev-standards)

- Created `claude/modules/llm.md` mirroring `neo4j.md`'s structure: Two-Pass
  Pipeline Pattern (+ "When NOT to use two-pass" subsection), Chunking
  Discipline (+ determinism pitfall + error-handling), Config Conventions for
  LLM Calls (+ deprecation-safe key migration), Thinking-Model Handling,
  Pre-filtering Before LLM Calls, Optional/Advanced Producer/Consumer
  Parallel Pipeline, and a closing "What NOT to Do (LLM)" section for
  consistency with the neo4j module's convention.
- **New decision (not in original spec):** discovered a pre-existing broken
  `llm-amplifier` module entry (listed in `scripts/setup-project.sh`'s
  `MODULE_KEYS`/`MODULE_LABELS` and flagged in `claude.md`'s own Tech Debt —
  file never existed). Confirmed with user: removed `llm-amplifier` from
  `setup-project.sh` (menu array + `--modules` usage string) and replaced it
  with the new `llm` key/label. `README.md`'s Available Modules table never
  listed `llm-amplifier`, so only the `llm` row was added there, plus the
  repo-structure tree got `llm.md`.
- Removed the two now-resolved `llm-amplifier` Tech Debt / Next Steps entries
  from `dev-standards/claude.md` and renumbered Next Steps accordingly.
- Not yet done: dev-standards' own `claude.md` header still reads
  `modules[]` (bootstrap paradox, pre-existing — dev-standards doesn't
  consume its own modules) — left as-is, consistent with existing behavior.

### Part B — lifeos-mcp application: not started

Pending a session inside the `lifeos-mcp` repo to inspect its current LLM-
calling code before applying the new module, per the original session file's
locked decision that this repo's state hasn't been reviewed yet.
