# Jev on a random MMLU-Pro subset

**82.90% accuracy (829/1,000)**; approximate 95% Wilson interval 80.44%–85.11%.

Sampled 1,000 test questions uniformly without replacement, seed 42. This is a subset estimate, not a full-test score. The interval treats questions as independent and does not apply a finite-population correction.

Zero-shot direct answers through OpenRouter's Jev `choice` endpoint. State contains only the question; criteria map original answer letters to option text. No gold answers or provided rationales enter the request. The API's selected choice is scored by exact match. No retries based on correctness.

This differs from the benchmark's usual five-shot chain-of-thought setup; do not treat it as a reproduction of published leaderboard scores. Public benchmark training overlap is unknown.

Resolved model: typesafe/jev-1.13-20260917. Successful-response cost: $0.0235. Saved responses with in-run retries: 1 (excludes attempts from interrupted collection segments).

| Subject | Correct | Questions | Accuracy |
|---|---:|---:|---:|
| biology | 47 | 48 | 97.92% |
| business | 40 | 58 | 68.97% |
| chemistry | 101 | 122 | 82.79% |
| computer science | 31 | 32 | 96.88% |
| economics | 63 | 71 | 88.73% |
| engineering | 66 | 81 | 81.48% |
| health | 47 | 55 | 85.45% |
| history | 26 | 35 | 74.29% |
| law | 76 | 102 | 74.51% |
| math | 90 | 103 | 87.38% |
| other | 60 | 72 | 83.33% |
| philosophy | 40 | 47 | 85.11% |
| physics | 89 | 113 | 78.76% |
| psychology | 53 | 61 | 86.89% |

Source: [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) ([official evaluation](https://github.com/TIGER-AI-Lab/MMLU-Pro)). The pinned revision, dataset hash, sampled row indices, prompt, and request settings are recorded in metrics.json. Raw dataset text is not committed.
