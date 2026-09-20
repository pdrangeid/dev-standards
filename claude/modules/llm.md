# Claude Module: LLM Pipeline Standards

Two-pass pipeline design, chunking discipline, and config conventions for any
project that drives an LLM over variable-length input — chat, extraction,
classification, or reasoning calls of any kind. These are structural
patterns, not vendor- or domain-specific instructions.

---

## Two-Pass Pipeline Pattern

Some large/remote reasoning models fight structured-output instructions —
they emit chain-of-thought prose inside what's supposed to be a JSON
payload, or wrap output in explanation the caller didn't ask for. The fix is
not tighter prompting; it's splitting the call in two:

1. **Pass 1 (reasoning)** — let a large/remote model respond in free-form
   prose or analysis, with no structured-output constraint at all.
2. **Pass 2 (extraction)** — hand Pass 1's output to a second, smaller/faster
   model built for structured extraction, and constrain *that* call's output
   format.

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

**Never-raises contract (hard rule):** `run_pass1()` and `run_pass2()` must
never raise on a model/parse failure — they return an `error`/`parse_error`
result instead. A single bad call must not crash the run; callers decide how
to handle an error result, not `try`/`except` around every call site.

### When NOT to use two-pass

A single small/fast model that reliably emits valid structured output
directly does not need a second extraction pass. Two-pass is a fix for one
specific failure mode — large reasoning models resisting structured output —
not a default requirement for every LLM call.

---

## Chunking Discipline

Any LLM call over a variable-length collection (columns, records, files,
rows, chunks of text) **must** use a bounded chunk size — never send an
unbounded collection in one call.

- Pass-specific chunk sizes are independent config values, not derived from
  one another (e.g. `pass1_chunk_size` and `pass2_chunk_size` are set
  separately, not `pass2 = pass1 / 2`).
- Enforce a minimum-floor guard on every configured chunk size so a
  misconfigured `0` or `1` doesn't silently degenerate the run:

  ```python
  MIN_CHUNK = 10
  for label, val in (("pass1_chunk_size", pass1_chunk_size), ("pass2_chunk_size", pass2_chunk_size)):
      if val < MIN_CHUNK:
          logger.warning("llm.%s.%s %d is below minimum %d — using %d", section, label, val, MIN_CHUNK, MIN_CHUNK)
  ```

### Chunk-boundary determinism (named pitfall)

Any query or iteration that feeds a chunking loop **must** have a stable,
explicit order. `collect()` (or any language's unordered-aggregation
equivalent) without an explicit `ORDER BY` produces non-deterministic
ordering, which silently shifts chunk boundaries across re-runs and breaks
resumability / retry logic. Always sort before chunking.

### Error handling inside a chunked loop

- Never let a chunk failure crash the whole run — catch at the chunk
  boundary, log, continue.
- Thread the chunk index/label through every log line inside a chunked loop
  (`"chunk %d/%d"` in every warning/error) so failures are traceable without
  re-running.
- Cap raw-output error logging length at `ERROR` (e.g. first 1000 chars);
  log the full raw output at `DEBUG` only.

---

## Config Conventions for LLM Calls

Builds on the base standards' Configuration Conventions
(`config.yaml` + `.env`, `config.py` as sole reader) — this section adds
LLM-specific sub-conventions, not a replacement.

```yaml
llm:
  reasoning:                     # Pass 1 — large/remote model, prose or long-form output
    base_url: "http://localhost:11434"
    model: "gemma3:4b"
    api_key: "ollama"
    timeout_seconds: 600
    extra_params: {}

  extraction:                          # Pass 2 — small/local model, structured 
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

- Role names (`reasoning`, `chat`, or other names as a project needs them)
  are config sections under `llm.*` — never hardcode model names, base URLs,
  or timeouts in source.
- `max_tokens` **must** always be set explicitly for extraction-role calls —
  an unset/default token budget risks silent truncation on wide or large
  inputs, producing a partial payload that fails to parse instead of an
  obvious error.

### Deprecation-safe key migration

When renaming a config key, read both the old and new names, warn once on
the old path, and never make the caller migrate blind:

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

---

## Thinking-Model Handling

Models that emit internal `<think>...</think>` blocks must have that
suppressed for extraction-role calls — set `think: false` (or the
equivalent flag for the provider) in `extra_params`. A thinking model doing
structured extraction risks producing an incomplete JSON payload before its
token budget frees up for the actual answer, or timing out mid-thought.

Suppression flags are not universally honored. Strip `<think>...</think>`
from output defensively even when suppression is requested, in case the
model ignores the flag — never assume the flag alone is sufficient. See
**Defensive JSON Extraction Pipeline** below for the concrete
implementation.

---

## Defensive JSON Extraction Pipeline

Extraction-role output ("return a JSON array") fails in more ways than just
unsuppressed `<think>` blocks: markdown code fences around the payload,
trailing commas before `}`/`]`, mid-output truncation from a token-budget
cutoff, and stray non-ASCII tokenizer artifacts or model-specific enum
shorthand inside individual fields. Treat all of these as expected failure
modes of extraction calls, not edge cases — parse defensively, in a fixed
stage order.

### Pipeline order (fixed — order matters)

1. Strip `<think>...</think>` blocks (defense-in-depth even when `think:
   false` was requested)
2. Strip markdown code fences
3. Sanitize known syntactic LLM errors (trailing commas before `}`/`]`)
4. Parse; on failure, attempt truncation recovery (salvage up to the last
   complete array element) and re-parse once
5. Per-item field sanitization (strip non-ASCII tokenizer artifacts from
   structural fields only; normalize known enum aliases) — applied *after*
   parsing, *before* validation

Two orderings are non-obvious and must not be swapped:

- **Fence-stripping before parsing.** A fenced payload (```` ```json ... ``` ````)
  is not valid JSON as-is — parsing before stripping fences always fails,
  even when the payload inside is perfectly well-formed.
- **Truncation recovery only after a parse failure, never preemptively.**
  Most output parses cleanly on the first try; recovery is a fallback that
  discards data (everything past the last complete element), so it must
  never run against output that would otherwise have parsed intact.

### Implementation shape

```python
def _strip_thinking(raw: str) -> str:
    """Remove <think>…</think> blocks that reasoning models emit.

    Handles complete blocks, orphaned </think> closing tags, and any
    surrounding whitespace. Called unconditionally on all extraction output.
    """
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences around a JSON payload."""
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _sanitize_json(text: str) -> str:
    """Remove trailing commas before } or ] (common LLM error)."""
    return re.sub(r",\s*([\}\]])", r"\1", text)


def _truncation_recovery(text: str) -> str:
    """Salvage a truncated JSON array by closing it at the last complete
    object boundary.

    When a model hits its max_tokens limit mid-output, the JSON array is cut
    off somewhere inside an incomplete object. This finds the last '},' or
    '}' that closes a complete item, discards everything after it, and
    appends ']' to produce a valid (partial) array.

    Returns the original text unchanged if no recovery boundary is found.
    """
    last_close = text.rfind('},')
    if last_close == -1:
        last_close = text.rfind('}')
    if last_close == -1:
        return text
    recovered = text[:last_close + 1].rstrip() + '\n]'
    logger.warning(
        "Truncated JSON — salvaged array up to char %d (original: %d chars); "
        "items past truncation point are missing", last_close, len(text),
    )
    return recovered


def _sanitize_item(
    obj: dict, structural_fields: set[str], value_aliases: dict[str, dict[str, str]]
) -> dict:
    """Strip non-ASCII tokenizer artifacts from a parsed JSON item.

    Keys are always sanitized — field names must be ASCII identifiers.
    Values are sanitized only for fields listed in `structural_fields` (values
    that must match known identifiers/enums). Free-form prose fields are left
    untouched — over-sanitizing legitimate model output corrupts it.

    `value_aliases`: {field_name: {model_shorthand: canonical_value}} — lets
    known model-specific shorthand (e.g. a smaller model abbreviating an enum
    value) get normalized before validation instead of failing schema checks.
    """
    result = {}
    for k, v in obj.items():
        clean_key = re.sub(r'[^\x00-\x7F]', '', k).strip()
        if clean_key in structural_fields and isinstance(v, str):
            clean_val = re.sub(r'[^\x00-\x7F]', '', v).strip()
            aliases = value_aliases.get(clean_key, {})
            clean_val = aliases.get(clean_val, clean_val)
            if clean_val != v:
                logger.warning("Sanitized value of '%s': %r -> %r", clean_key, v, clean_val)
            result[clean_key] = clean_val
        else:
            if clean_key != k:
                logger.warning("Sanitized non-ASCII key: %r -> %r", k, clean_key)
            result[clean_key] = v
    return result


def _parse_json_array(raw: str, label: str = "") -> tuple[list[dict], bool]:
    """Parse extraction-model output into a list of items.

    Returns (items, parse_ok). parse_ok is False on unrecoverable failure
    AND when truncation recovery was used — callers must treat a recovered
    result as partial, not a clean success.
    """
    cleaned = _strip_thinking(_strip_fences(raw))
    cleaned = _sanitize_json(cleaned)
    partial = False

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed%s: %s\nRaw (first 1000 chars):\n%s", label, exc, raw[:1000])
        logger.debug("Full raw output%s:\n%s", label, raw)

        recovered = _truncation_recovery(cleaned)
        if recovered != cleaned:
            try:
                parsed = json.loads(recovered)
                partial = True
            except json.JSONDecodeError:
                return [], False
        else:
            return [], False

    if not isinstance(parsed, list):
        logger.error("Expected a JSON array, got %s", type(parsed).__name__)
        return [], False

    items = [_sanitize_item(i, STRUCTURAL_FIELDS, VALUE_ALIASES) if isinstance(i, dict) else i for i in parsed]
    return items, not partial
```

`structural_fields` and `value_aliases` are supplied per-project — copy the
*shape* of `_sanitize_item`, not a hardcoded field list.

**Structural vs. free-form fields:** only sanitize values for fields that
must match a known identifier or enum (`structural_fields`). Never run
non-ASCII stripping on free-form/prose fields (a rationale, explanation, or
summary field) — those are legitimate model output, and stripping non-ASCII
characters from them corrupts the content instead of fixing an error.

---

## Pre-filtering Before LLM Calls

Heuristically excluding provably-irrelevant items *before* they reach an LLM
call reduces both cost and noise in the output.

- Keep pre-filter logic separate from, and prior to, chunking — pre-filter
  the full collection first, then chunk what remains.
- Log every pre-filter exclusion with its reason at `DEBUG`, so an
  unexpectedly-missing item can be traced back to why it was dropped.

---

## Optional/Advanced: Producer/Consumer Parallel Pipeline

**This is an optional pattern, not a default requirement.** Reach for it
only after the two-pass + chunking basics above are in place and have
proven insufficient.

Shape: a bounded `queue.Queue`, one producer thread and one consumer thread,
sentinel-based shutdown, and state files for resumability so a killed run
can pick back up rather than restart from scratch.

Measured trade-off: a single-table test showed only ~5–10% wall-clock gain.
It's worth the added complexity mainly when Pass 1 and Pass 2 run on
genuinely separate compute so they can overlap — not as a general
throughput fix.

---

## What NOT to Do (LLM)

- **Don't** send an unbounded collection to an LLM call — always chunk, with
  an explicit minimum-floor guard on the configured size
- **Don't** derive one pass's chunk size from another's — set them
  independently in config
- **Don't** iterate an unordered aggregation into a chunking loop — sort
  first, or chunk boundaries silently shift across re-runs
- **Don't** let `run_pass1()` / `run_pass2()` raise on failure — return an
  error result and let the caller decide
- **Don't** leave `max_tokens` unset on an extraction-role call — silent
  truncation produces an unparseable payload instead of a clear error
- **Don't** trust a thinking-suppression flag alone — strip
  `<think>...</think>` from output defensively regardless
- **Don't** treat a truncation-recovery parse as a clean success — flag it
  as a partial result so callers know some items are missing
- **Don't** sanitize free-form/prose fields for non-ASCII content —
  restrict sanitization to fields that must match known structural or enum
  values
- **Don't** reach for the producer/consumer parallel pipeline before the
  two-pass + chunking basics are proven insufficient
- **Don't** hardcode model names, base URLs, or timeouts in source — always
  via `llm.<role>.*` config
