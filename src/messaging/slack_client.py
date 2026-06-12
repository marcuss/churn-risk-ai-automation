"""POST the formatted briefing to a Slack incoming webhook."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def send(webhook_url: str, payload: dict, *, timeout: float = 10.0) -> None:
    """POST to a Slack incoming webhook and verify delivery.

    Slack returns a synchronous receipt: HTTP 2xx + body ``ok`` on success, an error
    status otherwise. We raise on either failure, so a non-delivered message is never
    silent. (Webhooks return no message id, so a *specific* message can't be fetched
    or re-verified later — see docs/adr/0004.)
    """
    response = requests.post(webhook_url, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.text.strip()
    if body != "ok":
        raise RuntimeError(
            f"Slack did not confirm delivery (HTTP {response.status_code}): {body!r}"
        )
    logger.info("Slack confirmed delivery (HTTP %s, 'ok')", response.status_code)
