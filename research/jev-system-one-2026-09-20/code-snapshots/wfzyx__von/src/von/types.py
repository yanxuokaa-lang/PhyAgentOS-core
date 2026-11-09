"""Types and schemas for Von decision primitives."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class Noul(BaseModel):
    """A yes/no probability question."""
    type: Literal["noul"] = "noul"
    instructions: str
    criteria: Optional[Dict[str, str]] = None


class Choice(BaseModel):
    """Pick one option from a fixed list with probability distribution."""
    type: Literal["choice"] = "choice"
    instructions: str
    criteria: Dict[str, Optional[str]]


class Score(BaseModel):
    """A position on an ordered scale (2 to 10 levels)."""
    type: Literal["score"] = "score"
    instructions: str
    criteria: List[Union[str, Dict[str, Any]]]


Question = Union[Noul, Choice, Score]


def noul(instructions: str, criteria: Optional[Dict[str, str]] = None) -> Noul:
    """Helper to construct a Noul question."""
    return Noul(instructions=instructions, criteria=criteria)


def choice(instructions: str, criteria: Dict[str, Optional[str]]) -> Choice:
    """Helper to construct a Choice question."""
    return Choice(instructions=instructions, criteria=criteria)


def score(instructions: str, criteria: List[Union[str, Dict[str, Any]]]) -> Score:
    """Helper to construct a Score question."""
    return Score(instructions=instructions, criteria=criteria)


class NoulAnswer(BaseModel):
    """Answer to a Noul question."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["noul"] = "noul"
    noul: float = Field(..., description="Probability between 0.0 and 1.0 that the condition is true")


class ChoiceAnswer(BaseModel):
    """Answer to a Choice question."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["choice"] = "choice"
    choice: str = Field(..., description="The option key with highest probability")
    probabilities: Dict[str, float] = Field(..., description="Probability distribution across all options")
    confidence: float = Field(..., description="Confidence metric (0.0 to 1.0)")


class ScoreAnswer(BaseModel):
    """Answer to a Score question."""
    model_config = ConfigDict(extra="ignore")
    type: Literal["score"] = "score"
    score: float = Field(..., description="Probability-weighted expectation across levels")
    confidence: float = Field(..., description="Confidence metric (0.0 to 1.0)")
    legend: Dict[str, str] = Field(..., description="Mapping of level numbers to descriptions")
    probabilities: Dict[str, float] = Field(..., description="Probability distribution across levels")


Answer = Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]


class Usage(BaseModel):
    """Token usage metadata."""
    input_tokens: int = 0
    output_tokens: int = 0


class SystemOneResponse(BaseModel):
    """Response envelope for a System One evaluation."""
    model_config = ConfigDict(extra="ignore")
    model: str
    answers: Dict[str, Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]]
    usage: Usage

    def __getitem__(self, item: str) -> Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]:
        return self.answers[item]
