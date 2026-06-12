"""Deterministic churn-risk rules — the single authoritative source of risk
qualification. The LLM never participates here (see docs/risk_strategy.md and
docs/adr/0001-deterministic-risk-scoring.md).

Rules are kept as explicit, readable functions rather than a data-driven table:
the point values *are* the business policy, and being able to read them top to
bottom is worth more than cleverness (CLAUDE.md §3).
"""

from __future__ import annotations

from src.models import SubscriptionStatus

# An account is flagged when its total score reaches this. Roughly "two real
# problems, or one severe one." See risk_strategy.md for the rationale.
RISK_THRESHOLD = 6


def status_points(status: SubscriptionStatus) -> int:
    if status is SubscriptionStatus.CANCELED:
        return 10  # signaled non-renewal -> auto-flags; the top save target
    if status is SubscriptionStatus.PAST_DUE:
        return 5  # active dunning
    return 0  # active; EXPIRED is filtered upstream and never scored


def failed_payment_points(count: int) -> int:
    if count >= 2:
        return 4
    if count == 1:
        return 2
    return 0


def inactivity_points(days_since_last_login: int) -> int:
    if days_since_last_login > 60:
        return 5
    if days_since_last_login > 30:
        return 3
    if days_since_last_login > 14:
        return 1
    return 0


def support_points(open_tickets: int) -> int:
    if open_tickets > 5:
        return 3
    if open_tickets > 2:
        return 2
    return 0


def renewal_points(days_until_renewal: int) -> int:
    if days_until_renewal < 14:
        return 3
    if days_until_renewal < 30:
        return 2
    return 0
