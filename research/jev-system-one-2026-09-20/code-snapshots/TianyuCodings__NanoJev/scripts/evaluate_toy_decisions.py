#!/usr/bin/env python3
"""评估 toy 决策分布；仅 calibration 拟合温度，标准库实现，无模型调用。"""
import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


LOG_FLOOR = 1e-15
TYPES = {"boolean", "choice", "score"}
SPLITS = {"train", "dev", "calibration", "test", "ood"}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def softmax(logits, temperature=1.0):
    if not number(temperature) or temperature <= 0:
        raise ValueError("temperature 必须是有限正数")
    maximum = max(logits)
    exps = [math.exp((value - maximum) / temperature) for value in logits]
    total = math.fsum(exps)
    return [value / total for value in exps]


def distribution(values, k, tolerance=1e-6):
    if not isinstance(values, list) or len(values) != k:
        raise ValueError("distribution_length_mismatch")
    if not all(number(value) and 0 <= value <= 1 for value in values):
        raise ValueError("invalid_probability_value")
    total = math.fsum(values)
    if total <= 0:
        raise ValueError("zero_mass_not_a_point_distribution")
    if abs(total - 1) > tolerance:
        raise ValueError("probability_sum_not_one")
    # 这里只修正容限内的浮点总和，不重建低精度缺失的概率质量。
    return [value / total for value in values]


def extract_logits(row, k):
    value = next((row[key] for key in ("student_logits", "logits", "logit") if key in row), None)
    if value is None:
        return None
    if number(value) and row["type"] == "boolean" and k == 2:
        value = [0.0, float(value)]  # scalar 必须表示 log(p_true/p_false)。
    if not isinstance(value, list) or len(value) != k or not all(number(x) for x in value):
        raise ValueError("logits 长度或数值无效")
    return [float(x) for x in value]


def validate_predictions(records):
    validated, seen = [], set()
    required = {"id", "state_id", "family_id", "split", "qid", "type", "candidate_ids", "gold_index", "student_probs"}
    for line_number, original in enumerate(records, 1):
        if not isinstance(original, dict) or required - set(original):
            raise ValueError(f"第 {line_number} 行缺少必要预测字段")
        row = dict(original)
        if row["type"] not in TYPES or row["split"] not in SPLITS:
            raise ValueError(f"第 {line_number} 行题型或 split 无效")
        for key in ("id", "state_id", "family_id", "qid"):
            if not isinstance(row[key], str) or not row[key]:
                raise ValueError(f"第 {line_number} 行 {key} 必须是非空字符串")
        ids = row["candidate_ids"]
        if not isinstance(ids, list) or len(ids) < 2 or not all(isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"第 {line_number} 行 candidate_ids 无效")
        k = len(ids)
        if type(row["gold_index"]) is not int or not 0 <= row["gold_index"] < k:
            raise ValueError(f"第 {line_number} 行 gold_index 超出范围")
        if row["type"] == "boolean" and ids != ["false", "true"]:
            raise ValueError("Boolean candidate_ids 必须为 ['false','true']")
        if row["type"] == "score":
            try:
                ordinal = [int(x) for x in ids]
            except ValueError as exc:
                raise ValueError("Score candidate_ids 必须表示等级序号") from exc
            if sorted(ordinal) != list(range(k)):
                raise ValueError("Score 序号必须恰好覆盖 0..K-1")
            row["_ordinal"] = ordinal
        key = (row["split"], row["id"], row["qid"])
        if key in seen:
            raise ValueError(f"重复预测: {key}")
        seen.add(key)
        row["_student_probs"] = distribution(row["student_probs"], k)
        row["_logits"] = extract_logits(row, k)
        if row["_logits"] is not None:
            derived = softmax(row["_logits"])
            if max(abs(a - b) for a, b in zip(derived, row["_student_probs"])) > 1e-4:
                raise ValueError(f"第 {line_number} 行 raw logits 与 student_probs 不对应")
        row["_teacher_probs"] = None
        row["_teacher_status"] = "missing"
        if original.get("teacher_probs") is not None:
            try:
                row["_teacher_probs"] = distribution(original["teacher_probs"], k)
                row["_teacher_status"] = original.get("teacher_target_kind", "provided_normalized_target_precision_unspecified")
            except ValueError as exc:
                row["_teacher_status"] = str(exc)
        elif original.get("teacher_raw_probs") is not None:
            try:
                row["_teacher_probs"] = distribution(original["teacher_raw_probs"], k, tolerance=1e-12)
                row["_teacher_status"] = "raw_probabilities_as_proxy"
            except ValueError as exc:
                row["_teacher_status"] = str(exc)
        validated.append(row)
    if not validated:
        raise ValueError("预测文件为空")
    return validated


def mean(values):
    return math.fsum(values) / len(values) if values else None


def nll(probability):
    return -math.log(max(probability, LOG_FLOOR))


def gold_metrics(rows, probability_key="_student_probs", bins=10, include_bins=True):
    rows = [row for row in rows if row.get(probability_key) is not None]
    if not rows:
        return {"questions": 0, "states": 0}
    hits, losses, briers, absolute_errors, normalized_errors = [], [], [], [], []
    bucket = [{"count": 0, "confidence_sum": 0.0, "correct_sum": 0.0} for _ in range(bins)]
    zero_gold = 0
    for row in rows:
        p = row[probability_key]
        y = row["gold_index"]
        prediction = max(range(len(p)), key=p.__getitem__)
        correct = int(prediction == y)
        confidence = p[prediction]
        hits.append(correct)
        losses.append(nll(p[y]))
        zero_gold += int(p[y] == 0)
        briers.append(math.fsum((value - int(i == y)) ** 2 for i, value in enumerate(p)))
        b = bucket[min(bins - 1, int(confidence * bins))]  # p=1 位于最后一箱。
        b["count"] += 1
        b["confidence_sum"] += confidence
        b["correct_sum"] += correct
        if row["type"] == "score":
            values = row["_ordinal"]
            estimate = math.fsum(value * probability for value, probability in zip(values, p))
            error = abs(estimate - values[y])
            absolute_errors.append(error)
            normalized_errors.append(error / (len(p) - 1))
    reliability, ece = [], 0.0
    for i, b in enumerate(bucket):
        count = b["count"]
        confidence = b["confidence_sum"] / count if count else None
        accuracy = b["correct_sum"] / count if count else None
        if count:
            ece += count / len(rows) * abs(confidence - accuracy)
        reliability.append({"lower": i / bins, "upper": (i + 1) / bins,
                            "upper_inclusive": i == bins - 1, "count": count,
                            "mean_confidence": confidence, "accuracy": accuracy})
    result = {"questions": len(rows), "states": len({row["state_id"] for row in rows}),
              "accuracy": mean(hits), "nll": mean(losses), "brier": mean(briers), "ece": ece,
              "zero_gold_probability_count": zero_gold, "score_questions": len(absolute_errors),
              "score_mae": mean(absolute_errors), "score_normalized_mae": mean(normalized_errors)}
    if include_bins:
        result["reliability_bins"] = reliability
    return result


def fidelity_metrics(rows):
    pairs = [row for row in rows if row.get("_teacher_probs") is not None]
    if not pairs:
        return {"questions": 0}
    tv, kl, soft_ce, agreements = [], [], [], []
    for row in pairs:
        t, p = row["_teacher_probs"], row["_student_probs"]
        ce = -math.fsum(a * math.log(max(b, LOG_FLOOR)) for a, b in zip(t, p) if a > 0)
        entropy = -math.fsum(a * math.log(a) for a in t if a > 0)
        soft_ce.append(ce)
        kl.append(max(0.0, ce - entropy))  # 仅消除显示指标的浮点级负零。
        tv.append(0.5 * math.fsum(abs(a - b) for a, b in zip(t, p)))
        agreements.append(int(max(range(len(t)), key=t.__getitem__) == max(range(len(p)), key=p.__getitem__)))
    return {"questions": len(pairs), "tv": mean(tv), "forward_kl_teacher_student": mean(kl),
            "soft_cross_entropy": mean(soft_ce), "argmax_agreement": mean(agreements),
            "target_status_counts": dict(Counter(row["_teacher_status"] for row in pairs))}


def breakdown(rows, probability_key="_student_probs"):
    result = {"overall": gold_metrics(rows, probability_key), "by_type": {}, "by_family": {}}
    for field, label in (("type", "by_type"), ("family_id", "by_family")):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row[field]].append(row)
        result[label] = {key: gold_metrics(value, probability_key) for key, value in sorted(grouped.items())}
    return result


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(math.floor(position))
    high = int(math.ceil(position))
    return values[low] + (values[high] - values[low]) * (position - low)


def cluster_bootstrap(rows, probability_key="_student_probs", samples=500, seed=17):
    clusters = defaultdict(list)
    for row in rows:
        if row.get(probability_key) is not None:
            clusters[row["state_id"]].append(row)
    groups = list(clusters.values())
    if samples <= 0 or len(groups) < 2:
        return {"samples": samples, "clusters": len(groups), "status": "insufficient_clusters_or_disabled"}
    rng = random.Random(seed)
    collected = defaultdict(list)
    for _ in range(samples):
        draw = [row for _ in groups for row in rng.choice(groups)]
        metrics = gold_metrics(draw, probability_key, include_bins=False)
        for key in ("accuracy", "nll", "brier", "ece", "score_mae", "score_normalized_mae"):
            if metrics.get(key) is not None:
                collected[key].append(metrics[key])
    return {"samples": samples, "clusters": len(groups), "unit": "state_id", "confidence_level": 0.95,
            "intervals": {key: [percentile(values, 0.025), percentile(values, 0.975)]
                          for key, values in collected.items()}}


def fit_temperature(rows):
    # 本函数不查看 dev/test/ood 的标签来选择温度。
    calibration = [row for row in rows if row["split"] == "calibration"]
    if not calibration:
        return {"status": "unavailable_no_calibration_rows", "temperature": None, "questions": 0}
    if any(row.get("_logits") is None for row in calibration):
        return {"status": "unavailable_missing_calibration_logits", "temperature": None,
                "questions": len(calibration)}
    temperatures = [math.exp(math.log(0.25) + i / 80 * math.log(16)) for i in range(81)]
    temperatures[40] = 1.0
    objectives = []
    for temperature in temperatures:
        losses = [nll(softmax(row["_logits"], temperature)[row["gold_index"]]) for row in calibration]
        objectives.append(mean(losses))
    # 同损失优先选离1更近的温度，避免平坦目标任意落到边界。
    best = min(range(len(temperatures)), key=lambda i: (objectives[i], abs(math.log(temperatures[i]))))
    return {"status": "fitted_on_calibration_only", "temperature": temperatures[best],
            "questions": len(calibration), "states": len({r["state_id"] for r in calibration}),
            "method": "shared_scalar_logspace_grid", "grid_min": 0.25, "grid_max": 4.0,
            "grid_points": 81, "at_grid_boundary": best in (0, 80),
            "raw_calibration_nll": objectives[40], "fitted_calibration_nll": objectives[best]}


def evaluate_records(records, bootstrap_samples=500, seed=17):
    rows = validate_predictions(records)
    by_split = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)
    raw = {}
    for split, group in sorted(by_split.items()):
        paired = [row for row in group if row["_teacher_probs"] is not None]
        raw[split] = {
            "student_gold": breakdown(group),
            "teacher_gold": breakdown(paired, "_teacher_probs"),
            "student_gold_on_teacher_subset": gold_metrics(paired),
            "teacher_fidelity_raw": fidelity_metrics(group),
            "teacher_target_status_counts": dict(Counter(row["_teacher_status"] for row in group)),
        }
        if split in ("test", "ood"):
            raw[split]["student_state_cluster_ci"] = cluster_bootstrap(group, samples=bootstrap_samples, seed=seed)
            raw[split]["teacher_state_cluster_ci"] = cluster_bootstrap(paired, "_teacher_probs", bootstrap_samples, seed)
    calibration = fit_temperature(rows)
    calibrated = {}
    if calibration["temperature"] is not None:
        for split in ("test", "ood"):
            group = by_split.get(split, [])
            if not group:
                continue
            if any(row["_logits"] is None for row in group):
                calibrated[split] = {"status": "unavailable_missing_evaluation_logits"}
                continue
            for row in group:
                row["_calibrated_probs"] = softmax(row["_logits"], calibration["temperature"])
            calibrated[split] = {
                "student_gold": breakdown(group, "_calibrated_probs"),
                "student_state_cluster_ci": cluster_bootstrap(group, "_calibrated_probs", bootstrap_samples, seed),
            }
    return {
        "schema_version": "openjev-toy-metrics-v1", "question_weighting": "equal_per_question",
        "nll_probability_floor": LOG_FLOOR, "brier_definition": "sum_over_candidates",
        "ece_definition": "top_label_equal_width_10_bins_last_includes_1",
        "raw": raw, "calibration": calibration, "calibrated": calibrated,
        "limits": ["自写合成 toy、少量状态，只检验算法通路，不能证明现实校准或一般泛化。",
                   "bootstrap 按 state 聚类，但不能消除共享规则/模板导致的所有相关性。",
                   "仅 calibration 标签选择温度；本评估器不选择模型 checkpoint。",
                   "概率为0时NLL使用已报告的数值下界，另报零真值概率次数。",
                   "teacher fidelity 仅比较供应的合格目标，不声称恢复舍入前真实概率。"],
    }


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 重复键: {key}")
        result[key] = value
    return result


def load_predictions(path):
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for number_, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line, object_pairs_hook=reject_duplicate_keys))
                except (ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"第 {number_} 行 JSON 无效: {exc}") from exc
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="包含 calibration/test/ood 等分区的 predictions.jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    if args.bootstrap_samples < 0:
        parser.error("bootstrap-samples 不得为负数")
    try:
        metrics = evaluate_records(load_predictions(args.input), args.bootstrap_samples, args.seed)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = {"output": str(output), "calibration": metrics["calibration"],
               "raw_student": {key: value["student_gold"]["overall"] for key, value in metrics["raw"].items() if key in ("test", "ood")}}
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
