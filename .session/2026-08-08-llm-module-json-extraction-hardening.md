Status: active

# Session Handoff: Add Defensive JSON Extraction Pipeline to `llm.md`

**Date:** 2026-08-08
**Topic:** llm-module-json-extraction-hardening

---

## Goal

Add a new **"Defensive JSON Extraction Pipeline"** section to the `dev-standards` `llm` module (`llm.md`, attached current version), capturing the layered sanitization pattern proven in `datasource-graph-analyzer`'s `llm_mapper.py` — think-tag stripping, code-fence stripping, trailing-comma repair, truncation recovery, and per-field non-ASCII/enum-alias normalization — as a generic extraction-hardening pattern. This closes a real gap: the current `llm.md` tells the reader to "strip `<think>...</think>` defensively" in the Thinking-Model Handling section but never shows the mechanics, and has no coverage at all for the other failure modes (markdown fences, trailing commas, mid-output truncation, tokenizer artifact contamination, model-specific enum shorthand) that the source project actually hit and fixed.

---

## Context & Constraints

**Why this matters:** You correctly recalled that this logic existed and caught real bugs in `datasource-graph-analyzer`, but it didn't make it into the last distillation pass — that pass covered the two-pass split, chunking, and config conventions, but not the JSON-safety layer that sits inside Pass 2 output handling. This session closes that gap.

**Locked decisions:**
- This is an **addition to the existing `llm.md`**, not a new module and not a rewrite. The attached current version is the base to edit.
- Keep it **generic**: the source implementation's domain-specific bits (the `_ASCII_ONLY_FIELDS` set naming `source_column`/`target_entity`/etc., and the `_ROLE_ALIASES` dict mapping SAP-mapping-specific shorthand) do **not** belong in the standards doc verbatim. The module should show the *pattern* — an allowlist of structural fields whose values get sanitized, and a per-field alias-normalization hook for known enum fields — using generic placeholder names, not the mapping tool's actual field list.
- The five-stage pipeline order is itself a locked convention worth stating explicitly, because order matters (e.g., fence-stripping before JSON parsing, sanitize-before-parse for trailing commas, but truncation recovery only *after* a parse failure, not preemptively):
  1. Strip `<think>...</think>` blocks (defense-in-depth even when `think: false` was requested)
  2. Strip markdown code fences
  3. Sanitize known syntactic LLM errors (trailing commas before `}`/`]`)
  4. Parse; on failure, attempt truncation recovery (salvage up to the last complete array element) and re-parse once
  5. Per-item field sanitization (strip non-ASCII tokenizer artifacts from structural fields only; normalize known enum aliases) — applied after parsing, before validation
- Truncation recovery must always be logged as a **partial-result** condition (`parse_ok=False` equivalent), not silently treated as success — downstream callers need to know some items past the truncation point are missing.
- Free-form/prose fields (e.g., a rationale or explanation field) are explicitly *not* subject to non-ASCII stripping — only fields that must match known structural/enum values. This distinction should be called out, since over-aggressive sanitization would corrupt legitimate model output.

**Out of scope:**
- Any change to the two-pass, chunking, or config sections already in `llm.md` — this is additive only.
- Porting the actual `_ASCII_ONLY_FIELDS` / `_ROLE_ALIASES` domain values from `datasource-graph-analyzer` — those stay in that project's `llm_mapper.py`.
- Applying this pattern to `lifeos-mcp` in this session (that's still pending the Part B inventory step from the prior handoff, `2026-08-07-llm-pipeline-standards.md`).

**Reference files:**
- `llm_mapper.py` in `datasource-graph-analyzer` — `_strip_thinking()`, `_strip_fences()`, `_sanitize_json()`, `_sanitize_item()`, `_truncation_recovery()`, `_parse_json_array()` (the orchestrator)
- `llm.md` (attached, current version) — insertion point is after "Thinking-Model Handling" and before "Pre-filtering Before LLM Calls"

---

## Relevant Specs / Schemas / Examples

### Source implementation, in pipeline order (from `llm_mapper.py`)

```python
def _strip_thinking(raw: str) -> str:
    """Remove <think>…</think> blocks that reasoning models emit.

    Handles complete blocks, orphaned </think> closing tags, and any
    surrounding whitespace. Called unconditionally on all Pass 1 output.
    """
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences (for Pass 2 JSON output)."""
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _sanitize_json(text: str) -> str:
    """Remove trailing commas before } or ] (common LLM error)."""
    return re.sub(r",\s*([\}\]])", r"\1", text)


def _truncation_recovery(text: str) -> str:
    """Attempt to salvage a truncated JSON array by closing it at the last
    complete object boundary.

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


def _sanitize_item(obj: dict, structural_fields: set[str], value_aliases: dict[str, dict[str, str]]) -> dict:
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
```

### Orchestrator (shows the required ordering + partial-result signaling)

```python
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

---

## Instructions

1. Open the current `llm.md` (attached version). Insert a new `## Defensive JSON Extraction Pipeline` section immediately **after** `## Thinking-Model Handling` and **before** `## Pre-filtering Before LLM Calls`.

2. In the new section, state the five-stage pipeline order as a numbered list (per the locked decision above), and explain *why* order matters for at least the two non-obvious orderings: fence-stripping must happen before JSON parsing (fences aren't valid JSON), and truncation recovery must only be attempted *after* a parse failure, never preemptively (most output parses cleanly; recovery is a fallback, not a first pass).

3. Include the code fragments from the spec above, but **generalize the sanitize-item signature** — use `structural_fields: set[str]` and `value_aliases: dict[str, dict[str, str]]` as parameters (as already written above) rather than hardcoding domain field names, so a reader copies the *shape* and supplies their own project's field list.

4. Add one sentence clarifying the free-form-vs-structural field distinction as its own callout (not just buried in the docstring) — this is the detail most likely to get skipped by someone copying the pattern quickly, and skipping it is what causes corrupted prose output.

5. Cross-reference this section from `## Thinking-Model Handling`: change "Strip `<think>...</think>` from output defensively even when suppression is requested" to point at the new section for the concrete implementation, so the two sections don't duplicate the think-stripping explanation.

6. Add two new bullets to `## What NOT to Do (LLM)`:
   - **Don't** treat a truncation-recovery parse as a clean success — flag it as a partial result so callers know some items are missing.
   - **Don't** sanitize free-form/prose fields for non-ASCII content — restrict sanitization to fields that must match known structural or enum values.

7. Leave every other existing section of `llm.md` unchanged — this is an additive, single-section insertion.

8. After editing, re-run whatever validates/publishes the module (if `dev-standards` has a lint or module-index check per the Part A step 4 note from the prior handoff) to confirm the new section doesn't break module loading for projects that pull `llm`.

---

## Decisions Made This Session

- Inserted `## Defensive JSON Extraction Pipeline` into `claude/modules/llm.md`
  between `## Thinking-Model Handling` and `## Pre-filtering Before LLM Calls`,
  per the locked five-stage order, with both non-obvious orderings (fence-strip
  before parse; truncation recovery only after parse failure) called out.
- Cross-referenced the new section from `## Thinking-Model Handling` instead of
  duplicating the think-stripping explanation.
- Added the two new `## What NOT to Do (LLM)` bullets (truncation-recovery ≠
  clean success; no non-ASCII sanitization on free-form/prose fields).
- Confirmed no module lint/index validation step exists in this repo
  (`scripts/*.sh` has no such check) — step 8 (re-run validator) was a no-op.
- All other sections of `llm.md` left untouched — verified via header diff
  (`Two-Pass Pipeline Pattern` → `Chunking Discipline` → `Config Conventions` →
  `Thinking-Model Handling` → **new section** → `Pre-filtering` → `Producer/
  Consumer` → `What NOT to Do`).
