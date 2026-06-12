"""Anthropic (Claude) client for summary generation.

This layer only writes prose — it never decides risk and never produces the
fallback (CLAUDE.md §2, §9). On unrecoverable failure it raises, and the
resilience layer substitutes a deterministic fallback. Transient errors and
unusable ("garbage") responses are retried before giving up.
"""

from __future__ import annotations

import logging
from datetime import date

from src.ai import prompt_builder
from src.config import Config
from src.models import RiskAssessment
from src.resilience.retry import retry

logger = logging.getLogger(__name__)

MAX_TOKENS = 256
TEMPERATURE = 0.3  # a little natural variation, but mostly stable prose
_MIN_CHARS = 20
_MAX_CHARS = 800  # a 2–3 sentence note; longer means the model rambled -> reject


class SummaryGenerationError(RuntimeError):
    """Raised when the model output is unusable (empty, too short, or too long)."""


class LLMClient:
    def __init__(self, config: Config, client=None) -> None:
        self._config = config
        self._client = client or self._build_client(config)

    @staticmethod
    def _build_client(config: Config):
        from anthropic import Anthropic  # imported lazily so tests need no SDK

        return Anthropic(api_key=config.anthropic_api_key)

    def generate_summary(self, assessment: RiskAssessment, today: date) -> str:
        system = prompt_builder.system_prompt()
        user_prompt = prompt_builder.build_user_prompt(assessment, today)

        def _call() -> str:
            message = self._client.messages.create(
                model=self._config.model,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                # Cache the shared system prompt across the batch to cut cost.
                system=[
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ],
                messages=[{"role": "user", "content": user_prompt}],
            )
            return _validate(_extract_text(message))

        return retry(_call, attempts=3)


def _extract_text(message) -> str:
    parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _validate(text: str) -> str:
    if not (_MIN_CHARS <= len(text) <= _MAX_CHARS):
        raise SummaryGenerationError(f"summary length out of bounds ({len(text)} chars)")
    return text
