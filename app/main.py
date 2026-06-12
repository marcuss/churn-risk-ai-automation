"""Entry point: CSV -> deterministic risk -> LLM summaries -> Slack briefing.

Run with ``python -m app.main`` (so the repo root is on the import path).

Designed to always complete (CLAUDE.md §4): per-account LLM failures fall back to
deterministic summaries, and a missing Slack webhook prints the briefing instead
of sending it — which also makes a no-credentials dry run possible.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from datetime import date

from src.ai.fallback_summary import build_fallback
from src.ai.llm_client import LLMClient
from src.config import Config
from src.ingestion.csv_loader import load_accounts, load_accounts_from_path
from src.messaging import slack_client, slack_formatter
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


def run(
    accounts,
    config: Config,
    today: date,
    llm: SummaryProvider | None = None,
):
    assessments = [assess(a, today) for a in accounts]
    flagged = [a for a in assessments if a.is_flagged]
    logger.info("Assessed %d accounts; %d flagged for review", len(assessments), len(flagged))

    llm = llm if llm is not None else build_llm(config)
    summarized = [_summarize(llm, a, today) for a in flagged]

    fallbacks = [a for a in summarized if a.used_fallback]
    if fallbacks:
        logger.warning(
            "%d/%d summaries used the deterministic fallback", len(fallbacks), len(summarized)
        )
        _alert_on_fallback(config, fallbacks)

    payload = slack_formatter.build_payload(summarized)
    if config.slack_webhook_url:
        slack_client.send(config.slack_webhook_url, payload)
        logger.info("Briefing delivered to Slack")
    else:
        logger.warning("No SLACK_WEBHOOK_URL set — printing briefing instead of sending")
        print(payload["text"])
    return summarized


def _summarize(llm, assessment, today):
    if llm is None:  # configured-off path: fall back quietly, no error noise
        return dataclasses.replace(
            assessment, summary=build_fallback(assessment), used_fallback=True
        )
    return summarize_safely(llm, assessment, today)


def _alert_on_fallback(config: Config, fallbacks) -> None:
    """Post a degradation alert to the ops webhook so fallbacks aren't silent.
    Best-effort: alerting must never break the briefing itself."""
    if not config.slack_alert_webhook_url:
        return
    try:
        slack_client.send(config.slack_alert_webhook_url, slack_formatter.build_alert(fallbacks))
        logger.info("Posted fallback alert to the ops channel")
    except Exception as exc:  # noqa: BLE001 — alerting failure must not abort the run
        logger.error("Failed to post fallback alert: %s", exc)


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Weekly churn-risk briefing for Customer Success."
    )
    parser.add_argument("--csv", help="Path to the account CSV (default: read from stdin)")
    args = parser.parse_args(argv)

    config = Config.from_env()
    today = date.today()
    accounts = load_accounts_from_path(args.csv) if args.csv else load_accounts(sys.stdin)
    run(accounts, config, today)


if __name__ == "__main__":
    main()
