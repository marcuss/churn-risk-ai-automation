"""CSV / stdin ingestion.

Reads the weekly export, parses rows into `Account`s, and drops accounts that
should never reach scoring — `expired` accounts have already churned (see
docs/adr/0005). Per-row parse failures are logged and skipped so one malformed
row never aborts the batch (CLAUDE.md §4: fail gracefully).
"""

from __future__ import annotations

import csv
import logging
from typing import TextIO

from src.models import Account, SubscriptionStatus

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {
    "account_id",
    "account_name",
    "mrr",
    "plan_name",
    "subscription_status",
    "failed_payment_count_last_30d",
    "days_since_last_login",
    "open_support_tickets",
    "contract_end_date",
}


def load_accounts(source: TextIO) -> list[Account]:
    reader = csv.DictReader(source)
    missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    accounts: list[Account] = []
    for line_no, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            account = Account.from_csv_row(row)
        except (ValueError, KeyError) as exc:
            logger.warning("Skipping malformed CSV row %d: %s", line_no, exc)
            continue
        if account.subscription_status is SubscriptionStatus.EXPIRED:
            logger.info("Excluding already-churned (expired) account %s", account.account_id)
            continue
        accounts.append(account)
    return accounts


def load_accounts_from_path(path: str) -> list[Account]:
    with open(path, newline="", encoding="utf-8") as fh:
        return load_accounts(fh)
