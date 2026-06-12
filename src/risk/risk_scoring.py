"""Turn an `Account` into a deterministic `RiskAssessment`.

Produces three things: the numeric `score`, the `is_flagged` decision, and the
human-readable `signals` that the AI layer later narrates. The raw score is
deliberately *not* exposed to the LLM — only the interpreted signals are.
"""

from __future__ import annotations

from datetime import date

from src.models import Account, RiskAssessment, SubscriptionStatus
from src.risk import risk_rules


def assess(account: Account, today: date) -> RiskAssessment:
    days_to_renewal = account.days_until_renewal(today)
    score = (
        risk_rules.status_points(account.subscription_status)
        + risk_rules.failed_payment_points(account.failed_payment_count_last_30d)
        + risk_rules.inactivity_points(account.days_since_last_login)
        + risk_rules.support_points(account.open_support_tickets)
        + risk_rules.renewal_points(days_to_renewal)
    )
    return RiskAssessment(
        account=account,
        score=score,
        is_flagged=score >= risk_rules.RISK_THRESHOLD,
        signals=_derived_signals(account, days_to_renewal),
    )


def _derived_signals(account: Account, days_to_renewal: int) -> list[str]:
    """Interpreted signals handed to the LLM in place of raw metrics.

    These are coarser than the scoring bands on purpose — they describe *why* an
    account looks risky in analyst language, not the exact points it earned.
    """
    signals: list[str] = []
    if account.subscription_status is SubscriptionStatus.CANCELED:
        signals.append("pending non-renewal")
    if (
        account.failed_payment_count_last_30d >= 1
        or account.subscription_status is SubscriptionStatus.PAST_DUE
    ):
        signals.append("payment instability")
    if account.days_since_last_login > 30:
        signals.append("low product engagement")
    if account.open_support_tickets > 2:
        signals.append("elevated support burden")
    if days_to_renewal < 30:
        signals.append("upcoming renewal (time-sensitive)")
    return signals
