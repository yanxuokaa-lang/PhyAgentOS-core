# Testing Jev on public and private data: classifier or filter?

[TypeSafe](https://typesafe.ai) opened early access to [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) on 15 September. The headline numbers in the launch compare it with a frontier model writing text. Most teams do not run classification on a frontier model. The decisions a pipeline makes thousands of times a day (is this page worth reading, is this email a request, which bucket does this go in) mostly run on the small, fast tier already: flash-lite class models, gpt-5.4-mini, gpt-5.6-luna. That is the tier Jev has to beat, and the one I measured it against.

Jev is a model that does not write text. You give it some text and a question with fixed answers, and it gives back a probability for each answer. One call looks like this:

```json
POST https://api.typesafe.ai/v1/systemone
{
  "model": "jev-latest",
  "state": {"text": "i am sorry that i was unable to get the full brunt of the comedy ."},
  "questions": {
    "sentiment": {
      "type": "choice",
      "instructions": "Is this movie review positive or negative?",
      "criteria": {"negative": "Unfavourable", "positive": "Favourable"}
    }
  }
}
```

```json
{
  "answers": {
    "sentiment": {
      "choice": "negative",
      "probabilities": {"negative": 0.97, "positive": 0.03},
      "confidence": 0.93
    }
  },
  "usage": {"input_tokens": 336},
  "model": "jev-1.13.0"
}
```

That call took 850 ms from my laptop and cost \$0.000014: 336 input tokens at \$0.042 per million, and output is free because there is none. A `choice` can have up to 255 options and comes back with a probability per option plus a `confidence` for the pick. A `noul` (TypeSafe's name for a yes/no question) comes back as one number, the probability of yes, so 0.05 is a confident no and 0.95 a confident yes. One call can carry many questions. TypeSafe does not say how `confidence` is computed; it is not the top probability (0.93 against 0.97 above), but gating on the top probability instead gave the same picture on the public sets, within a point. Confident, in this post, means that number was within 0.1 of either end for a yes/no, or 0.9 or higher for a pick-one.

I spent two days and about 16,000 calls finding out what it is good for. First on four public classification datasets, with two small OpenAI models answering the same questions. Then on a few thousand real decisions from the pipelines I work on, scored against what actually happened, not against another model's opinion.

## TL;DR

- On short-text classification it is level with or ahead of gpt-5.4-mini and gpt-5.6-luna on three of four public sets, at 5 to 56 times lower cost, with a median under a second.
- Its probabilities hold near 0 and 1. On tasks it can do, confident answers were right 90 to 100% of the time; the middle is a coin flip.
- It is best on short input with crisp labels. The longer the input and the fuzzier the labels, or the more business logic the question carries, the more its accuracy and its confidence fall together. On a whole-document read it is worse than the small model we run today, and no prompt fixed that.
- So it is a filter, not a replacement. It takes the calls it is confident about at either end; the rest fall back to the model you already use.

## Four public datasets

300 random items from each of [Enron spam](https://huggingface.co/datasets/SetFit/enron_spam), [SST-2](https://huggingface.co/datasets/stanfordnlp/sst2), [AG News](https://huggingface.co/datasets/fancyzhx/ag_news) and [Banking77](https://huggingface.co/datasets/legacy-datasets/banking77). Every model got the same question and the same one-line description per label, and had to return a probability for every option, because a gate needs that. The two OpenAI models ran through the Responses API with reasoning set to low; gpt-5.6-luna is one of the models on TypeSafe's own eval board.

![Jev's accuracy minus the better LLM, per dataset](public/accuracy.png)

| dataset | Jev | gpt-5.4-mini | gpt-5.6-luna | Jev, accurate when confident (share of items) |
|---|---|---|---|---|
| Enron spam, 2 options | **98.7** | 97.7 | 98.0 | 99.6 (90%) |
| SST-2 sentiment, 2 | **95.7** | 92.7 | 93.0 | 98.8 (82%) |
| AG News topic, 4 | **91.3** | 88.3 | 89.7 | 94.7 (88%) |
| Banking77 intent, 77 | 76.0 | 78.7 | **81.7** | 89.9 (66%) |

"When confident" is the pick-one sense: Jev's confidence in its pick was 0.9 or higher. Jev took all 77 Banking77 options in one question without complaint; it is also the one set where both LLMs beat it.

![Seconds per call, with a line at one second](public/latency.png)

| per call | Jev | gpt-5.4-mini | gpt-5.6-luna |
|---|---|---|---|
| median | 0.8-0.9 s | 1.4-4.2 s | 1.4-5.0 s |
| 95th percentile | 0.9-1.1 s | 2.1-5.9 s | 2.1-6.8 s |
| slowest of 300 | 1.4-1.8 s | 3.9-16.0 s | 3.6-10.5 s |

Jev takes about the same time whatever the task. The LLMs get slower as the options grow, because they write a probability for each one. All of this was measured with 20 calls in flight, which is what a pipeline sees. Jev's tail is not always this clean: at 100 calls in flight on our own pages a few per thousand took 10 to 35 seconds.

![One LLM call buys this many Jev calls](public/cost.png)

Two notes on cost. The LLM bills include output tokens, and asking for a probability per option is what makes them expensive: on Banking77 that is about 700 output tokens a call, which is why gpt-5.4-mini costs \$3.81 per thousand there. Ask for the choice alone and the bill drops severalfold, but then there is no confidence to gate on. And the gap depends on what you compare against: 5 to 15× against gpt-5.6-luna, 100× and more against a model that reasons hard or an agent. More on that below.

Every case, every per-item answer from all three models, and the scoring code are in this repo; see Reproduce below.

## On our own pipeline

Public sets are a sanity check. What we cared about was whether Jev could replace any of the classifier work we run today, thousands of small decisions a week. For these the answer key is what happened afterwards: did the page produce anything, did a human keep the task the agent started.

| decision | items | agrees with the outcome | accurate when confident (share of items) | possible action |
|---|---|---|---|---|
| is this page useful for routing a document | 1,005 | 97.8% | 100% (63%) | reject filter: 60% of pages under the line, nothing lost |
| is this an administrative page | 1,005 | 95.8% | 99.8% (86%) | reject filter: 52% under the line, nothing lost |
| is this a locations schedule page | 1,005 | 98.0% | 99.3% (94%) | reject filter: 25% under the line, nothing lost |
| does this page carry a value for one of 135 report rows | 1,005 | 68.6% | 78% (57%) | leave it to the current model |
| should this inbound email start a task | 800 | 87.4% | 96% (69%) | filter with a stated loss |

*Agrees with the outcome: Jev's yes/no, cutting P(yes) at 0.5, against what happened afterwards (the routing row is checked against today's classifier, since those pages have no outcome of their own). Accurate when confident: accuracy where P(yes) was at or below 0.1 or at or above 0.9, and the share of items in that band, which on pages is mostly the low end.*

The simple page types are where it earns its keep. It matched the outcome 96 to 98% of the time, matched our existing classifier 95 to 97%, and its probabilities barely move: the same page asked twice differs by about 0.01. It went in front of the classifier as a reject filter: any page with a P(yes) under the threshold (set as described below) skips the model, everything else goes through as before. Replaying five production runs with the filter off and on gave the same output on all 1,005 pages, with 50 to 67% fewer routing calls, 45 to 74% fewer admin-page calls and 8 to 13% fewer locations calls, the last one smaller because the classifier reads pages in pairs and a pair is only skipped when both pages are under the line.

The hard page type is where it does not. "Does this page carry a value for one of 135 report rows" means telling apart a mention of something from an actual value for it, and Jev fires on the mention. It needed about twice as many extraction jobs to match our recall, and its probability swung by 0.5 between runs on the same page. A general LLM asked the same question failed the same way, so this is the task, not the model.

The inbox was the most interesting. Today every mail on a shared service inbox gets an agent session that decides whether it is a request we should work on; that costs about 12 cents and 94 seconds at the median, and most of the time the answer is no. Given the same mail and the same written rules, Jev matched the recorded outcome 87% of the time, and 96% on the mail it was confident about (69% of it). But a few genuine requests come back near zero, a confident no (a routine request that happens to name a third party reads to it like a policy change), so there is no lossless threshold. What it offers is a trade: drop everything under 0.03 and 78% of the non-requests disappear, at the cost of 5 of the 231 real requests in this set. Those five are mostly short forwards from colleagues and mail whose only evidence is a photo, which Jev cannot read; route those two kinds to the agent regardless and what is left loses about one request in 140.

## What each decision costs us today

| decision | today, per 1,000 | Jev call alone, per 1,000 | time per call today | time per call, Jev |
|---|---|---|---|---|
| triage one inbound email | \$120 (an agent session each) | 15¢, 800× cheaper | 94 s | ~1 s |
| gate one document page for routing | \$1.50 (small LLM) | 11¢, 14× | 2-3 s, more under load | ~1 s |
| gate one page for admin extraction | \$3.50 (small LLM) | 6¢, 58× | up to 20 s under load | ~1 s |

On the document pipeline the saving is modest in dollars, a few percent of a run, and large in call volume: about a quarter of all calls to that rate-limited provider go away. On the inbox it is the reverse: few calls, but each one is an agent session, so the dollars are the point.

## Trust the ends, not the middle

![Every call as a dot, by confidence for the public sets and by P(yes) for our pages](public/confidence.png)

The useful thing about the number is that the ends mean what they say. On the public sets, 82% of the answers came back with confidence 0.9 or higher and 96% of those were correct; below 0.9 it was right 55 to 72% of the time depending on the band. On our pages the number is P(yes), so the two ends are a confident no and a confident yes, and both hold: 82% of pages came back under 0.1 and 0.3% of those turned out to matter; the 4% at 0.9 and above mattered 97% of the time; the 14% in between run from 6% to 83% depending on the band. No single cut-off works there. So trust the ends, and hand the middle to a model that can actually read the thing. (The page panel pools the three gates, 2,559 calls, because the routing gate contributes only the 549 pages that have an outcome of their own.)

You do not pick the drop threshold by hand. Take every item you know was a real positive, find the lowest P(yes) Jev gave any of them, and put the line at half of that. Set it on part of your data, check it on the rest, and re-check as new data arrives, because next month can bring a real positive lower than any you have seen. On our gates I set it on four of the five production runs and checked it on the fifth, rotating, and no fold lost a page. The lines came out at 0.12, 0.065 and 0.025 for routing, admin and locations, from 187, 124 and 61 positives, and put 25 to 60% of pages under the line. The line comes from your positives, not from the confident band, so it can land on either side of 0.1. On email it put almost nothing under the line, so there is no useful lossless threshold there, only the trade above.

## 100× cheaper than what?

| compared against | cost gap | speed gap |
|---|---|---|
| gpt-5.6-luna, reasoning low, 2-4 options (measured above) | 5-6× | 1.7-1.9× |
| gpt-5.6-luna, 77 options (measured above) | 15× | 6× |
| gpt-5.4-mini, reasoning low (measured above) | 23-56× | 1.7-5× |
| Terra, with reasoning, on TypeSafe's own board | ~75× | ~25× |
| a frontier model (Every's test) | ~580× | ~25× |
| a full agent session doing the same classification, call for call | ~800× | ~100× |

An LLM's output tokens cost 4 to 8 times its input tokens, and with reasoning on, most of its tokens are thinking. Jev has no output tokens. Keep reasoning low and the answer to a few tokens, and most of the headline gap disappears; what is left is the cheaper input price and a single pass.

## What others are seeing

Three days in, most of the noise is reaction to the announcement. The [Hacker News thread](https://news.ycombinator.com/item?id=49717558) is near 500 comments and very few are from people who had called the API. The argument there is about framing: the 193× and 444× headline compares Jev with a frontier model writing its answer out as text; "cannot hallucinate" means the output is typed, not that it is right; and [TypeSafe's own eval board](https://evals.typesafe.ai/) grades against the average of GPT-6 Astra and Claude Fable 5.1 rather than ground truth, where Jev sits at 67.8% against 74.1% for the best LLM, never top on accuracy, 200× cheaper. When a commenter called it "basically a zero-shot classifier", the [CEO replied "exactly right"](https://news.ycombinator.com/item?id=49718727), which is the most useful sentence in the thread. Within two days there were open imitations on GitHub and Hugging Face and a [70-repo awesome list](https://github.com/AnotiaWang/awesome-jev).

The measured reports, where someone ran Jev against an LLM on the same task, split by the shape of the task.

Short input, crisp labels: it wins or ties. [Near Here](https://nearhere.events/blog/typesafe-jev-mistral-gemini-event-validation) ran event listings against Mistral Small 4 and Gemini 3.5 Flash-Lite on high reasoning: 48 of 50 to their 42 and 43, none of the 13 real events rejected, 0.6 s against 2.9 and 3.4 s, 4¢ per thousand against 37¢ and \$2.50. Vercel's CTO [ran it on an existing classifier eval](https://x.com/cramforce/status/2100269198727602468) that used Gemini 2.5 Flash Lite and it "won both on quality (saturated the eval) and speed (6x)". [HiringCafe](https://x.com/h_nilforoshan/status/2100411132498641301) scores resumes against job descriptions with human labels: Spearman 0.79 at 2¢ per thousand, against 0.77 for DeepSeek V4 Flash at 14¢ and 0.72 for Gemini 3.1 Flash-Lite at 29¢. [A 19,500-email spam run](https://github.com/bitnovus/jev-spam-eval) got 98.3% zero-shot, level with a logistic regression trained on 15,000 of those emails, and its calibration matches mine: 0.1% spam below 0.1, 99.9% at 0.9 and above, 38% in the 0.5 to 0.6 band. [Classmethod](https://dev.classmethod.jp/en/articles/jev-for-llm-model-routing/)'s model router: 40 of 40 at 2.5¢ per thousand, lower confidence in the middle tier. [Every](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds): 6 of 7 planted defects at 0.35 s a passage, where Claude Fable 5.1 caught 7 at 8.8 s.

Longer input, fuzzier labels, or a verdict that needs reasoning: it loses, and the fix is the same each time. [A 2,000-email phishing bench](https://github.com/anisselbd/jev-phishing-bench) had Jev at 62.6% against 81.3% for Claude Haiku 4.5, with worse calibration and a 5-point swing from question wording alone; five narrow yes/no signals plus a logistic regression reached 95%, and Haiku on the same five signals got 93%. [Samuel Sacco](https://github.com/SamuelSacco/jev-exploration)'s 800-item difficulty ladder found the probabilities overstate the low end and understate the high end, yet everything at 0.9 or above was right, on 21 to 32% of items; his advice, treat the number as a score and fit your own cut-offs on a few hundred labelled cases, is where I landed too. [A poker study](https://backnotprop.com/blog/jev-poker/) against a solver: 63% on random spots, 94% on easy ones. And TypeSafe's weakest workflow on its own board is invoice processing, 61.8% against 79.1%, the same kind of whole-document read where it failed for me.

## Verdict

Filter. Jev is cheap and fast, answers only yes/no and pick-one questions, and its probability means what it says at the ends. That is enough to put it in front of a classifier and not enough to put it in place of one.

Below the drop line it was never wrong on our data, so those items skip the classifier and nothing downstream changes; on our page gates that was 25 to 60% of pages. Above 0.9 it is right 97% of the time on our pages and 90 to 99.6% on every public set, so where most items land up there you can act on Jev's answer and never call the classifier at all. We did not need that on pages, where only 3 to 9% land that high, but on a spam gate it is the bigger end: on Enron, 90% of items sit at 0.9 or above with 99.6% accuracy, nine classifier calls in ten gone. Everything in between falls back to the model you already use, exactly as today.

The pattern held in every test, mine and other people's. Short input, crisp labels: near-perfect and confident. Long input, fuzzy labels, or a rule that needs reasoning: accuracy and confidence fall together, and the fix is to split the question into narrow yes/no signals and combine them in code, which took the phishing bench from 63% to 95%.

That ceiling is the thing to watch. Everything Jev gets wrong here is a long-input problem, and [TypeSafe's own notes](https://docs.typesafe.ai/model-jaggedness/jev-1.13) say accuracy falls as the state grows. If a later version holds up on a full page or a full thread the way this one holds up on a sentence, the filter becomes the classifier, even for the complex ones, and the fallback becomes the exception.

Set both lines on your own recorded outcomes, check them on data you did not use to set them, and never ask it anything that needs the whole document read before the answer exists. The title's question has a one-word answer; the work is in where you draw the two lines.

*The public half is in this repo, down to every per-item answer; the pipeline numbers are from our own production code and data.*

## Reproduce

```bash
uv sync
cp .env.example .env          # TYPESAFE_API_KEY and OPENAI_API_KEY
uv run python -m jev_eval summarize                     # table from the shipped results, no API calls
uv run python -m jev_eval run sst2 --backend jev-latest # rerun one dataset (300 calls, about a cent)
uv run python -m jev_eval run sst2 --backend gpt-5.6-luna
uv run python -m jev_eval build ag_news --n 300 --seed 7  # rebuild a case file from Hugging Face
```

Files:

- `cases/<dataset>.jsonl`: one row per item: `id`, `state.text`, `state.questions` (the question and label descriptions sent to every model), `expected`, `meta` (source dataset and split).
- `results/<dataset>.<backend>.jsonl`: one row per item: the model's `choice`, `probabilities`, `confidence`, and `_meta` (latency, tokens, cost, the served model id). Rows with `_meta.error` are failed calls.
- `results/summary.json`: what `summarize` prints, as data.
- `jev_eval/`: `datasets.py` (case builders), `backends.py` (the two API clients), `scoring.py`, `cli.py`.

## Datasets

- [SetFit/enron_spam](https://huggingface.co/datasets/SetFit/enron_spam), test split
- [stanfordnlp/sst2](https://huggingface.co/datasets/stanfordnlp/sst2), validation split (the test split is unlabelled)
- [fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news), test split
- [legacy-datasets/banking77](https://huggingface.co/datasets/legacy-datasets/banking77), test split, CC BY 4.0

Rows are fetched through the Hugging Face datasets-server, so no dataset is vendored beyond the 300-row samples here.

## Notes

- Jev's `state` here is just the text; the question carries the label descriptions. The OpenAI models get the same text and questions as JSON in the user turn, with a short developer message asking for the JSON shape.
- Prices per 1M tokens used: Jev \$0.042 input, output free; gpt-5.4-mini \$0.75 / \$4.50; gpt-5.6-luna \$0.20 / \$1.20. Add a model to `OPENAI_PRICES_PER_M` in `backends.py` to compare another one.
- Jev's confidence is the API's own `confidence` field; for the OpenAI models it is the highest probability they returned.
- Both clients retry 429, 503 and 529 with backoff.
