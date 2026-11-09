# padflow-jev-evals

A small, public benchmark of the decisions PadFlow makes inside software.

PadFlow is a SaaS platform for land development companies: schedules, budgets,
draws, lot takedowns, document intake, and QuickBooks Online sync. Most of the
"intelligence" it needs is not chat. It is a typed decision with a confidence
score that the software acts on: post it, or send it to a human.

This repo publishes those decisions as JSON schemas, a labeled set of
anonymized examples, and a script that scores any OpenAI-compatible model on
them. It exists so a decision model (TypeSafe Jev, or anything else) can be
measured against the workload it would replace.

## The decisions

| Decision | Question the software asks | Schema | Examples |
|---|---|---|---|
| `route_document` | An email or file arrived. Which project, and what kind of document is it? | `schemas/route_document.json` | `data/route_document.jsonl` |
| `code_transaction` | A QuickBooks transaction synced. Which budget line and draw does it belong to? | `schemas/code_transaction.json` | `data/code_transaction.jsonl` |
| `classify_import_value` | A value was read from an imported schedule or budget page. What is it? | `schemas/classify_import_value.json` | `data/classify_import_value.jsonl` |

Each schema has the same shape: an `input` object, a `decision` enum, and a
`confidence` in `[0, 1]`. PadFlow posts automatically above a threshold and
queues the rest for a human. The threshold is a product decision; the model's
job is to be calibrated.

## What is measured

For each model and each decision:

- **Accuracy** — the share of examples where `decision` matches the label.
- **Calibration** — accuracy of the examples the model marked above the
  auto-post threshold (default 0.90). This is the number that matters. A model
  that is 85% accurate but knows which 60% it is sure of is more useful than a
  model that is 90% accurate and always says 0.95.
- **Cost per decision** — from the provider's usage report.
- **Latency** — wall time per call, p50 and p95.

## Baseline

Run `scripts/run_baseline.py` to fill this table. Every cell below was
produced by a run on 2026-09-17; nothing here is estimated.

n = 5 / 5 / 7 rows per decision (`route_document` / `code_transaction` /
`classify_import_value`). **These are the hand-written seed rows, not labeled
production rows**: the export from PadFlow on 2026-09-17 found 0 human-labeled
rows per decision (see `data/README.md` for why), so the labeled set does not
exist yet and neither does the public slice of 25. At n=5 one row is 20 points
of accuracy; read the columns as "the runner works and this is the shape of
the task", not as a ranking.

| Model | Decision | Accuracy | Accuracy above 0.90 | Auto-post rate | $ / decision | p50 ms |
|---|---|---|---|---|---|---|
| openai/gpt-5.6-luna | route_document | 0.800 | 0.800 | 1.00 | 0.00011 | 1148 |
| openai/gpt-5.6-luna | code_transaction | 0.600 | 0.600 | 1.00 | 0.00016 | 1866 |
| openai/gpt-5.6-luna | classify_import_value | 1.000 | 1.000 | 1.00 | 0.00010 | 1267 |
| anthropic/claude-sonnet-5 | route_document | 0.800 | 1.000 | 0.80 | 0.00193 | 2024 |
| anthropic/claude-sonnet-5 | code_transaction | 0.800 | 1.000 | 0.60 | 0.00177 | 1956 |
| anthropic/claude-sonnet-5 | classify_import_value | 1.000 | 1.000 | 0.86 | 0.00152 | 1785 |
| google/gemini-3.7-flash | route_document | 0.800 | 1.000 | 0.80 | 0.00113 | 2639 |
| google/gemini-3.7-flash | code_transaction | 0.600 | 0.750 | 0.80 | 0.00122 | 2546 |
| google/gemini-3.7-flash | classify_import_value | 1.000 | 1.000 | 1.00 | 0.00102 | 2560 |

All three ran through OpenRouter with `provider.data_collection = deny`, so
no row was routed to a provider that keeps prompts.

Context on the cost side: PadFlow's September 2026 page-reading trial (vision
extraction, a different task from the decisions here) ran $3–$33 per 1,000
pages across four frontier models. The decisions in this repo happen far more
often than page reads, so per-decision price is the constraint.

## Run it

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=...
python scripts/run_baseline.py --model openai/gpt-5.6-luna
python scripts/run_baseline.py --model anthropic/claude-sonnet-5 --decision code_transaction
python scripts/run_baseline.py --model google/gemini-3.7-flash --data-dir private
```

`run_baseline.py` talks to any OpenAI-compatible chat endpoint with JSON
schema output. Set `--base-url` to point it elsewhere. Results land in
`out/<model>.json` and the summary prints as a markdown row you can paste into
the table above.

## The data

`data/*.jsonl` is public and anonymized. Company names, people, project names,
emails, phone numbers, street addresses, and account numbers are replaced with
stable placeholders (`Company_A (grading)`, `Person_3`, `Project_1`,
`123 Placeholder St`) by `scripts/anonymize.py`. Amounts, dates, line-item
descriptions, and document structure are kept, because those are what the
decision depends on.

The labeled set is split: 25 rows per decision are published here, the rest
stay private, and the Baseline table is measured on the full set. Today the
files hold seed rows only -- `data/README.md` has the counts and the reason.
The set will be enough to rank models. It is not enough to certify one.

## License

MIT. Data is released for evaluation use.
