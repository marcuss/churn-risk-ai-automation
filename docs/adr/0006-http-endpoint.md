# 0006 — HTTP endpoint (webhook trigger)

- **Status:** Accepted
- **Date:** 2026-06-12

## Context

The pipeline runs as a CLI (`python -m app.main`, CSV via path or stdin). Some
callers would rather **trigger it over HTTP** — e.g. a billing platform POSTing the
weekly export, or an internal scheduler — and get the formatted briefing back
synchronously. This is the assessment's Stretch A.

## Decision

Add a thin HTTP layer in `app/server.py` (Flask) that **reuses the entire
pipeline** — it adds no business logic:

- `POST /churn-risk` — body is the CSV (text). Returns JSON
  `{flagged, delivered, message}` where `message` is the formatted Slack payload
  (`text` + Block Kit `blocks`). `?deliver=true` also POSTs it to the configured
  Slack webhook; otherwise the endpoint only *returns* the briefing.
- `GET /health` — liveness check.

To avoid duplicating orchestration between CLI and HTTP, the shared
risk→summarize→fallback-alert flow moves into `app/pipeline.py`
(`summarize_flagged`), which both `app/main.py` and `app/server.py` call.

Flask is chosen for minimalism (CLAUDE.md §1): one small dependency, no framework
ceremony. It is an **optional** dependency (`pip install -e ".[api]"`) so the core
CLI stays dependency-light.

## Tradeoffs

- **(+)** Reuses all risk/AI/messaging logic — the endpoint is ~40 lines.
- **(+)** Returns the briefing for inspection without forcing delivery.
- **(−)** Adds Flask as an (optional) dependency.
- **(−)** Synchronous: a request blocks while summaries are generated (seconds for
  a dozen accounts). Fine for a weekly trigger; a high-volume caller would want a
  queue / async worker.
- **(−)** No authentication yet — intended for localhost / trusted-network use.

## Consequences

- `app/pipeline.py` is the single orchestration path; `main.py` and `server.py` are
  thin wrappers (CLI vs HTTP).
- Production would add **auth** (signed requests / token), **rate limiting**, a
  request **size cap**, and likely an **async** job model so the HTTP call returns
  immediately while work happens in the background.
- The same `ANTHROPIC_API_KEY` / `SLACK_WEBHOOK_URL` env config drives both
  entry points.
