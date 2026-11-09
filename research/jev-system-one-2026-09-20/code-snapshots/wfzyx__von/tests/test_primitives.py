import pytest
import von
from von.types import Noul, Choice, Score, noul, choice, score


def test_helper_constructors():
    n = noul("Is this active?")
    assert isinstance(n, Noul)
    assert n.instructions == "Is this active?"

    c = choice("Which department?", {"billing": "Invoices", "support": "Help"})
    assert isinstance(c, Choice)
    assert "billing" in c.criteria

    s = score("Rate severity:", ["low", "medium", "high"])
    assert isinstance(s, Score)
    assert len(s.criteria) == 3


def test_decide_helper():
    ans = von.decide(
        "I need a refund for my order #1234",
        choices=["refund_request", "password_reset", "feature_idea"],
    )
    assert ans.type == "choice"
    assert ans.choice == "refund_request"
    assert "refund_request" in ans.probabilities
    assert 0.0 <= ans.confidence <= 1.0


def test_judge_helper():
    p = von.judge(
        "Urgent: Payment failed on invoice 999",
        instructions="Is this an urgent or critical payment failure?",
    )
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0
    assert p > 0.5


def test_rate_helper():
    ans = von.rate(
        "Server is completely dead and throwing 500 across all nodes",
        criteria=[
            "Cosmetic issue",
            "Minor slowdown",
            "Catastrophic outage with complete service disruption",
        ],
    )
    assert ans.type == "score"
    assert 0.0 <= ans.score <= 2.0
    assert ans.score > 1.0
    assert "2" in ans.probabilities
