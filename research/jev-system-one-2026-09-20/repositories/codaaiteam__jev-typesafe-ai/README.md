# Jev (TypeSafe AI) — unofficial developer notes

Practical notes and examples for **Jev**, TypeSafe AI's *System One* model — the AI that
returns **typed, calibrated decisions** for software instead of text.

> 🧪 **Try Jev free in your browser (no waitlist):** **[jevtypesafeai.com](https://jevtypesafeai.com)**
> Live playground that runs real `/v1/systemone` calls.

This is a community reference, not affiliated with TypeSafe AI. For official access and docs
see [typesafe.ai](https://typesafe.ai) and [docs.typesafe.ai](https://docs.typesafe.ai).

---

## What is Jev?

Large language models are built to talk to *people*. **Jev is built to be called by
*machines*.** You give it some context (your program state) and the exact questions you need
answered, and it replies with **structured values instead of prose**. Because the shape of the
answer is fixed by your request, Jev can't hallucinate a format or emit an invalid type.

- **Speed:** 70–500 ms (≈ 40–200× faster than a frontier LLM on comparable tasks)
- **Cost:** $0.042 / million input tokens, output free (≈ $0.0004 per decision)
- **Safety:** no hallucinated formats, no type errors, by construction
- **Made by:** TypeSafe AI (founded by ex-OpenAI researcher Diogo Almeida), launched Sept 2026

More background: **[What is Jev?](https://jevtypesafeai.com/what-is-jev)**

## The three question types

Every question you send Jev is one of three primitives:

| type | returns | use for |
|------|---------|---------|
| `choice` | one of up to 255 labelled options + probabilities | routing, classification |
| `score` | a position on a 2–10 level ordered scale | risk, urgency, quality, fit |
| `noul` | a calibrated yes/no as a probability (0–1) | gates, filters, guardrails |

## Quick example

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jev-latest",
    "state": "Customer: I was charged twice and I am furious.",
    "questions": {
      "topic":  { "type": "choice", "instructions": "What is the issue about?",
                  "criteria": { "billing": "money problems", "bug": "broken product" } },
      "urgent": { "type": "noul", "instructions": "Escalate to a human now?" }
    }
  }'
```

Response:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "topic":  { "type": "choice", "choice": "billing", "confidence": 1.0,
                "probabilities": { "billing": 1.0, "bug": 0.0 } },
    "urgent": { "type": "noul", "noul": 0.82 }
  },
  "usage": { "input_tokens": 382, "output_tokens": 55 }
}
```

Because the types are fixed, you branch on results with plain code — `if (answers.urgent.noul > 0.7)` —
no parsing, no regex, no malformed-response risk.

## Common use cases

- **Route & classify** — send a ticket, email, event or document to the right place
- **Score & prioritize** — turn fuzzy judgments into a threshold you can act on
- **Guardrail & gate** — auto-approve the easy cases, escalate the uncertain ones
- **Extract** — turn free text into typed, structured fields

## Links

- ▶️ **Live playground (free, no waitlist):** https://jevtypesafeai.com
- 📖 What is Jev: https://jevtypesafeai.com/what-is-jev
- 🔌 How to use the API: https://jevtypesafeai.com/how-to-use
- 💵 Pricing: https://jevtypesafeai.com/pricing
- 🏢 Official site: https://typesafe.ai

## License

MIT — these notes are free to reuse. "Jev", "System One" and "TypeSafe AI" belong to their
respective owners.
