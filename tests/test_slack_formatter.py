"""Tests for Slack briefing formatting.

Behavioral assertions (CLAUDE.md §5): the report shows the right content and
ordering, without brittle whole-string matching.
"""

from datetime import date

from src.messaging.slack_formatter import (
    EMPTY_STATE,
    HEADER,
    build_alert,
    build_payload,
    render_text,
)
from src.models import Account, RiskAssessment, SubscriptionStatus


def _flagged(name: str, mrr: float, score: int, summary: str) -> RiskAssessment:
    account = Account(
        account_id="id_" + name,
        account_name=name,
        mrr=mrr,
        plan_name="Growth",
        subscription_status=SubscriptionStatus.ACTIVE,
        failed_payment_count_last_30d=0,
        days_since_last_login=40,
        open_support_tickets=3,
        contract_end_date=date(2026, 12, 1),
    )
    return RiskAssessment(
        account=account, score=score, is_flagged=True, signals=["x"], summary=summary
    )


def test_report_has_title():
    payload = build_payload([_flagged("Acme", 3000, 7, "Acme looks at risk.")])
    assert HEADER in payload["text"]


def test_account_names_and_summaries_appear():
    items = [
        _flagged("Acme", 3000, 7, "Acme summary."),
        _flagged("Beta", 2000, 6, "Beta summary."),
    ]
    text = render_text(items)
    for expected in ("Acme", "Beta", "Acme summary.", "Beta summary."):
        assert expected in text


def test_empty_state_when_no_flagged_accounts():
    assert EMPTY_STATE in build_payload([])["text"]


def test_accounts_ordered_by_risk_severity_then_mrr():
    # Higher MRR but lower risk should rank BELOW lower MRR but higher risk.
    low_risk = _flagged("BigButCalm", 9000, 6, "low risk")
    high_risk = _flagged("SmallButSevere", 1000, 15, "high risk")
    text = build_payload([low_risk, high_risk])["text"]
    assert text.index("SmallButSevere") < text.index("BigButCalm")


def test_mrr_is_shown_on_each_line():
    assert "$8.5k" in render_text([_flagged("Acme", 8500, 7, "summary")])


def test_risk_tier_emoji_reflects_score():
    assert "🔴" in render_text([_flagged("Severe", 5000, 15, "x")])   # high
    assert "🟠" in render_text([_flagged("Medium", 5000, 9, "x")])    # medium
    assert "🟡" in render_text([_flagged("Elevated", 5000, 6, "x")])  # elevated


def test_alert_names_the_fallback_accounts():
    text = build_alert([_flagged("Acme", 3000, 7, "x"), _flagged("Beta", 2000, 6, "y")])["text"]
    assert "Acme" in text and "Beta" in text
    assert "2" in text  # count of fallbacks
