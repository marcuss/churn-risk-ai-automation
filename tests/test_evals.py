"""Tests for the eval harness's deterministic parts — no API calls.

Covers the Layer-1 checks, judge-score parsing, and suite aggregation, so the
governance logic is itself verified in the no-network `ci.yml`.
"""

from evals.run import (
    JUDGE_DIMENSIONS,
    CaseResult,
    JudgeResult,
    layer1_checks,
    parse_judge_scores,
    suite_passes,
)
from src.models import SubscriptionStatus

GOOD = (
    "In active dunning with three failed payments and 85 idle days, the account "
    "needs outreach before the renewal date."
)


def test_layer1_passes_for_a_clean_summary():
    assert all(layer1_checks(GOOD, "Vertex Payments", SubscriptionStatus.PAST_DUE).values())


def test_layer1_flags_restated_account_name():
    text = "Vertex Payments is in active dunning and needs outreach before renewal closes soon."
    checks = layer1_checks(text, "Vertex Payments", SubscriptionStatus.ACTIVE)
    assert checks["omits_account_name"] is False


def test_layer1_flags_leaked_score():
    text = "The account has a risk score of 20 and needs immediate outreach before renewal."
    assert layer1_checks(text, "Acme", SubscriptionStatus.ACTIVE)["no_leaked_score"] is False


def test_layer1_flags_bullets():
    text = "- billing\n- engagement\n- support tickets are piling up before the renewal date."
    assert layer1_checks(text, "Acme", SubscriptionStatus.ACTIVE)["no_bullets_or_headings"] is False


def test_canceled_requires_renewal_language():
    text = "The customer is disengaged and has several open tickets that remain unresolved today."
    checks = layer1_checks(text, "Acme", SubscriptionStatus.CANCELED)
    assert checks["canceled_mentions_renewal"] is False


def test_parse_judge_scores_extracts_json_from_noise():
    raw = (
        'Sure: {"synthesis": 5, "tone": 4, "actionability": 4, '
        '"faithfulness": 5, "canceled_framing": 3, "rationale": "solid"}'
    )
    jr = parse_judge_scores(raw)
    assert jr.scores["synthesis"] == 5
    assert jr.mean == (5 + 4 + 4 + 5 + 3) / 5
    assert jr.rationale == "solid"


def _case(layer1_ok: bool, judge_score: int) -> CaseResult:
    return CaseResult(
        name="X",
        score=10,
        layer1={"c": layer1_ok},
        judge=JudgeResult(scores=dict.fromkeys(JUDGE_DIMENSIONS, judge_score), rationale=""),
        summary="s",
    )


def test_suite_passes_when_above_both_bars():
    assert suite_passes([_case(True, 5) for _ in range(8)]) is True


def test_suite_fails_when_judge_below_bar():
    assert suite_passes([_case(True, 3) for _ in range(8)]) is False


def test_suite_fails_when_layer1_rate_below_bar():
    cases = [_case(False, 5), _case(False, 5)] + [_case(True, 5) for _ in range(8)]  # 80% < 90%
    assert suite_passes(cases) is False
