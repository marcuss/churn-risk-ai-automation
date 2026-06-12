# 0009 — Serverless deployment on AWS (Lambda + Step Functions)

- **Status:** Proposed
- **Date:** 2026-06-12

## Context

The brief's north star is *"We want this to just happen. We shouldn't have to touch
it."* Today this is a CLI + HTTP app that **someone** must schedule, run, and
operate — exactly the touch the mandate rejects. Truly hands-off operation needs
managed scheduling, durable per-step retries, and no servers to patch.

## Decision (proposed)

Run the whole workload **serverless on AWS**, with no always-on infrastructure:

- **EventBridge Scheduler** fires the weekly run; alternatively an **S3 event** when
  the billing CSV lands in a bucket kicks it off — realizing the Stretch A "webhook
  trigger" ([0006](0006-http-endpoint.md)) natively.
- **Step Functions** orchestrates: ingest → score → a **Map** state fanning out one
  summary per account → format → deliver. Step Functions' native **retry / catch**
  gives durable, per-account retry at the orchestration layer (no custom retry
  code), with failures routed to a DLQ + alert.
- **Lambda** runs each step; the existing `app/pipeline.py` split (ingestion / risk
  / summary / delivery) maps almost one-to-one onto functions.
- **Secrets Manager / SSM** for the API key and webhooks; **CloudWatch** plus the
  observability platform ([0008](0008-llm-observability-platform.md)) for
  traces and alerts.

## Tradeoffs

- **(+)** No servers to manage or patch; auto-scales; pay-per-use (a weekly batch is
  nearly free).
- **(+)** **Durable retries** and partial-failure handling become a platform
  feature, not our code — strengthening the graceful degradation of
  [0003](0003-graceful-degradation.md).
- **(+)** Native scheduling + S3/event triggers fulfil the "just happen" mandate
  directly.
- **(−)** AWS lock-in; cold starts (negligible for a weekly batch).
- **(−)** Local dev/test is harder (needs SAM / LocalStack), and it requires IaC
  (CDK / SAM / Terraform) plus Step Functions state-machine modeling to maintain.

## Consequences

- The deterministic/LLM split and the shared `app/pipeline.py` already factor
  cleanly into discrete Lambdas; the HTTP endpoint becomes API Gateway + Lambda, and
  the CLI stays for local/dev.
- Adds an IaC project; CI would deploy the stack.
- Combined with [0008](0008-llm-observability-platform.md), the system becomes
  genuinely operate-itself: scheduled, retried, observed, and alerted — no human in
  the loop until an alert fires.
