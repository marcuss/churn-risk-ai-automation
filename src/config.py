"""Runtime configuration, loaded once from the environment.

Secrets are never hard-coded (see `.env.example`). Centralizing access here means
the rest of the codebase depends on a typed `Config`, not scattered `os.environ`
lookups.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # python-dotenv is convenient locally but optional at runtime
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:  # pragma: no cover
    pass

DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    slack_webhook_url: str | None
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
            model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
        )
