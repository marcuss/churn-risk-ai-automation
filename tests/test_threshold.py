"""Threshold-boundary behavior (see prompts/testing/threshold_tests_prompt.md).

Each test places an account on a cutoff and checks that crossing it *flips the
at-risk classification* — testing observable behavior, not the internal point
arithmetic (CLAUDE.md §5).
"""

from datetime import date

from src.models import Account, SubscriptionStatus
from src.risk.risk_scoring import assess

TODAY = date(2026, 6, 11)


def _flagged(**overrides) -> bool:
    base = dict(
        account_id="acct_test",
        account_name="Boundary Co",
        mrr=3000.0,
        plan_name="Growth",
        subscription_status=SubscriptionStatus.ACTIVE,
        failed_payment_count_last_30d=0,
        days_since_last_login=3,
        open_support_tickets=0,
        contract_end_date=date(2026, 12, 1),
    )
    base.update(overrides)
    return assess(Account(**base), TODAY).is_flagged


def test_flag_threshold_lower_edge():
    # 2 failed payments + 20 idle days = 5 -> just under.
    assert _flagged(failed_payment_count_last_30d=2, days_since_last_login=20) is False
    # 2 failed payments + 3 open tickets = 6 -> exactly at threshold.
    assert _flagged(failed_payment_count_last_30d=2, open_support_tickets=3) is True


def test_inactivity_boundary_flips_classification():
    # Base 2 failed payments; 30 vs 31 idle days tips it over.
    assert _flagged(failed_payment_count_last_30d=2, days_since_last_login=30) is False
    assert _flagged(failed_payment_count_last_30d=2, days_since_last_login=31) is True


def test_renewal_window_boundary_flips_classification():
    # Base 2 failed payments; renewal at 30 days scores 0, at 29 days scores +2.
    assert _flagged(failed_payment_count_last_30d=2, contract_end_date=date(2026, 7, 11)) is False
    assert _flagged(failed_payment_count_last_30d=2, contract_end_date=date(2026, 7, 10)) is True


def test_failed_payment_boundary_flips_classification():
    # Base 40 idle days (+3) + 3 tickets (+2) = 5; one failed payment tips it.
    assert _flagged(days_since_last_login=40, open_support_tickets=3) is False
    assert _flagged(
        days_since_last_login=40, open_support_tickets=3, failed_payment_count_last_30d=1
    ) is True
