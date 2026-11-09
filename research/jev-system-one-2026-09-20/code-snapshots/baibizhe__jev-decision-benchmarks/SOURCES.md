# Sources and publication notes / 来源与发布说明

Snapshot date / 整理日期: **2026-09-19**.

The actual model in all three JEV experiments is `typesafe/jev-1.13-20260917`. Other models were not rerun. This is an independent report of adapted decision tasks, not an official leaderboard submission or endorsement.

三项实验的实际 JEV 版本一致。其他模型均引用原始论文或官方榜单，本仓库不代表官方认证排名。

## MetaTool

- [Paper v6](https://arxiv.org/html/2310.03128v6), Tables 3, 4, and 13.
- [Official repository](https://github.com/HowieHwong/MetaTool/tree/35e81bb7576826e980c80fed8f8c0a2b4a1e6fbb), commit `35e81bb7576826e980c80fed8f8c0a2b4a1e6fbb`.
- [Dataset count discussion](https://github.com/HowieHwong/MetaTool/issues/7) and [answer extraction clarification](https://github.com/HowieHwong/MetaTool/issues/10#issuecomment-2504792136).
- [JEV statistics](data/metatool/summary.json), [frozen protocol](data/metatool/protocol.json), [baseline values](data/metatool/published_baselines.csv), and [paper table excerpts](data/metatool/paper-tables.json).

The comparison includes 24 CSR conditions and two additional multi-tool outcome-distribution metrics for nine models: 234 values, including 208 paper baseline values. Paper model names are retained; “ChatGPT” is not mapped to a current API model. Published sample counts differ from the public package for two subtasks. The long-form CSV leaves historical baseline sample counts unspecified.

## When2Call

- [Official repository and published MCQ results](https://github.com/NVIDIA/When2Call/tree/ecc8d42388e91ab37e7e737d48e16e8ecea3d1dc), commit `ecc8d42388e91ab37e7e737d48e16e8ecea3d1dc`.
- [NAACL paper](https://aclanthology.org/2025.naacl-long.174.pdf), Tables 4, 5, 12, and 14–19.
- [JEV statistics](data/when2call/summary.json), [per-example scores](data/when2call/per_example.csv), [matrix calculations](data/when2call/derived_checks.json), and [verified interaction](data/when2call/hallucination_case.json).
- Archived [official README](data/when2call/official_README.txt) and paper excerpts: [page 7](data/when2call/paper_page_7.txt), [page 18](data/when2call/paper_page_18.txt), [page 19](data/when2call/paper_page_19.txt).

The source README retains its original Acc-Norm and BFCL columns for provenance; those columns are not imported into this project's comparisons. Ordinary accuracy for six baselines is recomputed from consistent paper matrices. Table 13's conflicting matrix is excluded. The Judge route is recorded separately; its hallucination denominator is not inferred from the nominal 300-example subset size.

## BFCL V4

- [Official leaderboard](https://gorilla.cs.berkeley.edu/leaderboard) and [official CSV](https://gorilla.cs.berkeley.edu/data_overall.csv).
- [Pinned evaluator](https://github.com/ShishirPatil/gorilla/tree/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/berkeley-function-call-leaderboard), commit `f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`, evaluator version `2025.12.17`.
- [Saved leaderboard CSV](data/bfcl/official_leaderboard.csv), [retrieval/version metadata](data/bfcl/leaderboard_metadata.json), [comparison](data/bfcl/comparison.csv), and [JEV statistics](data/bfcl/summary.json).

The page stated last updated **2026-04-12** when retrieved on **2026-09-19**. It contains 109 model/mode records. The homepage uses the 13 configurations selected for this report, preserving their modes; the detailed report includes every record. Irrelevance equally weights subset accuracies (240 and 884 examples), rather than pooling all 1,124 examples. Three JEV repetitions do not triple the independent sample count. The raw official CSV contains other task columns for provenance; they are not presented as evaluated JEV results.

## Artifact provenance and reuse

[The manifest](data/manifest.json) records SHA-256 hashes for the 19 byte-preserved input snapshots. `original_artifact` identifies a path in the original experiment archive, not another file promised to exist in this repository. Internal paths and source-code hashes inside archived protocols or metadata likewise refer to that original archive. The BFCL metadata also records an original HTML snapshot that is retained there.

This publication contains saved statistics, published-source excerpts, per-example When2Call scores, and one full When2Call request/response example. The complete inference harnesses, other raw API interactions, and original result archives remain outside this report package. The generator verifies and reproduces the published reports; it does not rerun model inference. Two narrative templates preserve findings from the earlier reports and are versioned alongside the generated reports.

`results.csv` is a long-form view of the included metrics. `value` is blank when unavailable; `unit` distinguishes percentages from F1 scores on a 0–100 scale; `direction=descriptive` marks outcome distributions that should not be maximized. `n` is the relevant sample count when supported by the evidence, not the number of repeated requests. Baseline source precision is retained. Displaying two decimals does not imply more measurement precision than the source.

Attribution and rights in third-party excerpts remain with their original authors. Consult the linked repositories and papers for their terms. No blanket license is applied to third-party data or papers through this repository.

原始归档路径仅用于追溯，不代表此公开包包含全部 API 日志或完整评测程序。原始统计与已发表基线支持离线核验表格，不能消除评测协议差异，也不能据此恢复基线的逐题显著性检验。引用内容的权利归原作者所有。
