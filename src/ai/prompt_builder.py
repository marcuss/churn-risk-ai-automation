"""Build the system + user prompts for summary generation.

Prompts are loaded from `prompts/*.txt` so they are versioned artifacts with a
single source of truth, not strings duplicated in code (see docs/prompt_design.md).

The account *name* is deliberately NOT sent to the model — the Slack formatter
owns it as a heading. That keeps the context minimal, makes it impossible for the
model to restate the name, and removes `account_name` as a prompt-injection
surface (the model only ever sees risk signals, never free-text fields).
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

from src.models import RiskAssessment, SubscriptionStatus

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_STATUS_DESCRIPTIONS = {
    SubscriptionStatus.ACTIVE: "Active",
    SubscriptionStatus.PAST_DUE: "Past Due (active dunning)",
    SubscriptionStatus.CANCELED: "Canceled (set to not renew; still active)",
}


@lru_cache
def _load(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def system_prompt() -> str:
    return _load("system_prompt.txt")


def build_user_prompt(assessment: RiskAssessment, today: date) -> str:
    account = assessment.account
    signal_lines = "\n".join(f"- {s}" for s in assessment.signals) or "- (no specific signals)"
    return _load("risk_summary_prompt.txt").format(
        status_description=_STATUS_DESCRIPTIONS.get(
            account.subscription_status, account.subscription_status.value
        ),
        failed_payment_count=account.failed_payment_count_last_30d,
        days_since_last_login=account.days_since_last_login,
        open_support_tickets=account.open_support_tickets,
        renewal_phrase=_renewal_phrase(account.days_until_renewal(today)),
        signal_lines=signal_lines,
    )


def _renewal_phrase(days: int) -> str:
    if days < 0:
        return f"overdue by {abs(days)} days"
    if days == 0:
        return "today"
    return f"in {days} days"
