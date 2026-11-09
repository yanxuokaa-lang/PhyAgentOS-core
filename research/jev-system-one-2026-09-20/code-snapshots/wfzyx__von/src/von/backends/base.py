"""Abstract Base Class for Von Decision Backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union
from ..types import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
)


class BaseBackend(ABC):
    """Base interface for all Von System One decision backends."""

    @abstractmethod
    def evaluate_choice(self, q_id: str, state_text: str, q: Choice) -> ChoiceAnswer:
        pass

    @abstractmethod
    def evaluate_score(self, q_id: str, state_text: str, q: Score) -> ScoreAnswer:
        pass

    @abstractmethod
    def evaluate_noul(self, q_id: str, state_text: str, q: Noul) -> NoulAnswer:
        pass

    @abstractmethod
    def evaluate(
        self,
        state: Any,
        questions: Dict[str, Union[Question, Dict[str, Any]]],
        model: str,
    ) -> SystemOneResponse:
        pass
