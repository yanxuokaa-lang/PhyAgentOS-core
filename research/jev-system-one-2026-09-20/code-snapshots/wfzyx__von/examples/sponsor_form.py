"""Example: Sponsor Form Triage using Von."""

import json
import von

state = {
    "opportunity": "link",
    "name": "Managed Postgres",
    "description": "We make a managed PostgreSQL hosting product and would like to sponsor the newsletter in October.",
}

questions = {
    "is_sponsor_inquiry": von.noul(
        instructions="Does `description` ask to sponsor the site or newsletter?"
    ),
    "product_category": von.choice(
        instructions="What kind of product is described by `name` and `description`?",
        criteria={
            "dev_tool": "Developer tools, hosting, APIs, SaaS for developers",
            "course": "Courses, books, or training",
            "unrelated": "Anything not aimed at developers",
        },
    ),
    "message_quality": von.score(
        instructions="How specific is the request?",
        criteria=[
            "Generic template, no reference to this site",
            "Mentions the site but no concrete ask",
            "Concrete ask with a timeframe or product named",
        ],
    ),
}

# Run speculative fan-out (all 3 questions answered in one pass)
response = von.system_one(state=state, questions=questions)

print("=== Von Response ===")
print("Model:", response.model)
print("Usage:", response.usage)
print("\n=== Answers ===")
for q_id, answer in response.answers.items():
    print(f"[{q_id}]: {answer.model_dump()}")

# Business logic branching
answers = response.answers
if (
    answers["is_sponsor_inquiry"].noul > 0.8
    and answers["product_category"].choice == "dev_tool"
):
    print("\nAction: Automatically send rate card email!")
else:
    print("\nAction: Queue for manual human review.")
