"""Behavioral tests for deterministic risk qualification (see risk_strategy.md).

Assertions are about business outcomes — flagged vs. not, and which derived
signals surface — never the internal point math (CLAUDE.md §5). 'Today' is fixed
so renewal-proximity math is deterministic.
"""

import dataclasses
from datetime import date

from src.models import Account, SubscriptionStatus
from src.risk.risk_scoring import assess

TODAY = date(2026, 6, 11)

_BASE = Account(
    account_id="acct_test",
    account_name="Test Co",
    mrr=3000.0,
    plan_name="Growth",
    subscription_status=SubscriptionStatus.ACTIVE,
    failed_payment_count_last_30d=0,
    days_since_last_login=3,
    open_support_tickets=0,
    contract_end_date=date(2026, 12, 1),
)


def make_account(**overrides) -> Account:
    return dataclasses.replace(_BASE, **overrides)


def test_healthy_account_is_not_flagged():
    assert assess(make_account(), TODAY).is_flagged is False


def test_canceled_account_is_always_flagged():
    # Signaled non-renewal is risk by definition, even with no other signal.
    result = assess(
        make_account(
            subscription_status=SubscriptionStatus.CANCELED,
            contract_end_date=date(2027, 1, 1),
        ),
        TODAY,
    )
    assert result.is_flagged is True
    assert "pending non-renewal" in result.signals


def test_past_due_with_failed_payments_is_flagged():
    result = assess(
        make_account(
            subscription_status=SubscriptionStatus.PAST_DUE,
            failed_payment_count_last_30d=2,
        ),
        TODAY,
    )
    assert result.is_flagged is True
    assert "payment instability" in result.signals


def test_billing_signal_alone_does_not_flag():
    # 2 failed payments and nothing else is below threshold by design.
    assert assess(make_account(failed_payment_count_last_30d=2), TODAY).is_flagged is False


def test_inactivity_alone_below_threshold_is_not_flagged():
    assert assess(make_account(days_since_last_login=45), TODAY).is_flagged is False


def test_compound_moderate_signals_cross_threshold():
    result = assess(
        make_account(
            failed_payment_count_last_30d=1,
            days_since_last_login=38,
            open_support_tickets=4,
        ),
        TODAY,
    )
    assert result.is_flagged is True


def test_support_burden_with_renewal_is_flagged():
    result = assess(
        make_account(
            open_support_tickets=7,
            days_since_last_login=20,
            contract_end_date=date(2026, 6, 28),
        ),
        TODAY,
    )
    assert result.is_flagged is True
    assert "elevated support burden" in result.signals


def test_severe_account_is_flagged():
    result = assess(
        make_account(
            subscription_status=SubscriptionStatus.PAST_DUE,
            failed_payment_count_last_30d=3,
            days_since_last_login=85,
            open_support_tickets=6,
            contract_end_date=date(2026, 6, 19),
        ),
        TODAY,
    )
    assert result.is_flagged is True


def test_borderline_account_just_below_threshold():
    # 1 failed payment (+2) + 47 idle days (+3) = 5 -> not flagged.
    assert assess(
        make_account(failed_payment_count_last_30d=1, days_since_last_login=47),
        TODAY,
    ).is_flagged is False


def test_healthy_account_surfaces_no_signals():
    assert assess(make_account(), TODAY).signals == []
