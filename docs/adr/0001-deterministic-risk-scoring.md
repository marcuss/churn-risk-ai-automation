# 0001 — Deterministic risk scoring

- **Status:** Accepted
- **Date:** 2026-06-11

## Context

The system must decide which accounts are "at risk" each week. Two broad options:
let an LLM (or a learned classifier) judge risk from the account fields, or encode
risk as explicit deterministic rules. This decision is the spine of the whole
pipeline — everything downstream (prompting, fallback, eval) depends on it.

## Decision

Risk qualification is **100% deterministic**, implemented as point-weighted rules
in `src/risk/` with a flag threshold of score ≥ 6. The weights, bands, and
threshold are specified in [`../risk_strategy.md`](../risk_strategy.md). The LLM
plays **no part** in deciding risk (see [0002](0002-llm-only-for-summarization.md)).

## Tradeoffs

- **(+)** Explainable: every flag traces to specific signals and points.
- **(+)** Debuggable and consistent: same input → same decision, always.
- **(+)** Cheap and fast: no model call to qualify; the 324-state space is small
  enough to reason about and unit-test exhaustively by archetype.
- **(+)** Makes the LLM eval small — it only has to grade prose, not correctness.
- **(−)** Weights are hand-tuned, not learned from outcomes; they encode judgment,
  not measured churn probability.
- **(−)** Cannot capture subtle cross-signal interactions an ML model might find.
- **(−)** Requires manual recalibration as the business changes.

## Consequences

- All risk logic lives in `src/risk/` and is covered by behavioral tests
  (archetypes + threshold boundaries).
- The threshold is the primary tuning knob; production would calibrate it against
  historical churn outcomes (see README → production notes).
- Because the decision is deterministic, the rest of the system can treat
  "is_flagged" as ground truth and focus its quality effort on the narrative.
