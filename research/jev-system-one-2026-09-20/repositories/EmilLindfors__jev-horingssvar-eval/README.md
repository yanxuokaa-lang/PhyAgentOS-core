# jev-horingssvar-eval

An early-access test of TypeSafe's Jev (`jev-1.13.0`) on 24 Norwegian
responses to the 2022 hearing on resource rent tax (grunnrenteskatt) for
salmon farming. Jev is compared with DeepSeek V4.1 Flash, with and without
reasoning, against reference labels written by Claude Fable 5.1.

The write-up is at
<https://lindfors.no/blog/a-first-look-at-typesafes-jev/>. This is a first
look on 24 documents, not a benchmark. `TODO.md` lists what is missing.

## What is here

| Path | What |
|---|---|
| `eval/questions.py` | The eleven questions, shared by every system |
| `eval/run_jev.py` | One Jev request per document |
| `eval/run_llm.py` | The same questions through any chat model on OpenRouter |
| `label/LABEL_GUIDE.md` | The label guide, written before any label existed |
| `label/runs/` | Two independent reference passes, `A_*` and `B_*` |
| `predictions/` | Raw answers, probabilities, tokens, cost and latency per system |
| `analysis/metrics.py` | Agreement, calibration table, cost and latency |
| `results/` | The output of `metrics.py` that the post quotes |
| `data/docs_index.jsonl` | The 25 sampled responses: uid, category, length. No text |
| `scrape/` | Fetch and text extraction |
| `PLAN.md` | The original 250-document design |

`predictions/jev_draft.jsonl` is the first Jev run with shorter question
wording. `predictions/jev.jsonl` uses the wording aligned to the label guide.
The post reports both.

## What is not here, and why

The response texts are not in the repo. They are public documents on
[regjeringen.no](https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/),
and each `uid` is the `?uid=` value of its page there. Senders in the
`Privatperson` category are listed without a name in the index.

The site's `robots.txt` disallows the `?uid=` pages for crawlers. The 25
documents here were fetched by script, once, at one request per second. The
remaining 387 were not fetched. Ask the ministry, or collect by hand, before
running `scrape/fetch.py` without `--sample`.

## Running it

```sh
uv sync
uv run scrape/fetch.py --sample 25      # writes data/raw/, gitignored
uv run scrape/extract.py
uv run eval/run_jev.py                  # needs API_KEY in .env (TypeSafe)
OPENROUTER_API_KEY=... uv run eval/run_llm.py --no-reasoning --workers 1 --name deepseek_noreason
uv run analysis/metrics.py
```

The runners skip any uid already present in their predictions file. Delete
the file to rerun.

## Caveats

- The reference labels come from a model, in a Claude Code session, not from
  a script. They cannot be regenerated exactly. The numbers are agreement
  with those labels, not accuracy.
- OpenRouter routed the DeepSeek runs across 13 providers, so its latency
  figures are a mix.
- I have early access to Jev. TypeSafe did not see the results before
  publication.
