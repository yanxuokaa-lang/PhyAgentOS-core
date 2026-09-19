"""One monotonic budget shared by all no-motion preparation stages."""

from __future__ import annotations

import math
from dataclasses import dataclass
from time import monotonic


class PreparationDeadlineExceededError(TimeoutError):
    """The complete preparation Query exhausted its configured budget."""


@dataclass(frozen=True)
class PreparationDeadline:
    expires_at: float

    @classmethod
    def start(cls, timeout_s: float) -> "PreparationDeadline":
        if isinstance(timeout_s, bool) or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("preparation timeout must be finite and positive")
        return cls(expires_at=monotonic() + float(timeout_s))

    def remaining(self, stage: str) -> float:
        remaining = self.expires_at - monotonic()
        if remaining <= 0:
            raise PreparationDeadlineExceededError(
                f"preparation deadline exceeded during {stage}"
            )
        return remaining

    def bounded_timeout(self, configured_s: float, stage: str) -> float:
        return min(float(configured_s), self.remaining(stage))


__all__ = ["PreparationDeadline", "PreparationDeadlineExceededError"]
