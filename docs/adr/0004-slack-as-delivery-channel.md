# 0004 — Slack as the delivery channel

- **Status:** Accepted
- **Date:** 2026-06-11

## Context

The briefing currently lands in Slack by hand every Monday — an analyst pastes
summaries into the Customer Success channel. The automation must deliver to where
CS already works, with minimal new surface area. Options considered: email, a
standalone dashboard/web app, or posting to Slack.

## Decision

Deliver via a **Slack incoming webhook**, formatted with Block Kit and a
plain-text fallback, posted to the Customer Success channel (`src/messaging/`).
This matches the existing manual process exactly, just automated.

## Tradeoffs

- **(+)** Meets CS in their existing workflow; zero new UI to build or maintain.
- **(+)** Incoming webhooks are trivial to set up and POST to.
- **(+)** Block Kit gives readable, scannable formatting; the text fallback covers
  notifications and non-block clients.
- **(−)** Webhooks are fire-and-forget: no delivery guarantee, threading, or read
  receipts.
- **(−)** One-way — the briefing can't be interactive (no "acknowledge" buttons).
- **(−)** The webhook URL is a secret that must be managed (see
  [`../system_card.md`](../system_card.md)).

## Consequences

- `slack_formatter.py` is pure presentation (no risk logic) and orders accounts by
  priority; `slack_client.py` POSTs the payload.
- The webhook URL is read from the environment, never committed.
- A future iteration could move to a Slack app (interactivity, retries, richer
  delivery signals) without touching the risk or AI layers.
