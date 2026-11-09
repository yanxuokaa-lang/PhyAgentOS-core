"""Example: Support Ticket Triage using Von."""

import von

TRIAGE_QUESTIONS = {
    "category": von.choice(
        instructions="What kind of ticket is `ticket`?",
        criteria={
            "bug_report": "Something is broken, degraded, or throwing errors",
            "feature_request": "Asking for something that does not exist yet",
            "billing": "Charges, invoices, payment methods, refunds",
            "other": "General inquiries or uncategorized",
        },
    ),
    "bug_severity": von.score(
        instructions="How severe is the issue in `ticket`?",
        criteria=[
            "Cosmetic; no impact on core functionality",
            "Broken or degraded feature, but a workaround exists",
            "Blocking issue; no workaround exists",
        ],
    ),
    "has_repro_steps": von.noul(
        instructions="Does `ticket` say how to reproduce the problem?"
    ),
    "refund_requested": von.noul(
        instructions="Does the customer ask for money back or a refund?"
    ),
    "frustration": von.score(
        instructions="How frustrated is the author of `ticket`?",
        criteria=[
            "Calm, just stating facts",
            "Frustrated but civil",
            "Very angry, strong language, or threatening to leave",
        ],
    ),
}


def triage(ticket: str) -> dict:
    resp = von.system_one(state={"ticket": ticket}, questions=TRIAGE_QUESTIONS)
    ans = resp.answers

    category = ans["category"]
    severity = ans["bug_severity"]
    has_repro = ans["has_repro_steps"]
    refund = ans["refund_requested"]
    frustration = ans["frustration"]

    # 1. Confidence threshold check
    if category.confidence < 0.4:
        return {"route": "human", "reason": "unclear category"}

    # 2. Bug reports
    if category.choice == "bug_report":
        if severity.score > 1.2 and has_repro.noul > 0.5:
            return {"route": "engineering", "priority": "high"}
        return {"route": "bug_backlog"}

    # 3. Billing
    if category.choice == "billing":
        return {"route": "billing", "refund_likely": refund.noul > 0.6}

    # 4. Feature requests
    if category.choice == "feature_request":
        return {"route": "product"}

    # 5. Default / High frustration human fallback
    return {"route": "human", "flag": frustration.score > 1.2}


if __name__ == "__main__":
    ticket1 = "The export button crashes the settings page in Safari. Steps: 1. Click Export 2. Browser freezes completely. Urgent!"
    print("Ticket 1 triage:", triage(ticket1))

    ticket2 = "I was charged $49 twice for order #982! Please refund the duplicate immediately."
    print("Ticket 2 triage:", triage(ticket2))
