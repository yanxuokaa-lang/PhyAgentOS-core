# Open JEV

**English** | [简体中文](README.zh-CN.md)

Local, bilingual probability decisions from your context, questions, and candidate answers.

**Open JEV is an independent open-source alternative project inspired by [TypeSafe's Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev). It is not affiliated with, sponsored by, or endorsed by TypeSafe. It does not contain Jev's proprietary code, weights, or RLCD implementation.** The project name does not imply an official open-source release of Jev.

> Research preview. The current backend is frozen **Qwen3-4B-Instruct-2507**, not a newly trained Open JEV foundation model. There is no demonstrated performance lead over Jev or other competing systems.

## Demo

![Open JEV English interface with example context, two questions, and actual model results](docs/images/demo-en.png)

English UI and English example, captured from real local inference. The displayed probabilities and elapsed time belong to this demonstration run, not the benchmark below.

## What it does

- Accept English or Chinese context, free-form questions, and your own candidate descriptions. No intent registration or question-specific training is required to submit a new question; reliable performance on arbitrary tasks is not guaranteed.
- Return a choice and relative probabilities **only over the supplied candidates**. No additional answer or abstention option is inserted.
- Support Choice and Binary decisions, multiple questions per request, editable examples, and JSON export.
- Run inference locally, without a paid inference API. The web interface starts in English; switch to 中文 without changing your inputs or results.
- Publish model identity, scoring protocol, evaluation limitations, and a frozen results snapshot.

The current engine reads one next-token answer-label distribution per question rather than generating an explanation. It still uses an autoregressively pretrained language model. Questions currently run sequentially and re-encode the context; shared-context computation is planned, not delivered.

## How it fits into an application

Open JEV turns a bounded decision into a reusable interface:

**Context → your questions and candidate answers → candidate probabilities → your application's next step.**

You define the decisions at request time. The context can contain a message, document excerpt, conversation, or application state serialized as text. Each question has its own candidate set. The API returns stable candidate IDs alongside scores, so an application can map a selected ID to a workflow branch without interpreting a generated explanation.

| Capability available today | What you can do with it |
|---|---|
| Free-form questions and candidate descriptions | Change the decision being asked without adding a fixed intent class or retraining for each question |
| Several questions about the same context | Request topic, requested action, and another relevant property through one API request; execution is currently sequential |
| Choice and Binary outputs | Compare several supplied alternatives, or inspect one designated positive alternative in a two-option decision |
| Full candidate distribution | Retain scores for every supplied answer instead of receiving only the winning label |
| English and Chinese input | Try monolingual and cross-language workflows; assess quality separately for each language combination |
| Local HTTP API and JSON export | Integrate with your own application or save outputs for review and experiments |
| Model and protocol identifiers | Track which model artifact and scoring protocol produced a result |

Open JEV currently accepts text, not raw audio, images, PDFs, or live device feeds. Those inputs need an upstream transcription, extraction, or serialization step. It returns decisions; it does not send messages, operate devices, or execute tools itself.

## Possible use cases

**The examples below are hypothetical integration ideas, not shipped integrations or validated domain benchmarks.** The listed candidates are supplied by the application. They are illustrative rather than a built-in taxonomy, and can be replaced for every request.

| Scenario | Example question and supplied choices | How an application could use the result |
|---|---|---|
| Customer-support routing | “Which queue should handle this message?” → billing / delivery / account access | Suggest the appropriate support queue |
| Email triage | “What does the sender need next?” → an answer / a scheduled meeting / acknowledgement | Organize an inbox or propose a follow-up action |
| Product-feedback analysis | “What is this feedback mainly asking for?” → fix a defect / add a feature / clarify documentation | Group feedback before a product review |
| Meeting follow-up | “Was the launch date agreed?” → agreed / still under discussion | Populate a meeting-review checklist |
| Delivery preferences | “Where should this parcel be left?” → reception / doorstep / collection point | Suggest an instruction for a delivery workflow |
| Document review | “Does the submission contain the requested budget?” → included / missing | Assist a document-completeness check |
| Reading practice | “Which statement best summarizes the passage?” → three teacher-written summaries | Compare selected answers in a learning tool |
| Community moderation triage | “Which review queue best fits this post?” → ordinary discussion / promotion / personal attack | Prioritize moderator review |
| Game dialogue | “How should the character respond?” → cooperate / negotiate / refuse | Select among game-authored dialogue branches |
| Agent tool routing | “Which available tool fits this request?” → document search / calculator / calendar lookup | Propose a tool choice to an agent controller |
| Home-automation language input | “Which lighting adjustment best fits the request?” → dim / brighten / switch off | Propose an action for a separate device controller |
| Incident triage | “Which subsystem best matches these symptoms?” → network / storage / application | Suggest the first troubleshooting queue |
| Knowledge-base maintenance | “Which article needs updating based on this announcement?” → installation / billing / troubleshooting | Direct an editor to one of the supplied articles |
| Workflow branch selection | “What step follows under the policy supplied in this context?” → request details / continue review / close request | Recommend a branch in an existing workflow |

For example, one support message could be evaluated with three independent questions: **which team should handle it**, **whether the customer requests a reply**, and **whether the order number is present**. Each question gets its own supplied choices and probability distribution. The same interface can be reused for a completely different document and question set.

In these examples, classification is a suggested decision, not proof of a fact or authorization to act. The surrounding application owns tool execution, permissions, and any review process. Scores should be validated on representative application data before using numeric thresholds for automation.

## Why use this instead of asking an LLM for a written answer?

**The current Open JEV backend is itself an LLM.** The benefit is a focused decision interface and execution path, compared with asking a general chat model to generate prose or a JSON answer. This is not a claim that LLMs cannot perform these tasks.

| Practical benefit | What Open JEV provides | Important boundary |
|---|---|---|
| Predictable output choices | Successful responses select IDs only from the supplied candidates; the runtime constructs JSON | A valid choice can still be semantically wrong |
| Less answer-parsing work | Applications consume IDs and numeric scores directly, without extracting an answer from prose | Structured-output LLM interfaces can also reduce parsing work |
| Scores for all candidates | Scores are computed from model logits, rather than asking the model to write probability numbers in its response | Logit-derived scores are not automatically calibrated or superior to other scoring methods |
| No explanatory text to decode | The current engine reads a label distribution after a forward pass instead of generating a long response | This avoids that output-generation work, but does not establish an end-to-end speed advantage over an optimized LLM scorer |
| Local control | The documented local setup performs inference without sending context to a hosted model API | Local LLM deployments offer this too; hardware, memory, and electricity still have costs |
| Reusable workflow contract | Different application questions use the same context/question/candidates interface | This is an integration benefit, not a unique model invention |
| Traceable experiments | Responses identify the source model, converted artifact, and scoring protocol | Reproducibility still depends on retaining inputs, versions, and the execution environment |

This interface is a good fit when the possible answers are known beforehand and software needs a selection or distribution. A general text-generation interface remains the better fit when you need an explanation, a draft, code, or an answer that cannot be enumerated in advance. The two can be combined: Open JEV proposes a branch, and a separate language-model call writes the response when needed.

We do **not** currently claim higher accuracy than the same underlying LLM, universal latency or cost savings, calibrated certainty, freedom from semantic errors, or faster multi-question shared-state inference. The frozen measurements below describe the evidence available today.

## Quick start — Apple Silicon

Tested locally on Apple M3, 16 GB unified memory, Python 3.14. Other platforms and dependency combinations have not been validated. The pinned source download is roughly 8 GB; the separate MLX 8-bit copy is roughly 4 GB, so allow additional disk space for both environments and caches.

```bash
# Run from the repository root. Download dependencies and weights once.
python3 -m venv .venv-mlx
.venv-mlx/bin/python -m pip install -r requirements-mlx.lock.txt
.venv-mlx/bin/python scripts/fetch_instruction.py \
  --repo Qwen/Qwen3-4B-Instruct-2507 \
  --revision cdbee75f17c01a7cc42f958dc650907174af0554 \
  --out data/instruction-4b-assets.json
.venv-mlx/bin/python scripts/convert_instruction_mlx.py

DECISION_BACKEND=mlx \
DECISION_ASSETS=data/instruction-4b-mlx8-assets.json \
.venv-mlx/bin/python -m uvicorn decisionmaking.server:app \
  --host 127.0.0.1 --port 8766
```

Open **http://127.0.0.1:8766/**. Stop with Ctrl-C. Model downloads require internet; subsequent inference is local. Do not run several large model processes on a memory-constrained machine.

The existing developer launcher `scripts/run_instruction_demo.sh` additionally checks the locally audited artifact. The explicit command above runs a newly converted model without claiming that conversion has reproduced the frozen evaluation. Matching evaluation panels appear only when corresponding local suites and identity-matched reports exist. The source-only release does not bundle those datasets or weights; historical results below remain available.

## API

```bash
curl http://127.0.0.1:8766/decide \
  -H 'Content-Type: application/json' \
  -d '{
    "state": "The parcel will arrive on Thursday. Do not call the recipient.",
    "questions": [{
      "id": "arrival",
      "type": "choice",
      "question": "When will the parcel arrive?",
      "options": [
        {"id": "tue", "description": "Tuesday"},
        {"id": "thu", "description": "Thursday"}
      ]
    }]
  }'
```

The response includes `choice`, `probabilities`, `elapsed_ms`, device, source revision, and converted artifact identity. Interactive schema: `/docs`; readiness: `/status`. Binary requests contain exactly two options and a `positive_id` matching one of their IDs. The web UI uses the first option as positive.

Limits: 2–8 candidates/question, 4,096 full prompt tokens/question including the chat template, 16 questions in the UI, 100 in the API. Overlength inputs are rejected rather than silently truncated. The experimental Score schema is not quality-validated and is not exposed in the UI.

Probabilities are normalized candidate-label scores, not established estimates of real-world correctness. A value near 100% is allowed; no artificial flattening is applied. Accuracy, calibration, and robustness remain separate evaluation questions.

## Frozen quality baselines

Snapshot: **2026-09-17**, source revision `cdbee75f17c01a7cc42f958dc650907174af0554`. See [machine-readable results](release/benchmark-summary.json) and [freeze record](release/FREEZE.md).

| Local baseline | Fixed development challenge | Reading subset |
|---|---:|---:|
| Qwen3-0.6B instruction, FP16 | 155/236 (65.7%) | 74/128 (57.8%) |
| Qwen3-4B-Instruct-2507, FP16 | 212/236 (89.8%) | 125/128 (97.7%) |
| Same 4B source, MLX 8-bit | 212/236 (89.8%) | 125/128 (97.7%) |

- The development challenge covers email actions, lighting, speech acts, and rule application. It is development evidence, not an independent final test. Per-task/per-language screening is still not fully passed.
- The reading subset contains **32 Belebele passage families × four language views**, not 128 independent passages. It was not used for project training or tuning; overlap with foundation-model pretraining is unknown. This is not the full Belebele benchmark.
- Reading accuracy for the MLX model: English→English 30/32; English→Chinese 32/32; Chinese→English 31/32; Chinese→Chinese 32/32. Arrows indicate context language→question/answer language.
- The 24.2 percentage-point development gain from 0.6B to 4B compares different foundation models and is not an architecture ablation.
- All 364 top choices matched between the evaluated FP16 and MLX copies. Probabilities were **not identical**: maximum absolute candidate-probability differences were 0.1854 on development and 0.0633 on reading. This is not a lossless-quantization claim.

## Observed local performance

Apple M3 / 16 GB. Eight fixed short HTTP requests; sequential observations, not a controlled hardware benchmark.

![Open JEV local latency chart: median request latency and first requests in separate runs](docs/images/performance-en.png)

Chart generated from the frozen aggregate measurements. Each panel starts at zero and uses its own millisecond scale; the first-request bars represent different run conditions.

| Measurement | Earlier FP16 runtime | MLX 8-bit runtime |
|---|---:|---:|
| Median of eight requests | 558 ms | 533 ms |
| First request in that run | 8,007 ms | 555 ms |
| First request after 84 seconds idle | Not matched | 657 ms |
| Reported allocator peak across evaluation | 8.35 GB, MPS | 4.60 GB, MLX |

The observed median latency reduction is about **4.6%**, not a general 10× or 20× speedup. Earlier slow first requests reached 13.5 seconds in a separate run. There is no answer cache or continuous background warmup. Framework memory counters differ, so the peak figures are not a controlled whole-process memory comparison. Long contexts, more questions, cold startup, and other system load can be slower. See [performance investigation](PERFORMANCE.md) for details (Chinese).

**No matched performance comparison against Jev, GLiClass, GLiNER2, or CAPPr has been completed.** Their published measurements are not interchangeable with ours.

## What comes next

1. Independent, source-family-separated bilingual evaluation and fair open-source baselines.
2. Shared-prefix KV reuse and bounded question batching without changing candidate semantics.
3. Train a general decision model only if controlled experiments establish a useful quality/efficiency tradeoff. User-reported failures are regression cases, not a question-specific training curriculum.

The shared-state architecture and earlier training scripts remain research history, not the deployed 4B model. See [roadmap](ROADMAP_AND_POSITIONING.md) (Chinese). Related work: [CAPPr](https://github.com/kddubey/cappr), [LMQL](https://github.com/eth-sri/lmql), [GLiClass](https://github.com/Knowledgator/GLiClass), [GLiNER2](https://github.com/fastino-ai/GLiNER2), and [TypeSafe's LLM adapter](https://github.com/typesafe-ai/system-one-adapter-python). Candidate scoring, natural-language labels, and caching are not claimed as inventions of this project.

## Source release and licensing

Project code: Apache-2.0, see [LICENSE](LICENSE). Third-party models and datasets retain their own licenses; this license does not grant rights to TypeSafe/Jev branding.

- Current foundation model: [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), Apache-2.0 according to its model assets; downloaded separately.
- Reading evaluation: [Belebele](https://huggingface.co/datasets/facebook/belebele), CC-BY-SA-4.0; source data and derived test text are not bundled in this release.
- Historical research also uses Qwen3-Embedding, MASSIVE, and XNLI. Historical data and trained checkpoints are excluded from the publication bundle pending a separate redistribution review.

The release bundle excludes local environments, credentials, downloaded weights, raw/derived datasets, private paths, user request logs, and pre-branding snapshots. It includes aggregate results and checksums, not all materials required to independently reproduce the evaluation; full evaluation reproduction is a remaining release milestone. See [publication checklist](release/PUBLISHING.md).
