"""Tiny retry helper for transient failures.

Deliberately a single function, not a framework (CLAUDE.md §1). `sleep` is
injectable so tests run instantly.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def retry[T](
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Attempt %d/%d failed: %s — retrying in %.1fs", attempt, attempts, exc, delay
            )
            sleep(delay)
    assert last_exc is not None  # unreachable unless attempts < 1
    raise last_exc
