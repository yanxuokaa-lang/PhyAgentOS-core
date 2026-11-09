"""Example: Intent Routing & Model Gate using Von."""

import von

ROUTER_QUESTIONS = {
    "intent": von.choice(
        instructions="What does the author of `message` want?",
        criteria={
            "order_status": "Where is my order, has it shipped, tracking lookup",
            "product_question": "How a product works, compatibility, specs",
            "return_exchange": "Return, exchange, or replace an item",
            "complaint": "Unhappy with service or product, wants a resolution",
        },
    ),
    "needs_reasoning": von.score(
        instructions="How much thought does a good answer to `message` need?",
        criteria=[
            "A lookup or a one-line fact",
            "A short explanation using product knowledge",
            "A judgment call with trade-offs or an unhappy customer",
        ],
    ),
}


def route_message(message: str) -> dict:
    resp = von.system_one(state={"message": message}, questions=ROUTER_QUESTIONS)
    ans = resp.answers

    intent = ans["intent"]
    reasoning = ans["needs_reasoning"]

    # Low confidence -> fallback to human
    if intent.confidence < 0.4:
        return {"handler": "human", "reason": "low_confidence"}

    choice = intent.choice
    if choice == "order_status":
        return {"handler": "db_lookup", "llm_needed": False}
    elif choice == "product_question":
        return {"handler": "rag_product_llm", "context": "product_docs"}
    elif choice == "return_exchange":
        return {"handler": "rag_returns_llm", "context": "returns_policy"}
    elif choice == "complaint":
        if reasoning.score > 1.0:
            return {"handler": "human_supervisor", "priority": "high"}
        return {"handler": "empathy_llm", "context": "complaints"}

    return {"handler": "human"}


if __name__ == "__main__":
    msg1 = "Where is my package for order #3948?"
    print(msg1, "->", route_message(msg1))

    msg2 = "Does this widget work with 220V European outlets?"
    print(msg2, "->", route_message(msg2))

    msg3 = "I have been waiting 3 weeks and your representative was rude to me on the phone!"
    print(msg3, "->", route_message(msg3))
