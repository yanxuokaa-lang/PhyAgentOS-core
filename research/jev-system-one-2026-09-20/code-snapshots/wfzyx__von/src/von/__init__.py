"""von - The open-source System One decision model.

Fast, local, non-autoregressive decision primitives.
Named in homage to John von Neumann and Ludwig von Mises.
"""

from .types import (
    Noul,
    Choice,
    Score,
    noul,
    choice,
    score,
    NoulAnswer,
    ChoiceAnswer,
    ScoreAnswer,
    SystemOneResponse,
    Usage,
)
from .client import VonClient, AsyncVonClient
from .api import system_one, decide, judge, rate, set_backend
from . import presets
from . import patterns

__version__ = "1.0.1"

__all__ = [
    "Noul",
    "Choice",
    "Score",
    "noul",
    "choice",
    "score",
    "NoulAnswer",
    "ChoiceAnswer",
    "ScoreAnswer",
    "SystemOneResponse",
    "Usage",
    "VonClient",
    "AsyncVonClient",
    "system_one",
    "decide",
    "judge",
    "rate",
    "set_backend",
    "presets",
    "patterns",
]
