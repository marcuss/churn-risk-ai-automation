# 0005 — Modeling `subscription_status` on Recurly's lifecycle

- **Status:** Accepted
- **Date:** 2026-06-11

## Context

The assessment CSV includes a `subscription_status` field but does not enumerate
its values. The obvious placeholder enum — `active / past_due / cancelled` —
quietly encodes a wrong assumption: that a `cancelled` account is a lost cause,
to be scored as terminal or ignored. Because the source platform is **Recurly**,
we can do better than a generic guess.

## Decision

Model `subscription_status` on Recurly's real subscription lifecycle and treat
the states by *actionability*, not by label:

- **`active`** — baseline (0 risk points from status).
- **`past_due`** — in active dunning; current billing distress (+5). Kept
  distinct from `failed_payment_count_last_30d`: status is *current state*, the
  count is *severity*.
- **`canceled`** — *set to not renew, but still active and paying through
  `contract_end_date`.* This is the highest-value save target, not a churned
  account. Weighted highest (+10, auto-flags) and surfaced first.
- **`expired`** — already churned; **filtered out before scoring.** A
  churn-*risk* report is about accounts that can still be saved.

## Tradeoffs

- **(+)** Aligns the model with how CS actually works: the report becomes a queue
  of *savable* accounts, and the most time-sensitive (`canceled` near renewal)
  rise to the top.
- **(+)** Excluding `expired` keeps the briefing actionable and short.
- **(−)** Couples the enum to Recurly semantics; a different billing source would
  need re-mapping at ingestion.
- **(−)** `canceled` auto-flagging means a re-subscribed account could linger in
  the report until the next export reflects the change — acceptable for a weekly
  batch.

## Consequences

- Scoring treats `canceled` as the strongest single signal and never scores
  `expired`.
- The sample dataset includes one `canceled`-near-renewal account (expected top
  of the briefing) and one `expired` account (expected absent) so the behavior is
  observable, not just asserted.
- Ingestion is the single place responsible for mapping raw status strings to
  this enum and dropping `expired` rows.
