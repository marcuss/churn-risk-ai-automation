"""Per-account failure isolation.

Turns a flagged assessment into one that always carries a usable summary: the
LLM is tried first, and any failure falls back to a deterministic summary,
logged with context. One account's failure never interrupts the batch
(CLAUDE.md §4).
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import date
from typing import Protocol

from src.ai.fallback_summary import build_fallback
from src.models import RiskAssessment

logger = logging.getLogger(__name__)


class SummaryProvider(Protocol):
    def generate_summary(self, assessment: RiskAssessment, today: date) -> str: ...


def summarize_safely(
    llm: SummaryProvider, assessment: RiskAssessment, today: date
) -> RiskAssessment:
    try:
        text = llm.generate_summary(assessment, today)
        return dataclasses.replace(assessment, summary=text, used_fallback=False)
    except Exception as exc:  # noqa: BLE001 — last line of defense for the batch
        logger.error(
            "Summary generation failed for %s: %s — using deterministic fallback",
            assessment.account.account_id,
            exc,
            exc_info=True,
        )
        return dataclasses.replace(
            assessment, summary=build_fallback(assessment), used_fallback=True
        )
