# OpenJev on a random MMLU-Pro subset

**57.70% accuracy (577/1,000)**; approximate 95% Wilson interval 54.61%–60.73%.

Sampled 1,000 test questions uniformly without replacement, seed 42. This is a subset estimate, not a full-test score. The interval treats questions as independent and does not apply a finite-population correction.

Zero-shot direct answers through OpenJev's `choice` endpoint. State contains only the question; criteria map original answer letters to option text. No gold answers or provided rationales enter the request. The API's selected choice is scored by exact match. No retries based on correctness.

This differs from the benchmark's usual five-shot chain-of-thought setup; do not treat it as a reproduction of published leaderboard scores. Public benchmark training overlap is unknown.

Resolved model: Qwen/Qwen3.6-35B-A3B. API response cost unavailable. Saved responses with in-run retries: 2 (excludes attempts from interrupted collection segments).

| Subject | Correct | Questions | Accuracy |
|---|---:|---:|---:|
| biology | 43 | 48 | 89.58% |
| business | 19 | 58 | 32.76% |
| chemistry | 48 | 122 | 39.34% |
| computer science | 22 | 32 | 68.75% |
| economics | 50 | 71 | 70.42% |
| engineering | 39 | 81 | 48.15% |
| health | 43 | 55 | 78.18% |
| history | 23 | 35 | 65.71% |
| law | 56 | 102 | 54.90% |
| math | 48 | 103 | 46.60% |
| other | 48 | 72 | 66.67% |
| philosophy | 33 | 47 | 70.21% |
| physics | 52 | 113 | 46.02% |
| psychology | 53 | 61 | 86.89% |

Source: [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) ([official evaluation](https://github.com/TIGER-AI-Lab/MMLU-Pro)). The pinned revision, dataset hash, sampled row indices, prompt, and request settings are recorded in metrics.json. Raw dataset text is not committed.
