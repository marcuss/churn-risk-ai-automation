"""Deterministic fallback summary.

Used when LLM generation fails or returns unusable output. Always produces a
non-empty, signal-grounded sentence so the weekly report is never blocked on the
model (CLAUDE.md §4). The text is intentionally plainer than the LLM's — its job
is reliability, not polish.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.models import RiskAssessment

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def _template() -> str:
    return (PROMPTS_DIR / "failed_generation_fallback.txt").read_text(encoding="utf-8").strip()


def build_fallback(assessment: RiskAssessment) -> str:
    signals = assessment.signals or ["elevated churn risk"]
    return _template().format(signal_summary=_humanize(signals))


def _humanize(signals: list[str]) -> str:
    if len(signals) == 1:
        return signals[0]
    return ", ".join(signals[:-1]) + f", and {signals[-1]}"
