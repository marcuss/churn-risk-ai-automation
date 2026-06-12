"""
Domain models for the churn-risk pipeline.

This module defines *data shapes only*. The deterministic scoring logic lives in
`src/risk/`, prompt construction in `src/ai/`, and Slack formatting in
`src/messaging/`. Keeping models free of business logic preserves the module
boundaries described in CLAUDE.md.

NOTE: structural skeleton. Parsing and derivation are stubbed (`NotImplementedError`)
until the ingestion and risk layers are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class SubscriptionStatus(str, Enum):
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
    def from_csv_row(cls, row: dict[str, str]) -> "Account":
        # TODO(ingestion): parse/validate raw CSV strings into typed fields.
        raise NotImplementedError


@dataclass(frozen=True)
class RiskAssessment:
    """Deterministic scoring output for a single account.

    `score` and `is_flagged` come from `src/risk/`. `signals` are the
    human-readable derived signals handed to the LLM (never the raw score).
    `summary` is the LLM-written note, or a deterministic fallback when
    generation fails. Ordering for the Slack report uses `priority` — risk
    severity first, MRR as the tiebreak (risk != priority).
    """

    account: Account
    score: int
    is_flagged: bool
    signals: list[str] = field(default_factory=list)
    summary: str | None = None
    used_fallback: bool = False

    @property
    def priority(self) -> tuple[int, float]:
        # TODO(risk): ordering key for the briefing — see docs/risk_strategy.md.
        raise NotImplementedError
