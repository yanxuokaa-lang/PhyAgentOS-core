# OpenJev on a random MMLU-Pro subset

**58.80% accuracy (588/1,000)**; approximate 95% Wilson interval 55.72%–61.81%.

Sampled 1,000 test questions uniformly without replacement, seed 42. This is a subset estimate, not a full-test score. The interval treats questions as independent and does not apply a finite-population correction.

Zero-shot direct answers through OpenJev's `choice` endpoint. State contains only the question; criteria map original answer letters to option text. No gold answers or provided rationales enter the request. The API's selected choice is scored by exact match. No retries based on correctness.

This differs from the benchmark's usual five-shot chain-of-thought setup; do not treat it as a reproduction of published leaderboard scores. Public benchmark training overlap is unknown.

Resolved model: Qwen/Qwen3.6-35B-A3B. API response cost unavailable. Saved responses with in-run retries: 0 (excludes attempts from interrupted collection segments).

| Subject | Correct | Questions | Accuracy |
|---|---:|---:|---:|
| biology | 41 | 48 | 85.42% |
| business | 19 | 58 | 32.76% |
| chemistry | 51 | 122 | 41.80% |
| computer science | 22 | 32 | 68.75% |
| economics | 52 | 71 | 73.24% |
| engineering | 44 | 81 | 54.32% |
| health | 46 | 55 | 83.64% |
| history | 23 | 35 | 65.71% |
| law | 52 | 102 | 50.98% |
| math | 49 | 103 | 47.57% |
| other | 50 | 72 | 69.44% |
| philosophy | 34 | 47 | 72.34% |
| physics | 53 | 113 | 46.90% |
| psychology | 52 | 61 | 85.25% |

Source: [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) ([official evaluation](https://github.com/TIGER-AI-Lab/MMLU-Pro)). The pinned revision, dataset hash, sampled row indices, prompt, and request settings are recorded in metrics.json. Raw dataset text is not committed.
