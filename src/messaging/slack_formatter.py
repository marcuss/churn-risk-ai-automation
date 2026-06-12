"""Format the weekly churn-risk briefing for Slack.

Pure presentation — no risk logic beyond mapping the deterministic score to a
display tier (CLAUDE.md §9). Flagged accounts are ordered by priority (risk
severity, then MRR); each entry is a triage-color tier + name + MRR, then the
analyst summary. MRR is shown for impact but never influences the risk decision.

Kept deliberately minimal: the brief warns against a "data dump", so the entry is
a triage color, the account, its MRR, and the analyst's words — nothing that
competes with the summary.
"""

from __future__ import annotations

from src.models import RiskAssessment

HEADER = "🚨 Weekly Churn Risk Report"
EMPTY_STATE = "✅ No accounts flagged for churn risk this week."


def build_payload(assessments: list[RiskAssessment]) -> dict:
    flagged = _ordered_flagged(assessments)
    return {"text": render_text(flagged), "blocks": _render_blocks(flagged)}


def render_text(flagged: list[RiskAssessment]) -> str:
    if not flagged:
        return f"{HEADER}\n\n{EMPTY_STATE}"
    lines = [HEADER, "", f"{len(flagged)} account(s) flagged for review.", ""]
    for a in flagged:
        head = f"{_risk_emoji(a.score)} *{a.account.account_name}* · {_fmt_mrr(a.account.mrr)} MRR"
        lines.append(head)
        lines.append(a.summary or "")
        lines.append("")
    return "\n".join(lines).rstrip()


def _ordered_flagged(assessments: list[RiskAssessment]) -> list[RiskAssessment]:
    return sorted(
        (a for a in assessments if a.is_flagged), key=lambda a: a.priority, reverse=True
    )


def _risk_emoji(score: int) -> str:
    """Deterministic triage tier from the risk score (bands in docs/risk_strategy.md).
    The tier conveys risk *level*, so it comes from the score, never the LLM."""
    if score >= 12:
        return "🔴"
    if score >= 8:
        return "🟠"
    return "🟡"


def _fmt_mrr(mrr: float) -> str:
    return f"${mrr / 1000:.1f}k" if mrr >= 1000 else f"${mrr:.0f}"


def _render_blocks(flagged: list[RiskAssessment]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": HEADER, "emoji": True}}
    ]
    if not flagged:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": EMPTY_STATE}})
        return blocks
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{len(flagged)} account(s) flagged for review."}
            ],
        }
    )
    blocks.append({"type": "divider"})
    for a in flagged:
        emoji, mrr = _risk_emoji(a.score), _fmt_mrr(a.account.mrr)
        head = f"{emoji}  *{a.account.account_name}*  ·  {mrr} MRR"
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"{head}\n{a.summary or ''}"}}
        )
    return blocks
