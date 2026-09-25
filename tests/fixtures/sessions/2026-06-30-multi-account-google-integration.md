---
Status: active
Date: 2026-06-30
Topic: Multi-account Google integration (business / personal / household)
Repo: lifeos-collector
---

# Goal

Extend `lifeos-collector` to authenticate and collect from **three** distinct
Google accounts instead of one: the existing business account (Calendar
only, already working), a new **personal** account (Calendar + Gmail), and a
new **household** account shared with Paul's wife (Calendar + Gmail — bills,
travel notifications, shared event items). Rather than bolting on one-off
"personal" naming, the token-generation and connection-config pattern should
be generalized around an `account_label` so a third (or future fourth)
account follows the same shape with no new code. Classification of what
each item *is* (flight, hotel, bill, shared event, etc.) stays out of the
collector entirely and is deferred to `lifeos-ingestor`, to be derived
empirically after reviewing real sample output from all three accounts.
