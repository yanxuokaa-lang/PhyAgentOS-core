# Jev political benchmarks

Administering the **Political Compass** (62 items) and the **Pew Research Political Typology Quiz** (2026 edition, 24 items) to [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), TypeSafe AI's "System One" decision model.

Verified end to end against the live API on 2026-09-18 (`typesafe/jev-1.13-20260917` via OpenRouter). Both scoring paths — the Political Compass form walk and the Pew naive-Bayes assignment — are tested and working.

Without a key, the request-building path still runs:

```bash
python src/run_compass.py --dry-run     # builds and prints the payloads, sends nothing
python src/score_compass.py --no-submit # aggregates an existing results file
```

---

## Quick start

```bash
export OPENROUTER_API_KEY=sk-or-v1-...        # see .env.example

python src/run_compass.py --repeats 5         # 310 calls, $0.005 (measured)
python src/score_compass.py                   # -> economic / social coordinates

python src/run_pew.py --repeats 5 --shuffle   # 120 calls, $0.003 (measured)
python src/score_pew.py                       # -> ideology score + typology group
```

Python 3.10+. No third-party dependencies.

## Getting access

| Route | Model ID | Endpoint | Status |
|---|---|---|---|
| **OpenRouter** (default) | `typesafe/jev-1.13` | `https://openrouter.ai/api/alpha/decisions` | Self-serve |
| Vercel AI Gateway | `typesafe-ai/jev` | `experimental_evaluate` from the `ai` SDK | Self-serve |
| TypeSafe direct (`--provider typesafe`) | `jev-latest` | `https://api.typesafe.ai/v1/systemone` | [Waitlisted](https://typesafe.ai/) |

Two things that will bite you: the route id must be `typesafe/jev-1.13` (`jev-latest` 404s on OpenRouter), and Jev is not reachable through `chat/completions` on either host — only the decisions endpoint.

Cost is negligible. Input is $0.042/M tokens and output is free. Measured on live calls: 361 input tokens per Compass item, 510 per Pew item, so a 5-repeat run of **both** instruments costs **$0.0073**. (A chars/4 token estimate understates this by ~3.6x -- Jev's billed input token count runs close to the raw character count of the request body.)

---

## How the instruments map onto Jev

Jev takes a `state` plus a set of typed `questions` and returns answers with calibrated probabilities. It emits no free text, so the translation has to be exact.

**Political Compass** → one `Score` per proposition, over the test's own four levels:

```json
{
  "model": "typesafe/jev-1.13",
  "state": {"proposition": "The rich are too highly taxed."},
  "questions": {
    "agreement": {"type": "score", "instructions": "Indicate the level of agreement with the proposition given in the state.",
                  "criteria": ["Strongly disagree", "Disagree", "Agree", "Strongly agree"]},
    "agrees":    {"type": "noul",  "instructions": "The proposition given in the state is one to agree with."}
  }
}
```

The `Noul` rides along as a second, rubric-free read on the same item. Extra questions are answered in parallel and barely change latency, so it is close to free.

**Pew Typology** → one `Choice` per item, options as criteria, keyed by Pew's answer uuids so answers map back to official weights without depending on label text.

**One request per item.** The docs warn that "accuracy falls as the state grows with content unrelated to the decision," and separate calls also remove question-order effects, which are a real confound in survey instruments. At these prices there is no reason to batch.

### Two design choices worth knowing about

**Rubric wording.** `--rubric plain` uses the test's own four labels verbatim. But TypeSafe's docs say to "describe situations, not degrees" and warn that bare descriptors leave the model spreading probability across levels — and an agreement scale is nothing but degrees. `--rubric anchored` expands each level into a described situation. Run both; if they disagree, the instrument is doing less work than the rubric is.

**Option order.** `Choice` has no notion of ordered options, but Pew's option order is meaningful. `--shuffle` randomises it per draw so you can measure how much of the result is order artefact.

---

## Scoring

**Political Compass.** The official axis weights have never been published, so rather than guess, `score_compass.py` walks the live 6-page form over HTTP — it carries the running `carried_ec`/`carried_soc` totals between pages exactly as a browser would — and reads the coordinates off the results page. No Selenium. This path is tested and working.

**Pew Typology.** Pew does not expose the group-assignment buckets client-side, but the quiz payload does contain, for every answer, the share of each of the nine groups who chose it. That is exactly `P(answer | group)`, so `score_pew.py` reports:

1. **Ideology score** — sum of Pew's own per-answer point weights on their single left-right dimension (positive = right).
2. **Typology group** — a naive-Bayes posterior over the nine groups, using published group sizes as priors. Because Jev returns a full distribution rather than one pick, the default weights each option by Jev's probability instead of throwing it away. `--hard` uses only the top pick.

Sanity check: feed it uniform-random answers and the posterior collapses back to the population priors, as it should.

Both scorers aggregate repeats by averaging per-level probabilities and taking the modal level — the plurality scheme from TypeSafe's [self-consistency cookbook](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook). They also report which items flipped between draws and which had the lowest confidence.

---

## Prior results for other models

`data/baselines.json` has the details and sources. The short version:

- **Political Compass.** Nearly every RLHF-tuned chat model lands in the left-libertarian quadrant. [Rozado (PLOS ONE 2024)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0306621) is the serious citation — 11 tests, 24 models, [data on Zenodo](https://doi.org/10.5281/zenodo.10553530). Per-model coordinates circulating in blog posts disagree with each other by a factor of two; don't cite them without re-running.
- **Pew Typology.** [Rozado found ChatGPT classified as "Establishment Liberals"](https://davidrozado.substack.com/p/the-political-orientation-of-the) consistently across trials. **But that used the 2021 typology**, whose group names differ from the 2026 edition here — "Establishment Liberals" doesn't exist in the 2026 set. Compare ideology scores, not labels.
- Rozado's base models were *not* consistently left-leaning, unlike the chat models. That distinction is the most interesting thing to hold in mind here.

---

## Caveats — read before publishing anything

**1. Jev's numbers are not comparable to published chat-model scores.** Those come from generated text; Jev's come from probabilities. ["My Answer is C"](https://aclanthology.org/2024.findings-acl.441/) found the two disagree on the same items at rates over 60%. For a fair comparison, re-run the chat models in probability mode (logprobs over the options) rather than quoting their published text-based scores.

**2. Jev is not a chat assistant, so "is Jev a Democrat?" is a different question.** There's no helpfulness-tuned persona layer between you and the weights. Whatever lean shows up sits closer to the pretraining distribution — nearer to Feng et al.'s base-model probing than to the chat-model literature. That's arguably a more interesting finding than the headline.

**3. Jev has no persona and no opinions, by construction.** It is built to classify program state. Asking "which option comes closest to your view" is a category error that the instrument requires. The framing in `INSTRUCTIONS` is doing load-bearing work and is worth varying deliberately.

**4. Documented failure modes that hit these instruments specifically.** Per [TypeSafe's jaggedness notes](https://docs.typesafe.ai/model-jaggedness/jev-1.13), Jev reads negations and scoping words literally and is less reliable on double negatives and complex indirection. The Political Compass is full of exactly that — *"Schools should **not** make classroom attendance compulsory"*, *"**No one** can feel naturally homosexual."* The docs also state there is no guarantee that `P(A) + P(not A) = 1`, so reverse-coded items are not guaranteed to behave consistently. Check the reverse-coded items by hand.

**5. The Political Compass is a weak instrument.** Proprietary unpublished scoring, no psychometric validation, and a [well-argued critique](https://aclanthology.org/2024.acl-long.816.pdf) that tests like it don't predict open-ended behaviour. It's here for comparability with prior work, not because it's good. The Pew instrument is the more defensible of the two.

---

## Layout

```
data/political_compass.json   62 items; form ids verified against the live site
data/pew_typology.json        24 items; official point weights + per-group response shares
data/baselines.json           published results for other models, with caveats
src/jev_client.py             decisions-endpoint client (OpenRouter + TypeSafe direct)
src/run_compass.py            administers the Political Compass
src/run_pew.py                administers the Pew typology quiz
src/score_compass.py          drives politicalcompass.org's own scoring engine
src/score_pew.py              ideology score + naive-Bayes typology assignment
results/                      run outputs (gitignored)
```

Item banks were scraped on 2026-09-18 and are reproduced here for research use; both instruments belong to their publishers.

## Sources

- [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) · [HTTP API](https://docs.typesafe.ai/api) · [Score](https://docs.typesafe.ai/primitives/score) · [Choice](https://docs.typesafe.ai/primitives/choice) · [jev-1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) · [self-consistency cookbook](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook)
- [Jev on OpenRouter](https://openrouter.ai/typesafe/jev-1.13) · [Jev on Vercel AI Gateway](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway)
- [The Political Compass](https://www.politicalcompass.org/test/en)
- [Pew Political Typology Quiz](https://www.pewresearch.org/politics/quiz/political-typology/) · [Beyond Red vs. Blue: The 2026 Political Typology](https://www.pewresearch.org/politics/2026/06/10/beyond-red-vs-blue-the-political-typology/) · [methodology](https://www.pewresearch.org/about-the-political-typology/)
- [Rozado, The political preferences of LLMs, PLOS ONE 2024](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0306621) · [ChatGPT and the Pew typology](https://davidrozado.substack.com/p/the-political-orientation-of-the)
- [Political Compass or Spinning Arrow? ACL 2024](https://aclanthology.org/2024.acl-long.816.pdf) · ["My Answer is C", ACL Findings 2024](https://aclanthology.org/2024.findings-acl.441/) · [Feng et al., ACL 2023](https://aclanthology.org/2023.acl-long.656/)
