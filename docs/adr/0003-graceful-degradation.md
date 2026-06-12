# 0003 — Graceful degradation

- **Status:** Accepted
- **Date:** 2026-06-11

## Context

LLM calls fail (timeouts, rate limits, transient 5xx) and sometimes return
garbage (empty, truncated, or rambling output). The weekly briefing is an
operational commitment — RevOps "shouldn't have to touch it" — so a single failed
account or call must never abort the run or block delivery.

## Decision

Each flagged account is summarized through a layered fallback (`src/resilience/`):

1. **Retry** transient failures (bounded attempts, exponential backoff).
2. **Validate** the output (non-empty, sane length); unusable output is treated
   as a failure and retried.
3. **Fall back** to a deterministic, signal-grounded summary if generation still
   fails — built from the same derived signals, so it is always usable.
4. **Continue** the batch; one account's failure is isolated from the rest.

A missing `SLACK_WEBHOOK_URL` prints the briefing instead of sending, which also
enables a no-credentials dry run. The report always completes.

## Tradeoffs

- **(+)** Reliability first: the briefing ships even during partial outages.
- **(+)** Per-account isolation: failures don't cascade.
- **(−)** Fallback prose is plainer and more templated than the LLM's.
- **(−)** Degradation can be silent; mitigated by logging each fallback and the
  per-run fallback count/rate.

## Consequences

- `src/resilience/retry.py` owns retry; `error_handler.py` owns per-account
  isolation and substitutes the fallback.
- `app/main.py` logs how many summaries fell back, so a spike is visible.
- Production would alert on fallback rate and treat a sustained spike as an
  incident.
