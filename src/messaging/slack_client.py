"""POST the formatted briefing to a Slack incoming webhook."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def send(webhook_url: str, payload: dict, *, timeout: float = 10.0) -> None:
    response = requests.post(webhook_url, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.info("Posted churn-risk briefing to Slack (HTTP %s)", response.status_code)
