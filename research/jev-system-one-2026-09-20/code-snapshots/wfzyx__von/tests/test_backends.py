import os
import pytest
import von


@pytest.fixture(autouse=True)
def reset_backend():
    yield
    von.set_backend("von-1.0")


def test_von_1_0_flagship_backend():
    von.set_backend("von-1.0")
    res = von.decide("Customer requests refund for duplicate charge on invoice #100", choices={
        "billing": "Invoices, billing, duplicate charges, refunds",
        "technical": "Software bugs and technical issues"
    })
    assert res.choice == "billing"
    assert "billing" in res.probabilities
    assert res.confidence > 0.0


def test_modernbert_alias():
    von.set_backend("modernbert")
    res = von.decide("Server CPU temperature reached 105 degrees Celsius", choices={
        "hardware_alert": "Hardware and temperature warnings",
        "billing": "Invoices and subscription payments"
    })
    assert res.choice == "hardware_alert"
    assert "hardware_alert" in res.probabilities
    assert res.confidence > 0.0


def test_local_needle_backend_if_present():
    if os.path.exists("src/von/local_backends/needle_backend.py"):
        von.set_backend("needle")
        res = von.decide("Billing error on checkout invoice", choices=["billing", "technical"])
        assert res.choice == "billing"
        assert res.confidence > 0.0

