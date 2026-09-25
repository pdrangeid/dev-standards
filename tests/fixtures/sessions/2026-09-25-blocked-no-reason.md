---
schema_version: 1
id: 2026-09-25-blocked-no-reason
title: Minimal draft session
status: blocked
status_reason: null
created: 2026-09-25
repos:
  - {name: dev-standards, role: primary}
branch: develop
links:
  depends_on: []
  supersedes: []
  split_from: null
  references: []
---
# Minimal draft session

## Goal

A draft with every template placeholder filled and an empty ledger.

## Context & Constraints

None.

## Relevant Specs / Schemas / Examples

None.

## Instructions

1. Nothing yet.

## Ledger

```yaml session-ledger
blockers:
  - {id: B1, text: Waiting on creds, kind: human_action, owner: user}
```
