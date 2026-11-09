# JEV Benchmark – CLASH contradiction detection

Runs the multiple-choice protocol of **CLASH: A Benchmark for Cross-Modal Contradiction
Detection** (Popordanoska, Li & Blaschko, CVPR 2026 Findings, [arXiv:2511.19199](https://arxiv.org/abs/2511.19199),
[code & data](https://github.com/tpopordanoska/clash)) against TypeSafe's **Jev** decision
model (`POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`).

Results: **[results/REPORT.md](results/REPORT.md)** (tables) and `results/summary.json`
(machine-readable). Raw per-sample predictions, including Jev's probability distributions,
are in `results/*_predictions.json`.

## The adaptation

CLASH pairs a COCO image with a caption that contradicts it in exactly one object or
attribute, asks a question about that element, and offers four options: the answer
grounded in the image, the answer grounded in the text, a plausible distractor, and
*"Conflicting information – cannot answer."* (the correct one).

Jev accepts text only ([docs](https://docs.typesafe.ai/concepts/state)), so the image is
replaced by the COCO caption it was annotated with – the caption CLASH derives its
`image_only` answer from. The state sent to Jev is

```json
{"image_description": "<original COCO caption>",
 "caption":           "<conflicting caption>",
 "question":          "<CLASH question>"}
```

and the question is a Jev `choice` over the four CLASH options, using the CLASH
multiple-choice instruction (see [src/jev_clash/prompts.py](src/jev_clash/prompts.py)).
Everything else follows the paper: same 1,289 human-verified test samples, per-sample
option shuffling, strict matching, 1,000-resample bootstrap standard deviations, and the
object/attribute category breakdowns.

Because this turns a cross-modal task into a text-vs-text one, the repository also runs:

| Run | `--condition` | `--source` | What it measures |
|---|---|---|---|
| main | `conflict` | `original` | paper Table 1 analog: conflict detection + modality bias |
| control | `no_conflict` | `original` | consistent input (both texts identical) – false conflict rate |
| harder | `conflict` | `alt_caption` | image represented by a *different* human COCO caption of the same image (859 samples) |
| harder control | `no_conflict` | `alt_caption` | consistent but non-identical texts – false conflict rate |
| ablation | `conflict` | `original` `--rubric` | adds a one-line rubric to the contradiction option |

Each request also carries a `noul` yes/no question ("Do the two sources contradict each
other about the answer?"), reported separately as a spontaneous-detection probe.

## Layout

```
data/      CLASH test split (vendored) + COCO captions for the alt_caption runs (fetched)
baselines/ CLASH authors' released GPT-5 / GPT-4.1 Mini / Gemini 2.5 predictions, re-scored here
src/jev_clash/
  data.py        sample -> Jev view (state, shuffled options, alt-caption selection)
  prompts.py     instruction text
  jev_client.py  thin HTTP client with retry/backoff
  run.py         inference CLI (resumable)
  evaluate.py    scoring, bootstrap, category tables, calibration, REPORT.md
scripts/fetch_coco_captions.py   pulls COCO train2017 captions for the test image ids
results/   predictions, summary.json, REPORT.md
```

## Reproduce

```bash
pip install -r requirements.txt
export TYPESAFE_API_KEY=...             # console.typesafe.ai; see .env.example
python scripts/fetch_coco_captions.py    # ~250 MB download, only needed for alt_caption runs
export PYTHONPATH=src
python -m jev_clash.run --condition conflict    --source original
python -m jev_clash.run --condition no_conflict --source original
python -m jev_clash.run --condition conflict    --source alt_caption
python -m jev_clash.run --condition no_conflict --source alt_caption
python -m jev_clash.run --condition conflict    --source original --rubric
python -m jev_clash.evaluate
```

A full run is ~1,300 requests, well under a minute with `--workers 6`, and costs about
a cent at Jev's $0.042 per million input tokens.

## Credits

Dataset, prompts and evaluation protocol: CLASH authors (see `data/README.md` for the
citation). Baseline predictions: released with the CLASH repository.
