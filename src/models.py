"""
Domain models for the churn-risk pipeline.

Data shapes + parsing only. Deterministic scoring lives in `src/risk/`, prompt
construction in `src/ai/`, and Slack formatting in `src/messaging/` — keeping
models free of business logic preserves the module boundaries in CLAUDE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    """Account lifecycle state, modeled on Recurly's real subscription states.

    `CANCELED` = pending non-renewal but still active and paying through
    `contract_end_date` -> the highest-value save target, NOT already churned.
    `EXPIRED` accounts have already churned and are filtered out before scoring:
    a churn-*risk* report is about accounts Customer Success can still save.
    """

    ACTIVE = "active"
    PAST_DUE = "past_due"   # in active dunning; current billing distress
    CANCELED = "canceled"   # signaled non-renewal -> top save target
    EXPIRED = "expired"     # already churned -> excluded upstream


def _parse_mrr(raw: str) -> float:
    return float(raw.replace("$", "").replace(",", "").strip())


@dataclass(frozen=True)
class Account:
    """One row of the weekly CSV export (the 9 source fields)."""

    account_id: str
    account_name: str
    mrr: float
    plan_name: str
    subscription_status: SubscriptionStatus
    failed_payment_count_last_30d: int
    days_since_last_login: int
    open_support_tickets: int
    contract_end_date: date

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> Account:
        """Parse one raw CSV row into a typed Account.

        Raises ``ValueError``/``KeyError`` on malformed data so the ingestion
        layer can skip the row and continue the batch rather than crash.
        """
        return cls(
            account_id=row["account_id"].strip(),
            account_name=row["account_name"].strip(),
            mrr=_parse_mrr(row["mrr"]),
            plan_name=row["plan_name"].strip(),
            subscription_status=SubscriptionStatus(row["subscription_status"].strip().lower()),
            failed_payment_count_last_30d=int(row["failed_payment_count_last_30d"]),
            days_since_last_login=int(row["days_since_last_login"]),
            open_support_tickets=int(row["open_support_tickets"]),
            contract_end_date=date.fromisoformat(row["contract_end_date"].strip()),
        )

    def days_until_renewal(self, today: date) -> int:
        return (self.contract_end_date - today).days


@dataclass(frozen=True)
class RiskAssessment:
    """Deterministic scoring output for a single account.

    `score`/`is_flagged` come from `src/risk/`. `signals` are the human-readable
    derived signals handed to the LLM (never the raw score). `summary` is the
    LLM-written note, or a deterministic fallback when generation fails — it is
    attached later via ``dataclasses.replace`` since this type is immutable.
    """

    account: Account
    score: int
    is_flagged: bool
    signals: list[str] = field(default_factory=list)
    summary: str | None = None
    used_fallback: bool = False

    @property
    def priority(self) -> tuple[int, float]:
        """Ordering key for the Slack briefing: risk severity first, MRR as the
        tiebreak. Risk != priority (see docs/risk_strategy.md)."""
        return (self.score, self.account.mrr)
