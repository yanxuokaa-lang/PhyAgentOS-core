import pytest

from tests.conftest import Client
from tests.helpers import models, system_one
from typesafe_sdk import AsyncTypeSafeClient, Choice, ChoiceAnswer, NoulAnswer, Questions, Score, ScoreAnswer, SystemOneResponse

pytestmark = pytest.mark.integration


class PydanticQuestionsResponse(SystemOneResponse):
    billing: NoulAnswer
    tone: ChoiceAnswer
    urgency: ScoreAnswer


async def test_live_models(live_client: Client) -> None:
    available = await models(live_client)
    assert available
    for model in available:
        assert isinstance(model.name, str)
        assert isinstance(model.description, str)
        assert isinstance(model.release_date, str)


async def test_live_questions(live_client: Client) -> None:
    result = await system_one(
        live_client,
        state={"subject": "Charged twice this month", "body": "I see two charges of $49. I only have one account. Please fix this ASAP."},
        questions={
            "billing": {
                "type": "noul",
                "instructions": "Is this ticket about billing?",
                "criteria": {"true": {"meaning": "Payments or invoices", "examples": ["charged twice"]}},
            },
            "tone": Choice(instructions="What is the customer's tone?", criteria={"calm": None, "frustrated": None, "angry": None}),
            "urgency": Score(instructions="How urgent is this ticket?", criteria=["can wait", "this week", "today"]),
        },
    )
    assert result.model
    assert result.usage.input_tokens is None or result.usage.input_tokens > 0
    assert result.usage.output_tokens is None or result.usage.output_tokens >= 0
    assert 0 <= result.nouls["billing"].noul <= 1
    assert result.choices["tone"].choice in {"calm", "frustrated", "angry"}
    assert sum(result.choices["tone"].probabilities.values()) == pytest.approx(1, abs=0.1)
    assert 0 <= result.scores["urgency"].score <= 2
    assert result.scores["urgency"].legend == {0: "can wait", 1: "this week", 2: "today"}
    assert set(result.scores["urgency"].probabilities) == {0, 1, 2}
    assert sum(result.scores["urgency"].probabilities.values()) == pytest.approx(1, abs=0.1)


async def test_live_pydantic_response(live_client: Client) -> None:
    state = {"subject": "Charged twice this month", "body": "I see two charges of $49. Please fix this ASAP."}
    questions: Questions = {
        "billing": {"type": "noul", "instructions": "Is this ticket about billing?"},
        "tone": Choice(instructions="What is the customer's tone?", criteria={"calm": None, "frustrated": None, "angry": None}),
        "urgency": Score(instructions="How urgent is this ticket?", criteria=["can wait", "this week", "today"]),
    }
    if isinstance(live_client, AsyncTypeSafeClient):
        result = await live_client.system_one(state, questions, response_model=PydanticQuestionsResponse)
    else:
        result = live_client.system_one(state, questions, response_model=PydanticQuestionsResponse)

    assert result.billing == result.nouls["billing"]
    assert result.tone == result.choices["tone"]
    assert result.urgency == result.scores["urgency"]
    assert 0 <= result.billing.noul <= 1
    assert result.tone.choice in {"calm", "frustrated", "angry"}
    assert 0 <= result.urgency.score <= 2
    assert result.request_id
