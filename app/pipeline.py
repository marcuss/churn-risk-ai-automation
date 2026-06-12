"""Shared orchestration: accounts -> deterministic risk -> analyst summaries.

Used by both the CLI (`app/main.py`) and the HTTP endpoint (`app/server.py`) so the
risk → summarize → fallback-alert flow lives in exactly one place. Delivery of the
final briefing (Slack post / print / HTTP response) is the caller's job.
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import date

from src.ai.fallback_summary import build_fallback
from src.ai.llm_client import LLMClient
from src.config import Config
from src.messaging import slack_client, slack_formatter
from src.models import RiskAssessment
from src.resilience.error_handler import SummaryProvider, summarize_safely
from src.risk.risk_scoring import assess

logger = logging.getLogger(__name__)


def build_llm(config: Config) -> SummaryProvider | None:
    """Return an LLM client, or None when no API key is configured. A None client
    is an expected, clean degraded mode — every summary uses the deterministic
    fallback (no per-account error/traceback)."""
    if config.anthropic_api_key:
        return LLMClient(config)
    logger.warning("No ANTHROPIC_API_KEY set — every summary will use the deterministic fallback")
    return None


def summarize_flagged(
    accounts,
    config: Config,
    today: date,
    llm: SummaryProvider | None = None,
) -> list[RiskAssessment]:
    """Score all accounts, summarize the flagged ones (with fallback), and alert on
    any degradation. Returns the summarized, flagged assessments."""
    assessments = [assess(a, today) for a in accounts]
    flagged = [a for a in assessments if a.is_flagged]
    logger.info("Assessed %d accounts; %d flagged for review", len(assessments), len(flagged))

    resolved = llm if llm is not None else build_llm(config)
    summarized = [_summarize(resolved, a, today) for a in flagged]

    fallbacks = [a for a in summarized if a.used_fallback]
    if fallbacks:
        logger.warning(
            "%d/%d summaries used the deterministic fallback", len(fallbacks), len(summarized)
        )
        _alert_on_fallback(config, fallbacks)
    return summarized


def _summarize(llm, assessment, today):
    if llm is None:  # configured-off path: fall back quietly, no error noise
        return dataclasses.replace(
            assessment, summary=build_fallback(assessment), used_fallback=True
        )
    return summarize_safely(llm, assessment, today)


def _alert_on_fallback(config: Config, fallbacks: list[RiskAssessment]) -> None:
    """Post a degradation alert to the ops webhook so fallbacks aren't silent.
    Best-effort: alerting must never break the run."""
    if not config.slack_alert_webhook_url:
        return
    try:
        slack_client.send(config.slack_alert_webhook_url, slack_formatter.build_alert(fallbacks))
        logger.info("Posted fallback alert to the ops channel")
    except Exception as exc:  # noqa: BLE001 — alerting failure must not abort the run
        logger.error("Failed to post fallback alert: %s", exc)
