# Jev demo

Five-tab demo of **TypeSafe AI's Jev model** (System One API: typed questions → calibrated
probabilities), covering support ticket triage, LLM guardrails, line-by-line search,
select-don't-generate extraction, and a raw playground.

## Run

```bash
export TYPESAFE_API_KEY="$(cat api_key.txt)"   # or set the env var directly
python3 app.py                                  # http://localhost:8787 (PORT= to change)
```

Python 3.10+, stdlib only, no dependencies.

## Layout

| file | role |
|---|---|
| `app.py` | Dependency-free Python server: serves `index.html` and proxies `POST /api/systemone` / `GET /api/models` to TypeSafe, so the key stays server-side. Reads `TYPESAFE_API_KEY` or `./api_key.txt`. |
| `index.html` | The five-tab UI. Every tab's questions, criteria and thresholds are defined in the `DEMOS` object near the top of the script; add an entry there (`title`, `blurb`, `presets`, `questions()`, `state()`, `decide()`) to add a tab. Results show the resolved model, latency, token usage/cost, probability bars, the code's decision, and the raw request/response JSON. |

The five demo tabs, for quick reference:

| Tab | Use case | What it demonstrates |
|---|---|---|
| **Support ticket triage** | Route a ticket, flag phishing, set priority | Speculative fan-out: 5 questions in one request; code gates on `confidence`. |
| **LLM guardrails** | Screen a message before it reaches an LLM | 4 hazard Nouls + severity Score, routed by a named threshold policy in code. |
| **Line-by-line search** | Find the clause answering a question | Choice over line ids ranks lines; a Noul says whether an answer exists at all. |
| **Select, don't generate** | Pull an email address / amount out of a message | Regex proposes candidates, Jev picks one (or `none`), code copies verbatim. |
| **Raw playground** | Edit state and questions JSON directly | All three primitives, nested-state paths, "count in code". |
