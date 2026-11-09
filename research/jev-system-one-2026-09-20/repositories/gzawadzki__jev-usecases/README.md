# Typed decisions on Polish text with TypeSafe Jev

Seven demos of [TypeSafe](https://docs.typesafe.ai/) **Jev**: a model that returns probabilities, not prose. Your code owns routing, thresholds, and side effects.

| Use case | What Jev decides | Measured |
| --- | --- | --- |
| [Play review inbox](usecases/play-reviews/) | Topic, bug, churn, feature request → product queue | **2975** reviews in **301.63 s** (8 workers) |
| [Czajka guard](usecases/czajka-guard/) | Hate, vulgar, sex, crime, self-harm → pass / review / block / support | 7 Polish samples, one request each |
| [Agent router](usecases/agent-router/) | Which specialist card to load (or none) | 10 bank-chat utterances |
| [Rozprawka](usecases/rozprawka/) | CKE matura rubric (35 pkt), not AES 1–6 | 3 papers: 31/35, 0, 0 |
| [Essay scoring](usecases/essay-scoring/) | AES 2 rubric traits → 1–6 plus teacher inbox | 1000 train essays, QWK **0.34** (winners ~0.84) |
| [Seed comparator](usecases/seed-comparator/) | Error type of a model answer vs ground truth | 9 cases |
| [RL data triage](usecases/rl-data-triage/) | Keep / downsample / discard / quarantine episode logs | 12 traces: bucket **12/12**, mode **11/12** |

Jev is a hosted System One model: you write the questions. It is not a chatbot and it does not generate replies.

## Setup

Python 3.10 or newer. A [TypeSafe API key](https://console.typesafe.ai/settings/keys).

```bash
pip install -r requirements.txt
cp .env.example .env
# set TYPESAFE_API_KEY
```

On Windows PowerShell use `copy .env.example .env`.

Run every command from the **repository root**.

## Run each demo

**Review inbox** (50-row smoke test, then the full timed corpus):

```bash
python usecases/play-reviews/classify.py --sample 50
python usecases/play-reviews/classify.py --workers 8
python usecases/play-reviews/summarize.py --write
```

**Czajka** (safety screen):

```bash
python usecases/czajka-guard/guard.py --demo
python usecases/czajka-guard/guard.py "Ale zagrałeś tragicznie w tym meczu, usuń konto."
```

**Agent router** (one Choice + Nouls over capability cards → one specialist or none):

```bash
python usecases/agent-router/router.py --demo
python usecases/agent-router/router.py "gdzie są wnioski kredytowe?"
```

**Rozprawka** (CKE 35-point matura paper):

```bash
python usecases/rozprawka/grade.py
```

**Essay scoring** (AES 2 rubric, not a Kaggle submit):

```bash
python usecases/essay-scoring/score.py
```

**Seed comparator**:

```bash
python usecases/seed-comparator/compare.py
```

**RL data triage** (offline IL / RL filter over symbolic episode logs):

```bash
python usecases/rl-data-triage/triage.py
python usecases/rl-data-triage/triage.py --write
```

## What stays in code

- Fetching and deduping Play reviews
- Inbox policy (`churn ≥ 0.70` → `churn_watch`, and so on)
- Guard routing (`self_harm` → support, not a silent block)
- Loading at most one agent context after the router
- AES integer caps (off-prompt, no thesis)
- CKE gates: *błąd kardynalny* zeroes the paper; under 300 words drops composition and language
- Exact-string compare in seedlab (this demo only replaces the *semantic* axis)
- Offline RL buckets (`quarantine` / `discard` / `downsample` / `keep`) and the IL vs offline split; env reward stays env math

## Data and license

MIT for the code. Do not commit `.env`.

Play review text belongs to its authors and Google Play. The scrape is a public snapshot for the demo, not a full dump of the store.

Ground-truth fragments in the seed comparator come from the `visual-emphasis` seed in a multimodal seed workshop. Jev does not see the images.

RL episode logs in `usecases/rl-data-triage/data/episodes.json` are synthetic bank-chat traces. They are not production traffic.
