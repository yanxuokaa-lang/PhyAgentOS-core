"""High-level convenience API for Von."""

from typing import Any, Dict, List, Optional, Union
from .client import VonClient
from .types import (
    Choice,
    ChoiceAnswer,
    Noul,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
)

_default_client: Optional[VonClient] = None


def _get_default_client() -> VonClient:
    global _default_client
    if _default_client is None:
        _default_client = VonClient(local=True)
    return _default_client


def set_backend(backend: str):
    """Set the underlying decision backend ('needle', 'modernbert', 'qwen0.5b')."""
    from .engine import VonEngine
    VonEngine.set_backend(backend)


def system_one(
    state: Any,
    questions: Dict[str, Union[Question, Dict[str, Any]]],
    model: str = "von-latest",
    client: Optional[VonClient] = None,
) -> SystemOneResponse:
    """Evaluate state and questions using System One."""
    cli = client or _get_default_client()
    return cli.system_one(state=state, questions=questions, model=model)


def decide(
    state: Any,
    choices: Union[List[str], Dict[str, Optional[str]]],
    instructions: str = "Which option best describes the state?",
    model: str = "von-latest",
) -> ChoiceAnswer:
    """Make a fast discrete decision among options."""
    if isinstance(choices, list):
        if len(choices) != len(set(choices)):
            raise ValueError(f"Duplicate choices found in options list: {choices}")
        criteria = {c: None for c in choices}
    else:
        criteria = choices

    q = Choice(instructions=instructions, criteria=criteria)
    resp = system_one(state=state, questions={"decision": q}, model=model)
    return resp.answers["decision"]  # type: ignore


def judge(
    state: Any,
    instructions: str,
    criteria: Optional[Dict[str, str]] = None,
    model: str = "von-latest",
) -> float:
    """Evaluate a yes/no question and return the probability (0.0 to 1.0)."""
    q = Noul(instructions=instructions, criteria=criteria)
    resp = system_one(state=state, questions={"judgment": q}, model=model)
    answer = resp.answers["judgment"]
    return getattr(answer, "noul", 0.0)


def rate(
    state: Any,
    criteria: List[Union[str, Dict[str, Any]]],
    instructions: str = "Rate where the state falls on this scale:",
    model: str = "von-latest",
) -> ScoreAnswer:
    """Evaluate a state on an ordered multi-level scale."""
    q = Score(instructions=instructions, criteria=criteria)
    resp = system_one(state=state, questions={"rating": q}, model=model)
    return resp.answers["rating"]  # type: ignore
