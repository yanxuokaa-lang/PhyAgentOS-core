#!/usr/bin/env python3
"""Verify saved evidence and rebuild bilingual benchmark reports, offline."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
MODEL = "typesafe/jev-1.13-20260917"
DATE = "2026-09-19"
META_PAPER = "https://arxiv.org/html/2310.03128v6"
META_REPO = "https://github.com/HowieHwong/MetaTool/tree/35e81bb7576826e980c80fed8f8c0a2b4a1e6fbb"
WHEN_REPO = "https://github.com/NVIDIA/When2Call/blob/ecc8d42388e91ab37e7e737d48e16e8ecea3d1dc/README.md#mcq-1"
WHEN_PAPER = "https://aclanthology.org/2025.naacl-long.174.pdf"
BFCL_REPO = "https://github.com/ShishirPatil/gorilla/tree/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/berkeley-function-call-leaderboard"
BFCL_BOARD = "https://gorilla.cs.berkeley.edu/leaderboard"
BFCL_SELECTION = [
    "Claude-Opus-4-5-20251101 (FC)",
    "Claude-Sonnet-4-5-20250929 (FC)",
    "Gemini-3-Pro-Preview (FC)",
    "Gemini-2.5-Flash (FC)",
    "GPT-5.2-2025-12-11 (FC)",
    "GPT-5-mini-2025-08-07 (FC)",
    "GPT-4.1-2025-04-14 (FC)",
    "o3-2025-04-16 (FC)",
    "DeepSeek-V3.2-Exp (FC)",
    "Moonshotai-Kimi-K2-Instruct (FC)",
    "Qwen3-235B-A22B-Instruct-2507 (FC)",
    "GLM-4.6 (FC thinking)",
    "Grok-4-1-fast-reasoning (FC)",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads((ROOT / path).read_text())


def read_csv(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def near(actual, expected, context, tolerance=1e-9):
    require(math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=tolerance),
            f"Value mismatch: {context}")


def table_key(row):
    return tuple(str(row.get(k) or "") for k in ("subtask", "shots", "policy", "scenario", "metric"))


def matrix_metrics(matrix):
    n = sum(map(sum, matrix))
    correct = sum(matrix[i][i] for i in range(4))
    f1 = []
    for i in range(4):
        support = sum(matrix[i])
        predicted = sum(row[i] for row in matrix)
        f1.append(2 * matrix[i][i] / (support + predicted) if support + predicted else 0)
    return n, correct, correct / n * 100, mean(f1) * 100


def verify_sources():
    manifest = read_json("data/manifest.json")
    paths = [item["path"] for item in manifest["files"]]
    require(len(paths) == len(set(paths)) == 19, "Unexpected source inventory")
    for item in manifest["files"]:
        digest = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        require(digest == item["sha256"], f"Source hash mismatch: {item['path']}")

    meta = read_csv("data/metatool/comparison.csv")
    ms = read_json("data/metatool/summary.json")
    baseline = read_csv("data/metatool/published_baselines.csv")
    models = list(meta[0])[7:]
    require(len(meta) == 26 and len(models) == 9 and len(baseline) == 208, "MetaTool coverage")
    require(models[0] == "JEV", "MetaTool model order")
    require(ms["complete"] and ms["expected"] == ms["completed"] == ms["valid"] == 8574,
            "MetaTool completion")
    require(ms["actual_models"] == {MODEL: 8574}, "MetaTool model identity")
    conditions = {}
    for item in ms["conditions"]:
        key = (str(item["subtask"]), str(item["shots"]), item["policy"], item["scenario"] or "")
        conditions[key] = item
        near(item["csr_percent"], item["correct"] / item["n"] * 100, "MetaTool count")
    require(sum(x["n"] for x in conditions.values()) == 8574, "MetaTool condition count")
    lookup = {table_key(row): row for row in meta}
    for row in meta:
        condition = conditions[table_key(row)[:4]]
        require(int(row["jev_n"]) == condition["n"], "MetaTool denominator")
        metric = "csr_percent" if row["metric"] == "csr" else row["metric"] + "_percent"
        near(row["JEV"], condition[metric], "MetaTool condition score")
    for row in baseline:
        near(lookup[table_key(row)][row["model"]], row["percent"], "MetaTool published score")

    when = read_csv("data/when2call/comparison.csv")
    ws = read_json("data/when2call/summary.json")
    records = read_csv("data/when2call/per_example.csv")
    wp = ws["primary"]
    require(len(when) == 22 and len(records) == wp["n"] == 3652, "When2Call coverage")
    require(len({r["uuid"] for r in records}) == 3652, "When2Call duplicate UUID")
    labels = ["direct", "tool_call", "request_for_info", "cannot_answer"]
    matrix = [[0] * 4 for _ in labels]
    for row in records:
        require(row["valid"] == "True", "When2Call invalid response")
        matrix[labels.index(row["gold"])][labels.index(row["prediction"])] += 1
        require(int(row["correct"]) == int(row["gold"] == row["prediction"]), "When2Call correctness")
    require(matrix == wp["confusion_matrix"], "When2Call confusion matrix")
    n, correct, accuracy, f1 = matrix_metrics(matrix)
    require(correct == wp["correct"] == 2733, "When2Call correct count")
    near(accuracy, wp["accuracy"] * 100, "When2Call accuracy")
    near(f1, wp["macro_f1"] * 100, "When2Call four-class F1")
    no_tools = [r for r in records if r["gold"] == "cannot_answer" and r["no_tools"] == "True"]
    hallucinations = [r for r in no_tools if r["prediction"] == "tool_call"]
    require(len(no_tools) == 258 and len(hallucinations) == 197, "When2Call hallucination counts")
    near(wp["tool_hallucination"]["rate"], 197 / 258, "When2Call hallucination rate")
    require(sum(int(r["correct"]) for r in no_tools) == 16, "When2Call no-tool accuracy")
    local = [r for r in when if r["protocol"] != "official_mcq_continuation_likelihood"]
    require(len(local) == 1 and MODEL in local[0]["model"], "When2Call JEV row")
    for field, value in [("accuracy_pct", accuracy), ("macro_f1_0_100", f1),
                         ("tool_hallucination_pct", 197 / 258 * 100)]:
        near(local[0][field], value, "When2Call table " + field)

    official_lines = (ROOT / "data/when2call/official_README.txt").read_text().splitlines()
    official = {}
    in_mcq = False
    for line in official_lines:
        if line.startswith("| Model"):
            in_mcq = "Acc-Norm" in line
        elif in_mcq and line.startswith("|") and not line.startswith("|--"):
            cells = [re.sub(r"[*_]", "", x.strip()) for x in line.strip("|").split("|")]
            official[cells[0]] = (float(cells[1]), float(cells[3].rstrip("%")))
    require(len(official) == 21, "When2Call official MCQ source coverage")
    derived = read_json("data/when2call/derived_checks.json")
    accepted = []
    for row in when:
        if row in local:
            continue
        score, hall = official[row["model"]]
        near(row["macro_f1_0_100"], score, "When2Call official F1")
        near(row["tool_hallucination_pct"], hall, "When2Call official hallucination")
        if row["accuracy_pct"]:
            table = row["accuracy_provenance"].removeprefix("derived_from_paper_table_")
            accepted.append(int(table))
            entry = derived["appendix_matrices"][table]
            total, hit, acc, mf1 = matrix_metrics(entry["matrix"])
            require(total == 3652 and hit == int(row["correct"]), "When2Call paper matrix count")
            near(row["accuracy_pct"], acc, "When2Call derived accuracy")
            near(round(mf1, 1), score, "When2Call paper F1 cross-check")
    require(accepted == [14, 15, 16, 17, 18, 19], "When2Call accepted matrices")
    require(next(r for r in when if r["model"] == "Llama 3.1 70B Instruct")["accuracy_pct"] == "",
            "Inconsistent Table 13 must remain excluded")
    case = read_json("data/when2call/hallucination_case.json")
    require(case["uuid"] == sorted(r["uuid"] for r in hallucinations)[0], "Case selection rule")
    example, request, response = case["dataset_example"], case["request_record"], case["response_record"]
    require(example["tools"] == [] and example["correct_answer"] == "cannot_answer", "Case gold/tools")
    choice = response["response"]["answers"]["next_response"]["choice"]
    require(choice == "c1" and request["choice_to_label"][choice] == "tool_call", "Case API choice")
    require("play_spotify_song" not in request["request"]["state"], "Tool leaked into case state")
    require(request["request_sha256"] == response["request_sha256"], "Case request/response identity")
    criteria = request["request"]["questions"]["next_response"]["criteria"]
    for candidate, label in request["choice_to_label"].items():
        require(criteria[candidate] == example["answers"][label], "Case original candidates")
    judge = read_csv("data/when2call/judge.csv")
    require(len(judge) == 9 and {r["protocol"] for r in judge} == {"official_llm_as_judge"}, "Judge isolation")

    bfcl = read_csv("data/bfcl/comparison.csv")
    bs = read_json("data/bfcl/summary.json")
    bo = read_csv("data/bfcl/official_leaderboard.csv")
    require(len(bfcl) == 110 and len(bo) == 109, "BFCL official coverage")
    require(bs["status"] == "complete" and bs["completed_requests"] == bs["valid_responses"] == 10938,
            "BFCL completion")
    lookup = {r["Model"]: r for r in bo}
    for row in bfcl[1:]:
        source = lookup[row["model_and_mode"]]
        for key, field in [("irrelevance_detection_percent", "Irrelevance Detection"),
                           ("relevance_detection_percent", "Relevance Detection")]:
            near(row[key], source[field].rstrip("%"), "BFCL published " + field)
    irr_values, rel_values = [], []
    for name in ["primary_1", "primary_2", "primary_3"]:
        subsets = bs["primary"][name]["subsets"]
        for key, total in [("irrelevance", 240), ("live_irrelevance", 884), ("live_relevance", 16)]:
            require(subsets[key]["expected"] == total, "BFCL sample count")
        irr_values.append(mean(subsets[k]["correct"] / subsets[k]["expected"]
                               for k in ["irrelevance", "live_irrelevance"]))
        rel_values.append(subsets["live_relevance"]["correct"] / 16)
    for a, b in zip(irr_values, bs["repeated_metrics"]["Irrelevance/accuracy"]["values"]):
        near(a, b, "BFCL per-run weighted score")
    near(mean(irr_values), bs["repeated_metrics"]["Irrelevance/accuracy"]["mean"], "BFCL mean")
    near(bfcl[0]["irrelevance_detection_percent"], mean(irr_values) * 100, "BFCL CSV mean", 1e-8)
    near(bfcl[0]["relevance_detection_percent"], mean(rel_values) * 100, "BFCL CSV relevance")
    require(rel_values == [0.875] * 3, "BFCL positive scores")
    require(set(BFCL_SELECTION) <= lookup.keys() and len(BFCL_SELECTION) == 13, "BFCL requested selection")
    return meta, when, bfcl


def format_table(model_header, rows, columns, highlight=True):
    """columns: (label, direction, percent); missing values never compete."""
    best = []
    for j, (_, direction, _) in enumerate(columns):
        values = [Decimal(str(values[j])) for _, values in rows if values[j] not in (None, "")]
        best.append((min if direction == "down" else max)(values) if values else None)
    lines = ["| " + " | ".join([model_header] + [c[0] for c in columns]) + " |",
             "|---|" + "---:|" * len(columns)]
    for model, values in rows:
        cells, has_best = [], False
        for j, value in enumerate(values):
            if value in (None, ""):
                cells.append("—")
                continue
            number = Decimal(str(value))
            cell = f"{number:.2f}" + ("%" if columns[j][2] else "")
            winner = highlight and number == best[j]
            has_best |= winner
            cells.append(f"**{cell}**" if winner else cell)
        name = f"**{model}**" if has_best else model
        lines.append("| " + " | ".join([name] + cells) + " |")
    return "\n".join(lines)


def homepage_tables(meta, when, bfcl, zh=False):
    header = "模型 / 模式" if zh else "Model / mode"
    model_names = list(meta[0])[7:]
    main = meta[:6]
    require([(r["subtask"], r["shots"], r["policy"]) for r in main] == [
        ("1", "0", "single"), ("1", "5", "single"), ("3", "0", "single"),
        ("3", "5", "single"), ("4", "0", "at_most_two"), ("4", "0", "exactly_two")], "MetaTool main columns")
    meta_labels = (["相似选择 0-shot ↑", "相似选择 5-shot ↑", "正确弃权 0-shot ↑", "正确弃权 5-shot ↑",
                    "最多两个 ↑", "必须两个 ↑"] if zh else
                   ["Similar 0-shot ↑", "Similar 5-shot ↑", "Abstain 0-shot ↑", "Abstain 5-shot ↑",
                    "At most two ↑", "Exactly two ↑"])
    mr = [("JEV 1.13 (Choice)" if m == "JEV" else m, [r[m] for r in main]) for m in model_names]
    wc = (["普通准确率 ↑", "Macro F1 ↑", "工具幻觉率 ↓"] if zh else
          ["Accuracy ↑", "Macro F1 ↑", "Tool hallucination ↓"])
    wr = [("JEV 1.13 (Choice)", [when[-1][k] for k in ("accuracy_pct", "macro_f1_0_100", "tool_hallucination_pct")])]
    wr += [(r["model"], [r[k] for k in ("accuracy_pct", "macro_f1_0_100", "tool_hallucination_pct")]) for r in when[:-1]]
    byname = {r["model_and_mode"]: r for r in bfcl}
    bkeys = ["irrelevance_detection_percent", "relevance_detection_percent"]
    br = [("JEV 1.13（二元适配；三次均值）" if zh else "JEV 1.13 (binary adapter; 3-run mean)",
           [bfcl[0][k] for k in bkeys])]
    br += [(name, [byname[name][k] for k in bkeys]) for name in BFCL_SELECTION]
    bc = (["Irrelevance：正确弃权 ↑", "Relevance：正确行动 ↑"] if zh else
          ["Irrelevance: correct abstention ↑", "Relevance: correct action ↑"])
    return [format_table(header, mr, [(x, "up", True) for x in meta_labels]),
            format_table(header, wr, [(wc[0], "up", True), (wc[1], "up", False), (wc[2], "down", True)]),
            format_table(header, br, [(x, "up", True) for x in bc])]


def readme(meta, when, bfcl, zh):
    tables = homepage_tables(meta, when, bfcl, zh)
    if zh:
        return f"""# JEV 决策能力评测

我们用这三个数据集的指标评估 JEV 能否选对工具、判断何时调用或不调用，以及是否会在没有可用工具时仍选择调用。

[English](README.md) | 简体中文

## MetaTool

评测模型能否根据用户需求，从候选工具中选对一个或多个工具，并在没有合适工具时选择不调用。

{tables[0]}

CSR 为完整工具集合选择正确率。JEV 使用 Choice 适配；论文模型生成工具名后抽取答案。相似选择和正确弃权的公开包各有 995 题，论文各记 975 题；多工具条件各 497 题。[论文 v6 表 3、4]({META_PAPER}) · [完整场景与协议](reports/metatool.zh-CN.md) · [CSV](data/metatool/comparison.csv)

## When2Call

评测模型能否在直接回答、调用工具、向用户追问和说明无法完成之间选对下一步，并统计没有可用工具时仍选择调用的比例。

{tables[1]}

共 3,652 题。JEV 同时读取四个候选并选择；官方 MCQ 分别计算候选续写似然。普通准确率仅有 6 个官方模型可由论文矩阵可靠复算；`—` 表示缺失。F1 以 0–100 展示，固定四类且本数据集上限为 75。工具幻觉率只统计无工具且应当拒答的 258 题，JEV 为 197/258。[官方 MCQ]({WHEN_REPO}) · [报告与幻觉实例](reports/when2call.zh-CN.md) · [CSV](data/when2call/comparison.csv)

## BFCL V4

本表使用 BFCL 的行动／弃权分项，评测模型能否在该用工具时选择调用、在工具不适用或缺少必要信息时选择不调用。

{tables[2]}

本表采用指定的 13 个官方模型配置；完整 109 条模型／模式记录见[详细报告](reports/bfcl.zh-CN.md)和 [CSV](data/bfcl/comparison.csv)。其他模型均为 FC 模式，GLM 保留 thinking 标记。JEV 使用二元适配，三次结果取均值。Irrelevance 为 240 题和 884 题两个子集准确率的等权平均；Relevance 为 16 题，每次答对 14 题。榜单读取于 **2026-09-19**，页面标注最后更新 **2026-04-12**。[官方榜单]({BFCL_BOARD})

## 如何阅读这些表

**加粗表示该表每列数值最优，并加粗对应模型名；并列均标出。** 模型名加粗表示至少一列最优，不表示所有列或整体最好。↑ 越高越好，↓ 越低越好。比较使用保存数值的原始精度，页面显示两位小数；缺失值不参与比较。

这是公开成绩与 JEV 适配实验的描述性对照。各表下的输入、输出、样本或重复次数差异意味着这些数值不构成严格同协议排名或显著性结论。BFCL 加粗范围仅限首页展示模型。三个 benchmark 不合成总分。

## 评测记录

JEV 实际版本为 `{MODEL}`，推理日期为 {DATE}。MetaTool 完成 8,574 个输入（4,287 条源记录的不同提示条件）；When2Call 完成 3,652 个输入；BFCL 完成 10,938 个请求（含重复、工具顺序和 schema 实验）。保存结果均为有效响应。

其他模型成绩来自原论文或官方榜单，没有重新调用。BFCL 测量行动／弃权及单独的名称选择诊断；完整参数生成、工具执行和 BFCL Overall 均未评测。When2Call 的 Acc-Norm 不列入比较，300 题 Judge 成绩单独保存在报告中。

## 数据、复查与来源

- [MetaTool 完整报告](reports/metatool.zh-CN.md)：24 个 CSR 条件、8 个论文模型及多工具结果分布。
- [When2Call 完整报告](reports/when2call.zh-CN.md)：混淆矩阵、普通准确率复算、Judge 参考及真实幻觉案例。
- [BFCL 完整报告](reports/bfcl.zh-CN.md)：三次结果、完整榜单决策分项和适配边界。
- [长表 CSV](results.csv)：统一整理三项 benchmark 的全部已收录指标；保留条件、协议、来源和缺失值。
- [来源与文件哈希](data/manifest.json)、[引用及数据说明](SOURCES.md)。公开包提供统计、来源摘录、逐题计分和一个 When2Call 原始交互案例；完整评测程序与其余 API 交互属于原实验归档。

Python 3.10+，仅使用标准库。在仓库根目录运行：

```bash
python3 scripts/build_tables.py --check
python3 scripts/build_tables.py
```

第一条命令核验来源哈希、数值、报告一致性和文件链接；第二条从保存数据重建中英文首页、详细报告和长表 CSV。两条命令均离线运行，不调用模型 API。报告模板位于 `templates/`。
"""
    return f"""# JEV Decision Benchmarks

We use these three benchmarks to evaluate whether JEV selects the right tools, knows when to call or abstain, and avoids choosing tool calls when no tools are available.

English | [简体中文](README.zh-CN.md)

## MetaTool

MetaTool tests whether a model selects the right tool or combination of tools for a user's request and abstains when no suitable tool is available.

{tables[0]}

CSR measures exact tool-set selection. JEV uses a Choice adapter; paper baselines generate tool names followed by answer extraction. The public similar-tool and abstention sets each contain 995 examples, versus 975 each in the paper; each multi-tool condition has 497 examples. [Paper v6, Tables 3–4]({META_PAPER}) · [Full results and protocol (中文)](reports/metatool.zh-CN.md) · [CSV](data/metatool/comparison.csv)

## When2Call

When2Call tests whether a model chooses the right next step: answer directly, call a tool, ask for missing information, or say it cannot complete the request. It also measures how often the model chooses a tool call when no tools are available.

{tables[1]}

All 3,652 test examples. JEV reads four candidates together and selects one; official MCQ scores candidate continuation likelihoods separately. Ordinary accuracy is reliably recoverable from paper matrices for only six official models; `—` means unavailable. F1 uses a 0–100 scale and four fixed classes, with a maximum of 75 on this dataset. Hallucination measures the 258 no-tool examples requiring `cannot_answer`; JEV selects `tool_call` on 197. [Official MCQ]({WHEN_REPO}) · [Report and real error example (中文)](reports/when2call.zh-CN.md) · [CSV](data/when2call/comparison.csv)

## BFCL V4

This table uses BFCL's action/abstention tasks to test whether a model calls a tool when it should and refrains when no tool is suitable or required information is missing.

{tables[2]}

These are the 13 requested official model configurations; all 109 model/mode records appear in the [full report (中文)](reports/bfcl.zh-CN.md) and [CSV](data/bfcl/comparison.csv). Baselines use FC mode, retaining GLM's thinking tag. JEV uses a binary adapter and the mean of three runs. Irrelevance equally weights the 240- and 884-example subset accuracies; Relevance has 16 examples, with 14 correct in every JEV run. Retrieved **2026-09-19**; the page states last updated **2026-04-12**. [Official leaderboard]({BFCL_BOARD})

## Reading the tables

**Bold marks the best displayed-table value per metric and its model; all exact ties are marked.** A bold model name means it leads at least one column, not every column or an overall score. ↑ Higher is better; ↓ lower is better. Comparisons use saved source precision; display values have two decimal places. Missing values do not compete.

These are descriptive comparisons between published scores and JEV adapter experiments. Differences in inputs, outputs, samples, or repetitions described below each table prevent strict same-protocol rankings or significance claims. BFCL highlighting applies only to the displayed selection. No aggregate score combines the three benchmarks.

## Evaluation record

The actual JEV version is `{MODEL}`, evaluated on {DATE}. MetaTool completed 8,574 inputs (different prompt conditions over 4,287 source records); When2Call completed 3,652 inputs; BFCL completed 10,938 requests, including repeats, tool-order variations, and schema ablation. All saved evaluation responses are valid.

Baseline numbers come from the original papers or official leaderboard; other models were not rerun. BFCL covers action/abstention and separate name-only selection diagnostics; full argument generation, tool execution, and BFCL Overall were not evaluated. When2Call Acc-Norm is excluded, and the 300-example Judge route is kept separate in the detailed report.

## Data, verification, and sources

- [MetaTool report (中文)](reports/metatool.zh-CN.md): all 24 CSR conditions, eight paper baselines, and multi-tool outcome distributions.
- [When2Call report (中文)](reports/when2call.zh-CN.md): confusion matrix, derived ordinary accuracies, separate Judge references, and a verified hallucination example.
- [BFCL report (中文)](reports/bfcl.zh-CN.md): individual repetitions, all published decision scores, and adapter limitations.
- [Long-form CSV](results.csv): all included metrics across the three benchmarks, with conditions, protocols, sources, and explicit missing values.
- [Source hashes](data/manifest.json) and [source notes](SOURCES.md). This package includes statistics, source excerpts, per-example scores, and one original When2Call interaction. Full evaluation programs and the remaining API interactions belong to the original experiment archive.

Python 3.10+, standard library only. From the repository root:

```bash
python3 scripts/build_tables.py --check
python3 scripts/build_tables.py
```

The first command checks source hashes, numerical derivations, report consistency, and local links. The second rebuilds both READMEs, detailed reports, and the long-form CSV from saved data. Both run offline without model API calls. Narrative templates are in `templates/`.
"""


def meta_report(meta):
    narrative = (ROOT / "templates/metatool-narrative.zh-CN.md").read_text()
    models = list(meta[0])[7:]
    sections = [narrative.rstrip(), "\n## 8. 全部模型对照\n",
                "数字均为百分比；加粗为该表该列最优及对应模型名，不代表同协议官方排名。",
                "\n### 主要任务\n", homepage_tables(meta, read_csv("data/when2call/comparison.csv"),
                                                       read_csv("data/bfcl/comparison.csv"), True)[0]]
    names = {"Finance Staff": "财务", "Housewife": "家庭管理", "Software Engineer": "软件工程",
             "Students": "学生", "artists&designers": "艺术与设计", "elders": "老年人",
             "TopTool_top5": "Top 5", "TopTool_top10": "Top 10", "TopTool_top15": "Top 15"}
    for shot in ["0", "5"]:
        selected = [r for r in meta if r["subtask"] == "2" and r["shots"] == shot]
        rows = [(m, [r[m] for r in selected]) for m in models]
        sections.extend([f"\n### 场景选择 CSR：{shot}-shot\n",
                         format_table("模型", rows, [(names[r["scenario"]] + " ↑", "up", True) for r in selected])])
    selected = [r for r in meta if r["subtask"] == "4" and r["policy"] == "at_most_two"]
    sections.extend(["\n### 多工具结果分布：最多两个\n",
                     "后两列是失败类型，不按越高越好解释；三类不覆盖全部结果。",
                     format_table("模型", [(m, [r[m] for r in selected]) for m in models],
                                  [("两个都对（CSR）", "up", True), ("只选一个且正确", "up", True),
                                   ("选两个，仅一个正确", "up", True)], highlight=False)])
    return "\n".join(sections) + "\n"


def when_report(when):
    summary = read_json("data/when2call/summary.json")
    primary = summary["primary"]
    lines = ["# JEV 在 When2Call 上的评测与公开模型对照\n",
             f"日期：{DATE}。实际模型：`{MODEL}`。3,652 个请求全部有效，零重试。",
             "\n## 1. 主结果与计分\n",
             "普通准确率为 **2733/3652 = 74.84%**，固定四类 Macro F1 为 **56.55**，工具幻觉率为 **197/258 = 76.36%**。",
             "JEV 同时看到原始四个答案候选，通过 Choice 选择一个；官方 MCQ 分别计算候选续写似然。双方使用相同 3,652 题及类别计分，但推理协议不同。这是有适配差异的任务对照，不能据此宣称严格同协议领先。",
             "Macro F1 对 direct、tool_call、request_for_info、cannot_answer 四类等权平均。direct 没有正样本且零分母计零，因此满分上限为 75（0–100 标度）。工具幻觉率分母仅为 `tools=[]` 且 gold 为 cannot_answer 的题目；分子为其中预测 tool_call 的数量。",
             "\n## 2. 官方 MCQ 全部模型\n",
             homepage_tables(read_csv("data/metatool/comparison.csv"), when, read_csv("data/bfcl/comparison.csv"), True)[1],
             "\n加粗仅表示本列数值最优及对应模型名。MNM 为 Mistral-NeMo-Minitron；dataset-SFT/RPO 表示使用 When2Call 训练。JEV 是否见过公开测试数据未知。",
             f"\nF1 和幻觉率来自[固定官方 README]({WHEN_REPO})；普通准确率来自[论文 Table 14–19]({WHEN_PAPER}#page=18) 的混淆矩阵复算，均通过总数 3,652、类别支持数及已发表 F1 一致性检查。Acc-Norm 不纳入结果。",
             "论文 Table 13 标为 Llama 3.1 70B，但矩阵总数为 3,649、复算 F1 为 17.58，与公布的 37.8 不符。因此该模型普通准确率留空；缺失值不以 Acc-Norm 或其他模型分数填补。",
             "\n### 普通准确率的独立复算\n", "| 模型 | 正确数 / 总数 | 普通准确率 |", "|---|---:|---:|"]
    for row in when[:-1]:
        if row["accuracy_pct"]:
            lines.append(f"| {row['model']} | {row['correct']} / {row['n']} | {float(row['accuracy_pct']):.2f}% |")
    lines.extend(["\n详见[矩阵与复算记录](../data/when2call/derived_checks.json)。", "\n## 3. 混淆矩阵\n",
                  "行是真实类别，列是预测类别。", "\n| 真实 / 预测 | direct | tool_call | request_for_info | cannot_answer |",
                  "|---|---:|---:|---:|---:|"])
    for name, row in zip(summary["label_order"], primary["confusion_matrix"]):
        lines.append("| " + " | ".join([name] + list(map(str, row))) + " |")
    lines.extend(["\n" + (ROOT / "templates/when2call-case.zh-CN.md").read_text(),
                  "\n## 4. 官方 Judge：单独参考\n",
                  "这条路线在 300 题子集上自由生成回答，再由 GPT-4-Turbo-04-09 判别，样本规模、输出形式和评分过程均不同。此表保留论文公布的 F1，不把它重命名为本实验固定四类 Macro F1，也不将 JEV Choice 成绩放入该表。",
                  "\n| 模型 | 论文 Acc ↑ | 论文 F1 ↑ | 工具幻觉率 ↓ | 论文表 |", "|---|---:|---:|---:|---:|"])
    for row in read_csv("data/when2call/judge.csv"):
        values = [f"{float(row[k]):.2f}" + ("%" if k != "f1_published_0_100" else "") if row[k] else "—"
                  for k in ["accuracy_pct", "f1_published_0_100", "tool_hallucination_pct"]]
        lines.append("| " + " | ".join([row["model"]] + values + [row["table"]]) + " |")
    lines.extend([f"\n来源：[论文 Table 4、5]({WHEN_PAPER}#page=7)。",
                  "\n## 5. 来源与复查\n",
                  "[统计 JSON](../data/when2call/summary.json) · [逐题计分](../data/when2call/per_example.csv) · [MCQ CSV](../data/when2call/comparison.csv) · [Judge CSV](../data/when2call/judge.csv) · [来源哈希](../data/manifest.json)",
                  "先前检索到的第三方新模型资料存在未公开数值、仅 15 题示例、格式回退或改变三类计分等问题，没有作为同口径主表成绩。基线均为已发表数字，未重测其他模型。",
                  "在仓库根目录运行 `python3 scripts/build_tables.py --check` 可离线复算准确率、四类 F1、幻觉率及六个论文矩阵，并核验案例选择和原始候选映射。"])
    return "\n\n".join(line.strip("\n") for line in lines if line).replace("|\n\n|", "|\n|") + "\n"


def bfcl_report(bfcl):
    summary = read_json("data/bfcl/summary.json")
    lines = ["# JEV 与 BFCL V4 行动／弃权分项对照\n",
             f"实际模型：`{MODEL}`。推理日期：{DATE}。官方榜单读取于 2026-09-19，页面标注最后更新为 2026-04-12。",
             f"\n## 1. 版本与协议\n\n固定官方 commit 为 `f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`，evaluator 版本为 `2025.12.17`。[源码]({BFCL_REPO})。读取时官方页面声明的版本一致。",
             "JEV 读取原对话与完整工具列表，回答是否应调用至少一个工具；`p_call ≥ 0.5` 为行动，其他为弃权，再映射到官方二元判分结构。没有生成或执行真实函数。",
             "官方模型通过各自 handler 解码实际调用，输出负担、提示、失败处理和重复次数与 JEV 二元适配不同。官方解码失败可能被视为弃权，JEV 无效响应不获得正确弃权奖励。因此不能将适配成绩称为同协议官方成绩。",
             "\n## 2. 三次主实验\n",
             "| 重复 | irrelevance | live_irrelevance | 两子集等权 Irrelevance | Relevance |",
             "|---|---:|---:|---:|---:|"]
    for i in [1, 2, 3]:
        subsets = summary["primary"][f"primary_{i}"]["subsets"]
        a, b = subsets["irrelevance"], subsets["live_irrelevance"]
        value = mean([a["correct"] / a["expected"], b["correct"] / b["expected"]]) * 100
        lines.append(f"| {i} | {a['correct']}/240 | {b['correct']}/884 | {value:.4f}% | 14/16 = 87.50% |")
    irr = summary["repeated_metrics"]["Irrelevance/accuracy"]
    lines.extend([f"\nIrrelevance 三次均值为 **{irr['mean'] * 100:.2f}%**，样本标准差为 **{irr['sample_sd'] * 100:.4f} 个百分点**。Relevance 三次均为 **87.50%**。重复不增加独立样本数，也没有集成预测。",
                  "两列必须联合解释：始终弃权可得到 100% Irrelevance、0% Relevance。Relevance 只有 16 题，一题相当于 6.25 个百分点，不宜根据细小差距声称显著领先。",
                  "\n## 3. 全部官方模型／模式\n",
                  "共 109 条官方记录，加 1 行 JEV。JEV 在第一行，官方模型保留 CSV 原顺序。FC、Prompt 和 thinking 标签保留，未将同名不同模式合并。这里的加粗按完整表格每列最优标记；首页按指定的 13 个官方配置标记，范围不同。"])
    rows = [("JEV 1.13（二元适配；三次均值）" if i == 0 else r["model_and_mode"],
             [r["irrelevance_detection_percent"], r["relevance_detection_percent"]]) for i, r in enumerate(bfcl)]
    lines.append(format_table("模型 / 模式", rows, [("Irrelevance ↑", "up", True), ("Relevance ↑", "up", True)]))
    lines.extend(["\n## 4. 单独诊断：工具名称选择\n",
                  "原实验还评测了 Choice 工具名称选择，通过名称投影使用官方 checker。这些指标只看函数名称，不能作为完整 AST Accuracy 或 BFCL Overall。",
                  "\n| 条件 | Multiple（200 题） | Live Multiple（1,053 题） |", "|---|---:|---:|"])
    for key, name in [("primary_1", "主实验 1"), ("primary_2", "主实验 2"), ("primary_3", "主实验 3"),
                      ("order_20260919", "顺序种子 20260919"), ("order_20260920", "顺序种子 20260920"),
                      ("no_parameters", "删除参数 schema")]:
        subsets = summary["primary"][key]["subsets"]
        lines.append(f"| {name} | {subsets['multiple']['accuracy_all_expected'] * 100:.2f}% | {subsets['live_multiple']['accuracy_all_expected'] * 100:.2f}% |")
    lines.extend(["\n名称选择三次均值分别为 100.00% 和 98.70%；Full AST 与 BFCL Overall 均未评测。完整保存统计还包含校准、重复性与鲁棒性结果。",
                  "\n## 5. 证据与复查\n",
                  f"[官网]({BFCL_BOARD}) · [官方 CSV](https://gorilla.cs.berkeley.edu/data_overall.csv) · [保存的官方 CSV](../data/bfcl/official_leaderboard.csv) · [对照 CSV](../data/bfcl/comparison.csv) · [JEV 统计](../data/bfcl/summary.json) · [榜单版本记录](../data/bfcl/leaderboard_metadata.json) · [来源哈希](../data/manifest.json)",
                  "基线直接引用官方发布值，未重跑其他模型，也未重新评分其逐题输出。读取日期不代表每个官方模型的推理日期。没有跨模型逐题配对结果，不能据此进行配对显著性检验。",
                  "本仓库验证脚本将全部 109 条决策分项与保存的官方 CSV 逐项核对，并从 JEV 三次正确数复算等权均值。"])
    return "\n\n".join(line.strip("\n") for line in lines if line).replace("|\n\n|", "|\n|") + "\n"


def long_csv(meta, when, bfcl):
    stream = io.StringIO(newline="")
    fields = ["benchmark", "condition", "model", "protocol", "metric", "value", "unit", "direction", "n", "source"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in meta:
        condition = ";".join(f"{k}={row[k]}" for k in ("subtask", "shots", "policy", "scenario"))
        for model in list(meta[0])[7:]:
            writer.writerow(dict(benchmark="MetaTool", condition=condition, model=MODEL if model == "JEV" else model,
                                 protocol="jev_choice" if model == "JEV" else "paper_generation_and_extraction",
                                 metric=row["metric"], value=row[model], unit="percent",
                                 direction="up" if row["metric"] == "csr" else "descriptive",
                                 n=row["jev_n"] if model == "JEV" else "",
                                 source="data/metatool/summary.json" if model == "JEV" else META_PAPER + " (Table " + row["paper_table"] + ")"))
    for row in when:
        for field, unit, direction in [("accuracy_pct", "percent", "up"), ("macro_f1_0_100", "score_0_100", "up"),
                                       ("tool_hallucination_pct", "percent", "down")]:
            writer.writerow(dict(benchmark="When2Call", condition="full_test", model=row["model"], protocol=row["protocol"],
                                 metric=field, value=row[field], unit=unit, direction=direction,
                                 n="258" if field == "tool_hallucination_pct" else row["n"],
                                 source=row["accuracy_source"] if field == "accuracy_pct" else row["score_source"]))
    for row in read_csv("data/when2call/judge.csv"):
        for field, unit, direction in [("accuracy_pct", "percent", "up"), ("f1_published_0_100", "score_0_100", "up"),
                                       ("tool_hallucination_pct", "percent", "down")]:
            writer.writerow(dict(benchmark="When2Call", condition="judge_300_subset", model=row["model"], protocol=row["protocol"],
                                 metric=field, value=row[field], unit=unit, direction=direction,
                                 n="" if field == "tool_hallucination_pct" else row["n_nominal"], source=row["source"]))
    for row in bfcl:
        for field, condition, n in [("irrelevance_detection_percent", "equal_weight_irrelevance_240_and_live_irrelevance_884", "1124"),
                                    ("relevance_detection_percent", "live_relevance", "16")]:
            writer.writerow(dict(benchmark="BFCL V4", condition=condition, model=row["model_and_mode"],
                                 protocol="jev_binary_3_run_mean" if row["source"] == "local_adapted" else "official_output_decoding",
                                 metric=field, value=row[field], unit="percent", direction="up", n=n,
                                 source="data/bfcl/summary.json" if row["source"] == "local_adapted" else row["source_url"]))
    return stream.getvalue().replace("runs/v1/summary.json", "data/when2call/summary.json")


def check_links_and_content():
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        # Templates' links intentionally resolve relative to their output directory.
        parent = ROOT / "reports" if path.parent.name == "templates" else path.parent
        content = path.read_text()
        require("/home/" not in content and "/root/" not in content, f"Local path: {path.relative_to(ROOT)}")
        for target in re.findall(r"\]\(([^\s)]+)\)", content):
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            require((parent / relative).exists(), f"Broken link in {path.relative_to(ROOT)}: {target}")
    for name in ["README.md", "README.zh-CN.md"]:
        content = (ROOT / name).read_text()
        require(content.count("\n|---|") == 3, f"Homepage must have exactly 3 tables: {name}")
        headings = re.findall(r"^## (.+)$", content, re.M)
        require(headings[:3] == ["MetaTool", "When2Call", "BFCL V4"], "Homepage benchmark order")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without rewriting files")
    args = parser.parse_args()
    meta, when, bfcl = verify_sources()
    outputs = {"README.md": readme(meta, when, bfcl, False),
               "README.zh-CN.md": readme(meta, when, bfcl, True),
               "reports/metatool.zh-CN.md": meta_report(meta),
               "reports/when2call.zh-CN.md": when_report(when),
               "reports/bfcl.zh-CN.md": bfcl_report(bfcl),
               "results.csv": long_csv(meta, when, bfcl)}
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.check:
            require(path.exists() and path.read_text() == content, f"Generated output out of date: {relative}")
        else:
            path.write_text(content)
    check_links_and_content()
    print(json.dumps({"status": "passed", "source_hashes": 19, "homepages": 2,
                      "homepage_model_rows": [9, 22, 14], "official_bfcl_rows": 109,
                      "when2call_recomputed_examples": 3652, "mode": "check" if args.check else "build"}))


if __name__ == "__main__":
    main()
