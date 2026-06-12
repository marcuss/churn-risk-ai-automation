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

1. **Retry** transient failures (bounded attempts, exponential backoff) —
   [`src/resilience/retry.py`](../../src/resilience/retry.py).
2. **Validate** the output (non-empty, sane length); unusable output is treated as
   a failure and retried —
   [`_validate` in `src/ai/llm_client.py`](../../src/ai/llm_client.py).
3. **Fall back** to a deterministic, signal-grounded summary if generation still
   fails — [`src/ai/fallback_summary.py`](../../src/ai/fallback_summary.py).
4. **Continue** the batch; one account's failure is isolated from the rest —
   [`summarize_safely` in `src/resilience/error_handler.py`](../../src/resilience/error_handler.py).

A missing `SLACK_WEBHOOK_URL` prints the briefing instead of sending, which also
enables a no-credentials dry run. The report always completes.

## Tradeoffs

- **(+)** Reliability first: the briefing ships even during partial outages.
- **(+)** Per-account isolation: failures don't cascade.
- **(−)** Fallback prose is plainer and more templated than the LLM's.
- **(−)** Degradation can be silent; mitigated by logging each fallback, the
  per-run fallback count, and an **ops alert** posted to a separate Slack webhook
  (`SLACK_ALERT_WEBHOOK_URL`) naming any account that fell back.

## Consequences

- `src/resilience/retry.py` owns retry; `error_handler.py` owns per-account
  isolation and substitutes the fallback.
- `app/main.py` logs how many summaries fell back and, when
  `SLACK_ALERT_WEBHOOK_URL` is set, posts a degradation alert to a separate ops
  channel — so a fallback is never silent. Alerting is best-effort and never
  aborts the briefing ([`_alert_on_fallback`](../../app/main.py)).
- Production would also alert on sustained fallback *rate* and treat it as an
  incident.
