# ASR-Rescore-Bench: A Benchmark for LLM-Based ASR Rescoring

Code for the ASR-Rescore-Bench paper.

[Paper (preprint)](https://arxiv.org/abs/xxxx.xxxxx) · [Leaderboard](LEADERBOARD.md) · [Data card](docs/data.md)

## Abstract

Modern ASR systems often emit an n-best list per utterance.  Rescoring that
list with an external language model — historically an n-gram or a small
neural LM — has consistently lowered WER.  With the rise of LLMs the natural
question is whether a 7B-class instruction-tuned model can do better than a
specialised neural LM, and at what cost.  We benchmark **eleven** rescoring
strategies (n-gram, masked-LM, causal-LM, instruction-tuned chat) across
**five** corpora (LibriSpeech, AISHELL-1, FLEURS, CommonVoice-zh, internal
medical-dialogue), and find that prompt-based rescoring with mid-sized LLMs
narrows the WER gap by 40-60% on average — but only when the n-best list is
large (n ≥ 10) and pre-cleaned for repetition.

## Requirements

```bash
pip install -e ".[full]"
```

`kenlm` is optional (only required for the n-gram baseline).

## Reproducing Results

The pipeline has three stages: **load** an n-best list, **rescore** with a
strategy, **score** the chosen-1-best against references.

```bash
arb rescore --nbest data/librispeech_test_clean_nbest10.jsonl \
            --strategy llm_prompt \
            --model Qwen/Qwen2.5-7B-Instruct \
            --output predictions/qwen2.5-7b__librispeech.jsonl

arb score predictions/qwen2.5-7b__librispeech.jsonl \
          --refs data/librispeech_test_clean_refs.jsonl
```

To reproduce **Table 3**:

```bash
bash scripts/repro_table3.sh
```

(This runs the full grid of strategy × corpus.  Roughly 14 GPU-hours on a single A100.)

## Pre-trained Models

We don't ship any pre-trained model — every rescorer is built on top of an
off-the-shelf LM (Qwen2.5, LLaMA-3, etc.).  Cached n-best lists for the four
public corpora are available in the **release attachments** (see
`docs/data.md`).

## Strategies

| Strategy        | Module                   | Notes                                   |
|-----------------|--------------------------|-----------------------------------------|
| oracle          | `arb.strategies.oracle`  | upper bound — picks the lowest-WER hyp  |
| ngram_lm        | `arb.strategies.ngram`   | kenlm ARPA, length-normalised log-prob  |
| neural_lm       | `arb.strategies.neural`  | causal LM perplexity                    |
| mlm_pll         | `arb.strategies.mlm`     | masked-LM pseudo-log-likelihood         |
| llm_prompt      | `arb.strategies.llm`     | "rank these hypotheses" prompt          |
| llm_listwise    | `arb.strategies.llm`     | one-shot listwise selection             |

## Headline results

| Strategy        | LibriSpeech-clean ↓ | AISHELL-1 (CER) ↓ |
|-----------------|---------------------|--------------------|
| 1-best baseline | 2.45                | 5.32               |
| ngram_lm        | 2.21                | 5.18               |
| neural_lm (GPT-2 medium) | 2.04        | 5.02               |
| mlm_pll (BERT-large) | 1.98           | 4.94               |
| llm_prompt (Qwen2.5-7B) | 1.78        | 4.61               |
| llm_listwise (Qwen2.5-7B) | 1.74     | **4.55**           |
| oracle (lower bound) | 0.62           | 1.41               |

## Citation

```bibtex
@article{asrrescorebench,
  title  = {{ASR-Rescore-Bench}: A Benchmark for LLM-based ASR Rescoring},
  author = {Ruijie Tang},
  year   = {2025},
  journal = {arXiv preprint arXiv:xxxx.xxxxx}
}
```

## License

Code: Apache-2.0.  Data: per-corpus license (see `docs/data.md`).
