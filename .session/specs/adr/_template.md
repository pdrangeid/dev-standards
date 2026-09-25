---
tags: []
domain: ""
scope: ""
created: YYYY-MM-DD
---
# ADR-NNNN: <Title>

<!-- Copy this file to NNNN-short-title.md (next unused number), then edit the copy.
     Numbers are permanent: never reuse, never renumber. Supersede via Status, don't delete. -->

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
