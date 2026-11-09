# Jev AI — quickstart & FAQ

A short, friendly starting point for **Jev**, the AI model from **TypeSafe AI** that answers
with **typed, calibrated decisions** instead of text — so software can act on the output directly.

> ▶️ **Play with Jev right now, free, no waitlist:** **[jevtypesafeai.com](https://jevtypesafeai.com)**

Community-maintained, not affiliated with TypeSafe AI. Official site: [typesafe.ai](https://typesafe.ai).

---

## 30-second version

- **Jev is not a chatbot.** It's a *System One* model built to be **called by other software**.
- You send it context + questions; it returns a **choice**, a **score**, or a **yes/no probability**.
- It **can't hallucinate a format** — the answer type is fixed by your request.
- **~70–500 ms**, **$0.042 / M input tokens** (output free), no type errors by construction.

## FAQ

**What is Jev AI?**
TypeSafe AI's first *System One* model. It turns messy input into typed, calibrated decisions
for automation. → [full explainer](https://jevtypesafeai.com/what-is-jev)

**How is it different from ChatGPT / an LLM?**
LLMs write prose for humans. Jev returns structured values with probabilities for machines —
faster, cheaper, and safe to branch on in code.

**How do I use the Jev API?**
One `POST` to `/v1/systemone` with a `state` and `questions`. → [API guide with curl / Python / TS](https://jevtypesafeai.com/how-to-use)

**How much does Jev cost?**
$0.042 per million input tokens, output free (~$0.0004 per decision). → [pricing](https://jevtypesafeai.com/pricing)

**Can I try Jev without the waitlist?**
Yes — the [free playground](https://jevtypesafeai.com) runs real API calls in your browser.

**Who makes Jev?**
TypeSafe AI, founded by ex-OpenAI researcher Diogo Almeida; launched September 2026 with $40M seed.

## The three answer types

```text
choice → pick one of up to 255 labelled options (+ probabilities)   e.g. routing, classification
score  → a position on a 2–10 level ordered scale                   e.g. risk, urgency, quality
noul   → a calibrated yes/no as a probability 0.0–1.0               e.g. gates, filters, guardrails
```

## Try it

- ▶️ Free playground: https://jevtypesafeai.com
- 📖 What is Jev: https://jevtypesafeai.com/what-is-jev
- 🔌 API guide: https://jevtypesafeai.com/how-to-use
- 💵 Pricing: https://jevtypesafeai.com/pricing

## License

MIT. "Jev", "System One" and "TypeSafe AI" are trademarks of their respective owners.
