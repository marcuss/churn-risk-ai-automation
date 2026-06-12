"""Tests for the deterministic fallback and per-account failure isolation.

These cover CLAUDE.md §4: when LLM generation fails or returns garbage, the
account still gets a usable summary and the batch keeps going.
"""

from datetime import date

import pytest

from src.ai.fallback_summary import build_fallback
from src.ai.llm_client import SummaryGenerationError, _validate
from src.models import Account, RiskAssessment, SubscriptionStatus
from src.resilience.error_handler import summarize_safely

TODAY = date(2026, 6, 11)


def _assessment(name="Lumen Retail", signals=None, score=14) -> RiskAssessment:
    account = Account(
        account_id="acct_x",
        account_name=name,
        mrr=4500.0,
        plan_name="Growth",
        subscription_status=SubscriptionStatus.CANCELED,
        failed_payment_count_last_30d=0,
        days_since_last_login=16,
        open_support_tickets=2,
        contract_end_date=date(2026, 6, 22),
    )
    return RiskAssessment(
        account=account,
        score=score,
        is_flagged=True,
        signals=signals if signals is not None else ["pending non-renewal"],
    )


class _FakeLLM:
    def __init__(self, text: str = "", error: Exception | None = None):
        self._text, self._error = text, error

    def generate_summary(self, assessment: RiskAssessment, today: date) -> str:
        if self._error:
            raise self._error
        return self._text


def test_fallback_is_non_empty():
    assert build_fallback(_assessment()).strip()


def test_fallback_mentions_detected_signals():
    text = build_fallback(_assessment(signals=["payment instability"]))
    assert "payment instability" in text


def test_fallback_handles_no_signals_gracefully():
    assert build_fallback(_assessment(signals=[])).strip()


def test_summarize_uses_llm_text_on_success():
    result = summarize_safely(_FakeLLM(text="A thoughtful analyst summary."), _assessment(), TODAY)
    assert result.summary == "A thoughtful analyst summary."
    assert result.used_fallback is False


def test_summarize_falls_back_on_llm_error():
    result = summarize_safely(_FakeLLM(error=RuntimeError("boom")), _assessment(), TODAY)
    assert result.used_fallback is True
    assert result.summary and result.summary.strip()


def test_one_account_failure_does_not_stop_the_batch():
    good = summarize_safely(_FakeLLM(text="ok summary text here"), _assessment("Acme"), TODAY)
    bad = summarize_safely(_FakeLLM(error=ValueError("garbage")), _assessment("Beta"), TODAY)
    assert good.used_fallback is False
    assert bad.used_fallback is True
    assert good.summary and bad.summary


def test_validate_rejects_empty_output():
    with pytest.raises(SummaryGenerationError):
        _validate("")


def test_validate_rejects_overlong_output():
    with pytest.raises(SummaryGenerationError):
        _validate("x" * 5000)
