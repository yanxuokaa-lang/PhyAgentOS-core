# Improving OpenJev's MMLU-Pro accuracy

Research and exploratory measurements, September 18, 2026 UTC.

The current evidence does not show a prompt-only path to 83–85% with this model
and one output token. A small explicit reasoning budget is the most informative
next experiment if that constraint can be relaxed. First, a serving precision
control would help distinguish model limitations from implementation effects.
Production was not changed during this investigation.

## What the published scores actually establish

- Our previous matched 1,000-question API evaluation found **Jev 82.9% versus
  OpenJev 58.8%**. These are zero-shot API results on a subset, not full-test
  reproductions of a published reasoning benchmark.
- [Qwen's model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) reports 85.2%
  MMLU-Pro, enables thinking by default, recommends generous output budgets, and
  recommends JSON answer formatting for multiple-choice evaluation. It does not
  establish an 85.2% one-token, thinking-disabled baseline. The exact settings for
  that table are not fully specified there.
- [NVIDIA's checkpoint card](https://huggingface.co/nvidia/Qwen3.6-35B-A3B-NVFP4)
  reports BF16 85.6% and NVFP4 85.0%, with a maximum output budget of 131,072 tokens
  for MMLU-Pro. This makes weight quantization alone an unlikely explanation for
  our entire gap, but does not validate our particular serving configuration.
- [MMLU-Pro's authors](https://github.com/TIGER-AI-Lab/MMLU-Pro) specifically report
  that chain-of-thought helps on this reasoning-focused benchmark.
- [TypeSafe describes](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
  a new architecture, parallel sampler, and training method called Reinforcement
  Learning for Calibrated Decisions. These are the company's claims, not an open
  recipe we have reproduced. Matching Jev's API and output probabilities does not
  reproduce its model training.

## Fresh one-token experiments

We sampled 256 questions from the pinned test split, excluding all 1,000 questions
in the earlier comparison. Seed: 20260918. All five variants ran at concurrency
16 on the existing NVFP4/B200 server. They used the native chat template with
thinking disabled, exactly one generated token, and argmax of selected label
logprobs. Test labels were retained locally and were not sent to the server.

| Prompt | Correct / 256 | Accuracy | Change from current, paired 95% interval | Mean input tokens |
|---|---:|---:|---:|---:|
| Current OpenJev | 142 | 55.5% | — | 265 |
| Plain MCQ | 148 | 57.8% | +2.3 points [-2.3, +6.6] | 221 |
| Plain MCQ, JSON answer prefix | 153 | 59.8% | +4.3 points [0.0, +8.6] | 229 |
| Five direct-answer examples | 152 | 59.4% | +3.9 points [-0.4, +7.8] | 1,004 |
| Five examples with rationales | 147 | 57.4% | +2.0 points [-2.0, +5.9] | 1,477 |

These are exploratory, unadjusted paired bootstrap intervals (10,000 draws).
Selecting the highest of four alternatives introduces selection bias; confirm it
on new questions before claiming an improvement. The 55.5% current result uses a
different sample from the earlier 58.8%, so it does not indicate a regression.

The plain prompt combines question and options into one user message. JSON adds
an assistant prefix of `{"answer": "` and asks for a JSON answer, but still scores
only the next letter. Five-shot variants use the five official validation examples
for each subject. The rationale variant includes their supplied explanations in
the input; it does **not** generate reasoning for the test question. There were no
exact question-text overlaps between these demonstrations and the probe sample.

JSON increased mean probability mass on valid answer letters from 87.2% to 99.9%,
but format compliance is not correctness or probability calibration. It beat plain
MCQ by only five questions. The current prompt predicted A 58 times versus 34 true
A answers; this motivates a label-bias experiment but does not establish its cause.

The probe calls SGLang directly with the compiled prompt, omitting the public API's
separate shared-state warmup. Radix caching stays enabled. These are prompt
diagnostics, not latency measurements of the full production API.

Reproduction: [script](../../prompt_probe.py), [manifest](manifest.json),
[metrics](metrics.json). The deployment remained at `edb8f61`; the probe source
hash is recorded in the manifest. All 1,280 requests completed successfully.
The public health endpoint returned 200 afterward.

## Short thinking: a practical next experiment

Use explicit budgets such as **0, 64, 256, and 1,024 reasoning tokens**, then allow
one final answer token. This is a proposal, not a measured accuracy result.

For each question: reuse the state prefix, generate at most B reasoning tokens
(stop sooner on the thinking-end token), close the thinking block if truncated,
then append a final-answer prefix and score one answer token. Question branches
can still run concurrently, and SGLang can reuse their cached prefixes. Each
branch now has sequential decoding, so this changes the latency and compute model.
Do not assume that an arbitrary `reasoning_effort="minimal"` field is supported.

[Qwen's official thinking-budget example](https://github.com/QwenLM/Qwen3/blob/main/docs/source/getting_started/thinking_budget.md)
uses this two-call pattern: bounded reasoning followed by a final-answer call.
It needs no SGLang source patch. A raw `max_tokens` cap alone can end in unfinished
reasoning with no answer. Validate the exact Qwen3.6 template and token IDs rather
than copying older Qwen3 constants. SGLang has had
[budget-enforcement reports](https://github.com/sgl-project/sglang/issues/25536)
on older releases; that report alone does not establish a current-version bug.

Measure paired accuracy, actual generated tokens, fraction forcibly truncated,
end-to-end p50/p95 latency, and throughput at concurrency 16. Use the same prompt
format across budgets. Include both reasoning-heavy MMLU-Pro and BoolQ. Small
budgets can interrupt a useful calculation, so accuracy need not rise monotonically.

One additional issue: final label probabilities become conditional on the sampled
reasoning trace, not just the original state. A wrong trace can make the final
answer confidently wrong. Recheck calibration; do not assume the existing BoolQ
curve survives. Avoid routing solely on unvalidated answer confidence.

## Other experiments, in priority order

1. **Serving precision control.** Keep weights and prompts fixed, compare FP8 KV
   cache against `--kv-cache-dtype auto` (verify it resolves to BF16) in an isolated
   deployment. Our pinned checkpoint has neither a KV quantization scheme nor
   saved KV output-scale tensors; see [audit](kv-cache-audit.json). SGLang's
   [KV-cache documentation](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/quantized_kv_cache.mdx)
   warns about uncalibrated scaling. The warning can also be
   [misleading for checkpoints with embedded scales](https://github.com/sgl-project/sglang/issues/31224),
   which is why we inspected the actual checkpoint. No runtime scale inspection
   or BF16 comparison has been performed, so the accuracy impact remains unknown.
   Also compare shared-state warmup versus full-prefill answers under identical
   prompts. If discrepancies persist, use a BF16-weight reference for a small set.
2. **Label-bias correction.** [PriDe](https://arxiv.org/abs/2309.03882) estimates
   answer-token priors using option permutations and corrects logits; contextual
   calibration offers a related [content-free-input approach](https://arxiv.org/abs/2102.09690).
   Estimate parameters on validation data and evaluate on untouched questions.
   Permutation ensembles cost multiple prefills and must preserve options that
   refer to other letters. Global temperature scaling cannot improve our argmax
   accuracy because it does not change the ordering of logits.
3. **Training for immediate decisions, if one token remains essential.** Distill
   a reasoning teacher into a direct-answer student on separate training data,
   randomize label assignments, and evaluate both accuracy and calibration on
   held-out tasks. [Stepwise internalization of CoT](https://arxiv.org/abs/2405.14838)
   demonstrates this research direction on arithmetic/GSM8K, not an 85% MMLU-Pro
   guarantee. This is a training project, not a serving flag or a small prompt fix.

Do not optimize repeatedly on the published 1,000-question subset. Freeze a
candidate configuration, then run a fresh paired comparison before deployment.
