---
schema_version: 1
id: YYYY-MM-DD-topic            # must equal the filename stem
title: One-line title
status: draft                   # draft | active | blocked | complete | superseded | abandoned
status_reason: null             # required when blocked or abandoned
created: YYYY-MM-DD             # must equal the id's date prefix
repos:
  - {name: repo-name, role: primary}   # exactly one primary; others secondary | reference
branch: develop
links:
  depends_on: []                # ["repo/YYYY-MM-DD-topic"]
  supersedes: []
  split_from: null
  references: []                # free-form paths/URLs
---
# <title>

<!-- Copy this file to YYYY-MM-DD-topic.md, then edit the copy. -->

## Goal

One paragraph. Specific deliverable and how "done" is judged (put the
checkable parts in the ledger as `checks`).

## Context & Constraints

Why this matters, out-of-scope items, reference files. Refer to locked
decisions by ledger ID (e.g. "see D1") instead of restating them here.

## Relevant Specs / Schemas / Examples

Actual data shapes, code fragments, commands.

## Instructions

1. Numbered, imperative steps.

## Ledger

<!--
Rules:
- Pre-session locked decisions: origin user or carried (carried needs carried_from).
- Add one runs entry per sitting; summary replaces free-form work-log bullets.
- Links point backward in time. Never edit a closed file to record later events;
  instead, a newer file's decision uses answers/supersedes with a qualified ref
  like repo/YYYY-MM-DD-topic#Q1.
- Same-file refs use "#Q1".
- Run `session-lint` on this file before closing.
-->

```yaml session-ledger
runs: []
outcome: null
decisions: []
questions: []
findings: []
checks: []
debt: []
blockers: []
produced: []
```
