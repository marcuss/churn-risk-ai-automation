# 0008 — LLM observability platform (e.g. Langfuse)

- **Status:** Proposed
- **Date:** 2026-06-12

## Context

Today's observability is structured-ish logs, a per-run fallback rate, a
fire-and-forget ops Slack alert ([0003](0003-graceful-degradation.md)), and an
offline eval gate ([0007](0007-evaluating-llm-output.md)). That's enough to know a
run degraded — but not enough to *operate* an AI pipeline. There is no per-call
**trace** (prompt / response / model / tokens / latency / cost), no cost or latency
trend, no drift detection, no historical eval scores, and the alerting is a single
webhook with no thresholds, deduplication, or routing. "Actionable alerts" require a
system that aggregates and reasons across many runs.

## Decision (proposed)

Integrate an LLM-observability platform — **Langfuse** (self-hostable; alternatives:
Helicone, Phoenix, LangSmith) — and instrument:

- **`llm_client` and the judge** — emit a trace per account: input signals, prompt
  version, model, response, tokens, latency, cost, and the fallback flag.
- **the eval harness** — push judge scores over time so quality regressions are
  visible across prompt versions.
- **actionable alerts on aggregates** — fallback-rate spike, cost/latency anomaly,
  eval-score drop, error rate — with thresholds, dedup, and routing, replacing the
  single ad-hoc ops webhook (which stays as a cheap fallback channel).

## Tradeoffs

- **(+)** Real operational visibility: cost, latency, drift, prompt-version
  analytics, and eval history.
- **(+)** Alerts become thresholded / deduped / routed instead of one message per
  fallback.
- **(+)** Traces make per-account debugging trivial — this is the Stretch B
  "structured per-account record", done properly.
- **(−)** Another dependency/vendor, and **prompts + account data egress** to a
  third party — mitigated by **self-hosting** Langfuse.
- **(−)** Instrumentation effort, platform cost, and operational ownership.

## Consequences

- Supersedes the MVP `SLACK_ALERT_WEBHOOK_URL` alert with platform-managed alerting.
- Closes the Stretch B gap (structured, queryable per-account records).
- Self-hosted deployment is preferred to keep account data in-house.
- Pairs with [0009](0009-serverless-aws-deployment.md): traces/metrics flow from the
  serverless workload into the platform.
