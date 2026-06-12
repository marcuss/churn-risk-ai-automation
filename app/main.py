"""CLI entry point: CSV -> deterministic risk -> LLM summaries -> Slack briefing.

Run with ``python -m app.main`` (so the repo root is on the import path).

Orchestration lives in `app/pipeline.py` (shared with the HTTP endpoint). This
module only handles CLI input and final delivery. A missing Slack webhook prints
the briefing instead of sending it, which also enables a no-credentials dry run.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from app.pipeline import summarize_flagged
from src.config import Config
from src.ingestion.csv_loader import load_accounts, load_accounts_from_path
from src.messaging import slack_client, slack_formatter
from src.resilience.error_handler import SummaryProvider

logger = logging.getLogger(__name__)


def run(accounts, config: Config, today: date, llm: SummaryProvider | None = None):
    summarized = summarize_flagged(accounts, config, today, llm)
    payload = slack_formatter.build_payload(summarized)
    if config.slack_webhook_url:
        slack_client.send(config.slack_webhook_url, payload)
        logger.info("Briefing delivered to Slack")
    else:
        logger.warning("No SLACK_WEBHOOK_URL set — printing briefing instead of sending")
        print(payload["text"])
    return summarized


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
