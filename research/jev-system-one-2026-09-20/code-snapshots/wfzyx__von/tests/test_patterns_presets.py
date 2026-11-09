import pytest
import von
from von.presets import triage_preset, email_preset, moderation_preset, security_preset
from von.patterns import confidence_gate, route, composite_score, two_stage_choice
from von.types import Choice, Noul, Score


def test_presets_structure():
    triage = triage_preset()
    assert "intent" in triage
    assert "is_urgent" in triage
    assert "frustration" in triage
    assert "churn_risk" in triage
    assert isinstance(triage["intent"], Choice)
    assert isinstance(triage["is_urgent"], Noul)
    assert isinstance(triage["frustration"], Score)

    email = email_preset()
    assert "destination" in email
    assert "is_spam_or_phishing" in email
    assert "priority" in email

    mod = moderation_preset()
    assert "policy_violation" in mod
    assert "should_block" in mod

    sec = security_preset()
    assert "event_type" in sec
    assert "is_threat" in sec


def test_patterns_route():
    state = "The customer wants an immediate refund for their unused subscription."
    q = Choice(
        instructions="Route customer request",
        criteria={
            "refund": "Customer asks for refund or payment reversal",
            "support": "Customer asks for technical support",
        }
    )

    dispatched = []

    def handle_refund(ans):
        dispatched.append("refund_handled")
        return "REFUND_PROCESSED"

    def handle_support(ans):
        dispatched.append("support_handled")
        return "SUPPORT_OPENED"

    res = route(
        state,
        question=q,
        routes={"refund": handle_refund, "support": handle_support},
    )
    assert res == "REFUND_PROCESSED"
    assert dispatched == ["refund_handled"]


def test_patterns_confidence_gate():
    state = "Urgent: database cluster crashed, connection pool completely exhausted."
    questions = {
        "is_outage": Noul(
            instructions="Is there an active database outage?",
            pos_criteria="Database crash, pool exhausted, downtime",
            neg_criteria="Normal operational query, no crash"
        )
    }

    gated = confidence_gate(state, questions, threshold=0.1)
    assert "automatic" in gated
    assert "escalate" in gated
    assert len(gated["automatic"]) + len(gated["escalate"]) == 1


def test_patterns_composite_score():
    state = "Catastrophic multi-region outage affecting all enterprise payments and databases."
    questions = {
        "severity": Score(
            instructions="Rate outage severity",
            criteria=["Minor", "Moderate", "Critical emergency"]
        ),
        "blocking": Noul(
            instructions="Is this blocking?",
            pos_criteria="Critical blocking outage",
            neg_criteria="Non-blocking"
        )
    }

    scored = composite_score(state, questions)
    assert "score" in scored
    assert 0.0 <= scored["score"] <= 1.0
    assert "breakdown" in scored
    assert "severity" in scored["breakdown"]
    assert "blocking" in scored["breakdown"]
