# jev-projects

Small projects built against [Jev](https://typesafe.ai) — TypeSafe AI's "System One"
model. Jev doesn't generate text; you give it a `state` (some text/JSON) plus a set of
typed `questions` (yes/no, multiple choice, or a score), and it returns calibrated
answers in ~100-500ms.

Both projects here follow the same shape: define a few fixed questions once, then run
them against a batch of real-world text.

## Setup

Both scripts read your Jev API key from a `.env` file at the repo root:

```
jev_key=your_key_here
```

(`.env` is gitignored — never commit your key.)

## [ethics-dilemma-classifier/](ethics-dilemma-classifier)

Runs five famous ethical dilemmas (the Trolley Problem, the Heinz Dilemma, the Ring of
Gyges, the Lifeboat Dilemma, Torture vs. Dust Specks) through Jev, asking:

- Is this a genuine, contested moral dilemma?
- Which ethical framework best analyzes it (utilitarian / deontological / virtue
  ethics / contractualist)?
- How difficult/contested is it?
- What should actually be done?

`results.html` is a self-contained interactive page (flip cards, hand-drawn scenario
illustrations, charts) built from a real run's output — open it directly in a browser.

```
python3 ethics-dilemma-classifier/ethics_classifier.py
```

## [paper-ranker/](paper-ranker)

Pulls the newest papers from arXiv (`cs.AI` by default) and ranks them against a
stated interest area, asking Jev:

- Is this paper worth reading, given the interest area?
- How novel does the core idea look?
- What type of paper is it (new method / benchmark / survey / applied system)?

```
python3 paper-ranker/paper_ranker.py
```

A more advanced version of this — multiple arXiv categories, a weighted
relevance+novelty score, and a daily GitHub Actions cron that republishes the ranked
list automatically — is deployed at [raaulc.com/projects/ai-paper-radar](https://raaulc.com/projects/ai-paper-radar).
