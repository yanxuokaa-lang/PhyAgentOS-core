# Zero-shot email classification with TypeSafe’s Jev

**TypeSafe’s Jev reached 98.64% accuracy on a 5,733-email ham/spam/phishing test using written category definitions and email context, without task-specific fine-tuning or labeled examples in its requests.** A TF-IDF logistic regression classifier trained on roughly 4,600 labeled messages per fold reached 98.87% with the same evidence.

This repository explores how far [TypeSafe](https://typesafe.ai)'s pretrained Jev model can go through **zero-shot classification and context enrichment**. The application supplies an email and definitions of the categories. Jev returns a category and probabilities that code can use directly.

The clearest improvement came from giving the model more of the email to work with. With the **question and category definitions unchanged**, adding link destinations, Reply-To, and attachment metadata raised accuracy from **93.62% to 97.98%**. A further wording change brought it to 98.64%. The context-only change raised phishing recall from **85.71% to 98.43%**, while legitimate messages incorrectly flagged as phishing stayed at one.

The result also extended beyond the main set. On 853 phishing messages from 2024–25, enriched Jev caught **95.31%**, compared with **75.26%** for regression given the same evidence and trained on 9,033 older messages. This later set measures phishing recall only; it contains no legitimate mail for measuring false positives.

The practical appeal is how little task-specific machinery this required: preserve the relevant context, define the decision, and let Jev interpret the evidence. The main enrichment result needed no additional training, labeled demonstrations, or hand-written phishing indicators.

> **What zero-shot means here:** Jev's weights were not updated for these tasks, and its requests contained no labeled demonstrations. Some specifications and experiment choices were informed by earlier labeled errors, so this is zero-shot inference, not a claim of development without labeled feedback. Results are exploratory, use `jev-1.13.0`, and cannot establish whether the public corpora were unseen during pretraining.

## More context, the same zero-shot question

The first version gave Jev the subject, sender where available, and a text body truncated to 6,000 characters. It removed HTML tags, retaining a link's visible words but losing its destination. That left the model judging an impersonated notification without some of the evidence that could expose the impersonation.

The enriched state preserves those original fields and adds:

- Reply-To.
- Visible link text paired with the actual destination and parsed hostname.
- Attachment filenames and content types, without attachment contents.

URLs are extracted from the full textual MIME parts, subject to documented size limits. No links are visited. Code performs extraction and parsing; the model makes the classification judgment.

We reran the original text-only question and evaluated the enriched input on **the same 9,886 messages with the same model version**. A second question tested evidence-focused wording on the enriched state while retaining the category definitions.

| Jev variant | Main accuracy | Main phishing recall | Fresh accuracy | Recent phishing recall |
|---|---:|---:|---:|---:|
| Original question, text only | 93.62% | 85.71% | 92.67% | 91.68% |
| Original question, enriched evidence | **97.98%** | **98.43%** | **95.39%** | **95.31%** |
| Evidence-focused wording, enriched evidence | 98.64% | 98.38% | 95.76% | 94.49% |

On the main set, enrichment corrected **256 errors and introduced 6**. Legitimate messages flagged as phishing stayed at **1**; spam flagged as phishing fell from **16 to 15**. On the fresh set, enrichment corrected 93 errors and introduced 3.

The extra wording improved overall accuracy on the two older sets, largely by reducing legitimate mail classified as spam. It caught fewer recent phishing messages than the original question with enriched evidence. More instruction was not uniformly better.

The missing context explains a concrete failure mode: fake eBay notifications often copied authentic message text. In the rerun, enrichment recovered **100 of 102 eBay-subject phishing messages that text-only Jev called legitimate**. This is a descriptive error slice, not an independent test, and multiple metadata fields changed together; it does not isolate the effect of URLs alone.

[Full paired results, confusion matrices, and extraction limits →](experiments/jev-context/REPORT.md)

## How close does zero-shot Jev get to a trained classifier?

The supervised baseline puts the zero-shot result in perspective: regression learns from thousands of labeled emails, while Jev receives the classification specification and each email's evidence. With enriched context and evidence-focused wording, Jev came within **0.23 percentage points** of enriched regression on the main test and **0.58 points** on the fresh set.

Both regression variants use the original word TF-IDF and logistic regression settings. The enriched variant receives a serialization of the same additional fields Jev saw. Input hashes were checked against every saved Jev request.

| Approach | Main accuracy | Fresh accuracy | Recent phishing recall |
|---|---:|---:|---:|
| Jev, zero-shot, text | 93.62% | 92.67% | 91.68% |
| Jev, zero-shot, enriched | 97.98% | 95.39% | **95.31%** |
| Jev, zero-shot, enriched + evidence-focused wording | 98.64% | 95.76% | 94.49% |
| TF-IDF logistic regression, text | 98.74% | **96.39%** | 70.34% |
| TF-IDF logistic regression, enriched | **98.87%** | 96.33% | 75.26% |
| 50/50 average of enriched Jev and regression | 99.30% | 96.21% | 95.66% |

The ensemble uses the original defined Choice, without the extra wording. Weights are fixed, not fitted.

**Context enrichment closed much of the gap without fitting Jev to the task.** Keeping the question fixed, Jev gained 4.36 percentage points on main accuracy, compared with 0.12 for regression. Regression retained a lead on the fresh set, including after excluding near-copies of main-set messages: **95.08% versus 93.83%** for enriched Jev, or 94.33% with the extra wording.

On recent phishing, equal evidence narrowed but did not remove Jev's advantage. This is evidence of better recall on this particular later collection, not proof of general robustness to distribution shift. The ensemble improved main accuracy and recent recall, but did worse than regression alone on fresh accuracy.

### How the sets and splits work

| Set | Messages | Regression training |
|---|---:|---|
| Main: 1,911 each of ham, spam, and phishing | 5,733 | Five-fold cross-validation; roughly 4,600 training labels per fold |
| Fresh: 1,100 each of ham, spam, and phishing | 3,300 | All 5,733 main messages |
| Recent: phishing from 2024–25 | 853 | All 9,033 main + fresh messages |

Main and fresh phishing come from roughly the same 2005–07 period. “Fresh” means different messages, not later mail. Ham and spam come from email-dataset; phishing comes from Jose Nazario's collection.

Near-duplicate clusters stay together in main cross-validation. Both regression variants use identical folds, and each vectorizer is fitted only on its training partition. A shared sensitivity analysis removes the 902 fresh messages with near-copies in main, leaving 2,398. Grouping uses the original text; relationships revealed only by added metadata can remain across folds.

The text-only regression reproduced all 9,033 original main/fresh classifications. Jev is evaluated without fitting to these training folds; its pretrained knowledge and written specifications are a different source of supervision.

[Matched-evidence report, all confusion matrices, and evaluation details →](experiments/jev-context/REGRESSION_REPORT.md)

## The interface: questions and typed answers

A [Choice](https://docs.typesafe.ai/primitives/choice) selects one category and returns its probability distribution. The three-way experiment uses explicit definitions for legitimate mail, unsolicited spam, and phishing. Advance-fee and lottery scams from strangers count as spam under this specification; phishing involves impersonation intended to obtain sensitive information or induce a malicious action.

This uses the actual question from the experiment:

```python
from typesafe_sdk import AsyncTypeSafeClient
from phish import QUESTIONS

async def classify_email(email: dict, api_key: str):
    async with AsyncTypeSafeClient(api_key=api_key) as client:
        response = await client.system_one(
            state={"email": email},
            questions={"category": QUESTIONS["category"]},
            model="jev-1.13.0",
        )
    return response.choices["category"]
```

The caller supplies parsed evidence in `email`. The enriched experiment's [runner](experiments/jev-context/evaluate.py) constructs that state. Jev's returned Choice label is retained when rounded probabilities tie; ensemble probabilities are normalized before averaging.

For a yes/no decision, a [Noul](https://docs.typesafe.ai/primitives/noul) returns the probability of “yes.” The earlier binary experiments ask whether an email is spam. The three-way experiments above use Choice, not a combination of Nouls.

## What the earlier experiments add

### Binary spam detection: complementary errors

On 18,514 unique email-dataset messages, detailed spam criteria approached a supervised baseline. Regression uses five-fold cross-validation with near-duplicate groups kept together; binary decisions use a 0.5 threshold.

| Approach | Accuracy | AUC | Missed spam | Ham flagged as spam |
|---|---:|---:|---:|---:|
| Jev, plain question | 95.96% | 0.9975 | 54 | 694 |
| Jev, detailed criteria | 98.33% | 0.9984 | 106 | 203 |
| TF-IDF logistic regression | 98.39% | 0.9986 | 149 | 150 |
| TF-IDF naive Bayes | 97.07% | 0.9971 | 367 | 175 |
| 50/50 average of detailed Jev + regression | **99.22%** | **0.9995** | 69 | 75 |

The average reduced regression's 299 errors to 144. Detailed criteria reduced false positives relative to the plain question, but increased missed spam. Breaking the task into nine narrower questions made the errors easier to inspect without yielding a comparable accuracy gain.

### Specifications do not transfer equally well

On Ling-Spam's 2,876 unique messages, Jev's plain question scored **98.57%**, while the detailed criteria scored **97.01%**. Many additional false positives were publishers' book announcements. The input often lacked the subscription context needed to distinguish expected announcements from unsolicited advertising.

TF-IDF trained on Ling-Spam itself reached **99.41%** with naive Bayes. A 50/50 Jev/regression average reached **99.83%**. TF-IDF trained on email-dataset instead scored only **73.0%**. Representative training data changes the comparison.

In the original three-way experiment, category names alone scored **73.1%**, versus **93.5%** with definitions. Much of that change was semantic: the names-only question called many scams phishing that the dataset treated as spam. Those earlier results are separate from the contemporaneous enriched-input rerun above. [Original phishing experiment →](PHISHING.md)

### Later mail and learning curves

On 633 messages from 2026, an earlier text-only Jev question with urgency/authority criteria scored **97.3%** on legitimate versus not-legitimate classification, compared with **72.5%** for regression trained on older mail. Legitimate messages came from only two Python mailing lists; the other messages came from a spam trap. The enrichment experiment has not been run on this set. [Out-of-distribution report →](OUT_OF_DISTRIBUTION.md)

The original learning curves estimate how many labels a trained baseline needs to approach a particular Jev specification:

| Original task and Jev variant | Jev accuracy | Approximate TF-IDF training labels to match |
|---|---:|---:|
| email-dataset, detailed binary criteria | 98.3% | 10,000 |
| Ling-Spam, plain binary question | 98.6% | 200 |
| Three-way, text-only urgency/authority criteria | 94.2% | 100 |

These are sampled learning-curve comparisons, not universal sample-complexity estimates. They **do not measure the label budget needed to match enriched Jev**. The data and scripts are in `results/learning_curve_*.jsonl` and [learning_curve.py](learning_curve.py).

## Limits of the evidence

- **No task-specific fitting is not no supervision.** Detailed binary criteria and some phishing wording were informed by labeled errors. The enriched experiment was motivated by earlier error analysis, and the sets had already been inspected. This is an exploratory study, not a locked benchmark.
- **Pretraining exposure is unknown.** All corpora are public. Later mail is a temporal test for the older-trained regression, but cannot be assumed unseen by Jev.
- **Labels and sources are confounded.** Some phishing-corpus messages are ordinary spam or unreadable; some spam messages are phishing. Phishing comes from a different collection than ham and spam. Authentic notifications from commonly impersonated brands are underrepresented.
- **Recall alone is incomplete.** The recent set contains no legitimate mail, so its high phishing recall cannot establish deployable precision or false-positive rates.
- **The baseline is bounded.** This is word TF-IDF logistic regression with fixed settings, not a tuned supervised ceiling. Character-level URL models, embeddings, fine-tuned transformers, other language models, and production filters are not evaluated.
- **Context is still incomplete.** Bodies are truncated. Enriched state contains bounded link and attachment metadata, not attachment contents, rendered images, recipient history, or independently verified sender authentication. Earlier binary experiments retain their original text-only representation.
- **One model version and mostly single runs.** Repeated calls can change borderline answers. Probability-shaped outputs still require calibration checks. Ensemble gains vary by test set.

## Reproduce

Install [uv](https://docs.astral.sh/uv/), then fetch the source datasets. Predictions are included; source emails are not.

```sh
uv sync
./fetch_dataset.sh
./fetch_nazario.sh

# New enriched-evidence experiment: no API calls for these commands.
uv run python experiments/jev-context/evaluate.py --check
uv run python experiments/jev-context/report.py
uv run python experiments/jev-context/regression.py
```

`report.py` recomputes the Jev tables from saved predictions. `regression.py` reconstructs and verifies the same inputs, retrains both baselines, and writes the matched comparison. Both use the original scripts and datasets at the repository root. See the [experiment README](experiments/jev-context/README.md) for artifacts, extraction limits, and provenance.

### Make new Jev calls

Set `TYPESAFE_API_KEY` in the environment or in the repository's `.env` file. The new runner pins `jev-1.13.0` and resumes successful saved predictions automatically. Running it against the included completed results makes no new requests; use a separate output directory for an independent replication.

```sh
# New output directory: a three-message smoke test, then the full comparison.
JEV_CONTEXT_OUTPUT_DIR=experiments/jev-context/rerun \
  uv run python experiments/jev-context/evaluate.py --limit 3
JEV_CONTEXT_OUTPUT_DIR=experiments/jev-context/rerun \
  uv run python experiments/jev-context/evaluate.py
```

The full paired run made **19,772 requests**: one text-only and one enriched request per email, with two independent questions in the enriched request. It completed without API errors in about **252 seconds** at concurrency 16, using **32.06 million input tokens**. At the earlier recorded rate of $0.042 per million input tokens, that is approximately **$1.35**; this is a historical-rate estimate, not a verified current bill. The three-message smoke test is separate.

### Earlier experiments

```sh
uv run spam_noul.py --questions criteria --all --report
uv run analyze.py
uv run tfidf_baseline.py
uv run learning_curve.py
uv run phish.py --report
uv run learning_curve.py --dataset phish

./fetch_lingspam.sh
uv run spam_noul.py --dataset lingspam --questions criteria --all --report
uv run tfidf_baseline.py --dataset lingspam
uv run learning_curve.py --dataset lingspam

./fetch_ood.sh
uv run ood_test.py --report
```

These report and baseline commands use saved Jev predictions. The older API runners, without `--report`, can overwrite matching result files; add `--resume` to retain successful predictions. The notebooks in `report/` visualize those earlier runs.

## Repository map

| Path | Purpose |
|---|---|
| `experiments/jev-context/` | Enriched input experiment, matched regression comparison, saved predictions, manifests, and reports |
| `spam_noul.py` | Original parsers, binary Noul questions, API runner, and reports |
| `phish.py`, `PHISHING.md` | Original three-way Choice definitions and text-only experiment |
| `tfidf_baseline.py` | Binary supervised baselines and near-duplicate grouping |
| `learning_curve.py` | Original training-label learning curves |
| `analyze.py` | Binary error, calibration, and review-rate analysis |
| `ood_test.py`, `OUT_OF_DISTRIBUTION.md` | Earlier cross-source and later-mail tests |
| `fetch_*.sh` | Source-dataset downloads |
| `results/`, `report/` | Earlier predictions and notebooks |

## Data and acknowledgments

Thanks to the creators of [email-dataset](https://github.com/realprogrammersusevim/email-dataset), published under the MIT license; Jose Nazario for the [phishing corpus](https://monkey.org/~jose/phishing/), under CC BY 4.0; Bruce Guenter for the public [spam archive](http://untroubled.org/spam/); and the contributors to the public python-list and python-announce-list archives.

The Ling-Spam corpus is described in I. Androutsopoulos, J. Koutsias, K.V. Chandrinos, G. Paliouras and C.D. Spyropoulos, “An Evaluation of Naive Bayesian Anti-Spam Filtering,” *Proceedings of the Workshop on Machine Learning in the New Information Age*, 11th European Conference on Machine Learning, Barcelona, 2000, pp. 9–17. Thanks to those authors for creating and sharing it. Its readme asks that published work credit the corpus and notify its author.

Saved predictions refer to emails by source path and contain no email bodies. Dataset licenses and attribution requirements are separate from the code license.

## License

MIT. See [LICENSE](LICENSE).
