"""Format the weekly churn-risk briefing for Slack.

Pure presentation — no risk logic (CLAUDE.md §9). Flagged accounts are ordered by
priority (risk severity, then MRR); MRR shows on each line so business impact is
visible without ever influencing the risk decision.
"""

from __future__ import annotations

from src.models import RiskAssessment

HEADER = "🚨 Weekly Churn Risk Report"
EMPTY_STATE = "✅ No accounts flagged for churn risk this week."


def build_payload(assessments: list[RiskAssessment]) -> dict:
    """Return a Slack webhook payload: rich Block Kit blocks + a plain-text
    fallback (used in notifications and by clients that ignore blocks)."""
    flagged = _ordered_flagged(assessments)
    return {"text": render_text(flagged), "blocks": _render_blocks(flagged)}


def render_text(flagged: list[RiskAssessment]) -> str:
    if not flagged:
        return f"{HEADER}\n\n{EMPTY_STATE}"
    lines = [HEADER, "", f"{len(flagged)} account(s) flagged for review.", ""]
    for a in flagged:
        lines.append(f"*{a.account.account_name}* · {_fmt_mrr(a.account.mrr)} MRR")
        lines.append(a.summary or "")
        lines.append("")
    return "\n".join(lines).rstrip()


def _ordered_flagged(assessments: list[RiskAssessment]) -> list[RiskAssessment]:
    return sorted(
        (a for a in assessments if a.is_flagged), key=lambda a: a.priority, reverse=True
    )


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
        line = f"*{a.account.account_name}*  ·  {_fmt_mrr(a.account.mrr)} MRR\n{a.summary or ''}"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": line}})
    return blocks
