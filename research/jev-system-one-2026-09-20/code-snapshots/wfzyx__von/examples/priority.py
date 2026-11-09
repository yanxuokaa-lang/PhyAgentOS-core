"""Example: Composite Scoring using Von."""

import von

PRIORITY_QUESTIONS = {
    "severity": von.score(
        instructions="How severe is the issue in `ticket`?",
        criteria=[
            "Cosmetic; no impact on functionality",
            "Broken or degraded feature, but a workaround exists",
            "Blocking issue; no workaround exists",
        ],
    ),
    "frustration": von.score(
        instructions="How frustrated is the author of `ticket`?",
        criteria=[
            "Calm, just stating facts",
            "Frustrated but civil",
            "Very angry or threatening to leave",
        ],
    ),
    "report_quality": von.score(
        instructions="How much does `ticket` give an engineer to work with?",
        criteria=[
            "No detail; just says something is broken",
            "Names the feature but no steps or environment",
            "Steps to reproduce or environment, but not both",
            "Steps to reproduce and environment",
        ],
    ),
}


def compute_priority(ticket: str) -> float:
    resp = von.system_one(state={"ticket": ticket}, questions=PRIORITY_QUESTIONS)
    ans = resp.answers

    # Normalize each score by its max level index
    norm_sev = ans["severity"].score / 2.0
    norm_frust = ans["frustration"].score / 2.0
    norm_qual = ans["report_quality"].score / 3.0

    # Composite weighted formula
    composite = (0.6 * norm_sev) + (0.3 * norm_frust) + (0.1 * norm_qual)
    return round(composite, 3)


if __name__ == "__main__":
    t = "Your whole checkout is down! I cannot process customer payments and I am losing thousands of dollars right now!"
    print("Computed priority score (0.0 to 1.0):", compute_priority(t))
