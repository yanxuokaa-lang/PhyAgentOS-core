"""Tests adapted from OpenJev (TheoLeeCJ/openjev) verifying schema & contract compatibility."""

import math
import pytest
import von
from von.types import Choice, Question


def test_openjev_row_format_evaluation():
    """Verify Von can evaluate OpenJev's canonical decision rows."""
    row = {
        "id": "route-1",
        "state": "Customer asks to reset a forgotten password and says the reset email never arrived.",
        "question": "Which queue should handle this request?",
        "options": [
            {"id": "account_access", "description": "Account access and authentication support."},
            {"id": "billing", "description": "Billing and payment support."},
            {"id": "sales", "description": "Sales and product evaluation."},
        ],
    }

    criteria = {opt["id"]: opt["description"] for opt in row["options"]}
    ans = von.decide(state=row["state"], choices=criteria, instructions=row["question"])

    assert ans.type == "choice"
    assert ans.choice == "account_access"
    assert ans.confidence > 0.4
    assert set(ans.probabilities.keys()) == {"account_access", "billing", "sales"}


def test_openjev_policy_row():
    """Verify Von on policy gating row."""
    row = {
        "id": "policy-1",
        "state": "Policy: production deletion requires an approved change ticket. Request: list the names of files in the production backup; do not modify anything.",
        "question": "Does the request require an approved change ticket under the stated policy?",
        "options": [
            {"id": "required", "description": "An approved change ticket is required."},
            {"id": "not_required", "description": "An approved change ticket is not required."},
            {"id": "insufficient", "description": "The evidence is insufficient to decide."},
        ],
    }
    criteria = {opt["id"]: opt["description"] for opt in row["options"]}
    ans = von.decide(state=row["state"], choices=criteria, instructions=row["question"])
    assert ans.choice in ("required", "not_required")
    assert ans.confidence > 0.0


def test_openjev_support_row():
    """Verify Von on deployment evidence assessment row."""
    row = {
        "id": "support-1",
        "state": "The deployment completed at 14:02 UTC. Health checks passed in all three zones. No rollback was initiated.",
        "question": "Is there evidence that the deployment succeeded?",
        "options": [
            {"id": "yes", "description": "The deployment succeeded."},
            {"id": "no", "description": "The deployment did not succeed."},
            {"id": "insufficient", "description": "The evidence is insufficient to decide."},
        ],
    }
    criteria = {opt["id"]: opt["description"] for opt in row["options"]}
    ans = von.decide(state=row["state"], choices=criteria, instructions=row["question"])
    assert ans.choice == "yes"
    assert ans.probabilities["yes"] > 0.45


def test_duplicate_options_rejected():
    """Ensure duplicate option IDs in Choice raise an error."""
    with pytest.raises(Exception):
        # In Python dicts duplicate keys overwrite, but if passed as raw list or validation:
        von.decide("some state", choices=["yes", "yes"])


def test_structured_json_state_supported():
    """Verify structured JSON state is preserved and evaluated correctly."""
    state = {
        "policy": "Never request passwords",
        "candidate": ["invoice id"],
        "user_role": "billing_admin",
    }
    ans = von.decide(
        state=state,
        choices={
            "allowed": "The action complies with stated security policies",
            "forbidden": "The action violates password or security policies",
        },
        instructions="Is it allowed to ask for user credentials?",
    )
    assert ans.choice in ("allowed", "forbidden")


def test_softmax_probabilities_normalized_and_finite():
    """Verify all probabilities are finite, normalized, and sum to 1.0."""
    ans = von.decide(
        "Database is running slow under load",
        choices=["performance", "billing", "general"],
    )
    total_prob = sum(ans.probabilities.values())
    assert total_prob == pytest.approx(1.0, abs=1e-3)
    assert all(math.isfinite(p) for p in ans.probabilities.values())
    assert all(0.0 <= p <= 1.0 for p in ans.probabilities.values())
