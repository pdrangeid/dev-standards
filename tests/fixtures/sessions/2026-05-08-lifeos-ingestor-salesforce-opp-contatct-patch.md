---
title: "SalesforceAdapter Contact-Role — Code Review & Targeted Patches"
date: 2026-05-08
status: completed
depends_on: 2026-05-08-salesforce-contact-role-adapter.md
affects:
  - lifeos-ingestor/pipeline/adapters/salesforce_adapter.py
out_of_scope:
  - lifeos-mcp changes
  - lifeos-core changes
  - Gong adapter changes
  - Stakeholder relationship-type normalization (flagged, deferred)
---

# Goal

Apply four targeted fixes to `salesforce_adapter.py`'s `_adapt_contact_roles()`
implementation. The method is structurally correct — dedup logic, stub pattern,
relationship shapes all work. The fixes address: (1) a more reliable
`accountDomain` derivation, (2) a dual-identity Account node that bridges to
the opportunity-report path, (3) a missing `sfSource` provenance flag on Account
and Opportunity nodes, and (4) a doc-string update that reflects the actual
behaviour.

