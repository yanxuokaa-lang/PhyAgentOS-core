#!/usr/bin/env python3
"""Summarize frozen event predictions, with policy diagnostics kept separate.

Standard library only. No training, API, model execution, or output-based model
selection. All valid rows, including zero-probability errors, enter the means.
An invalid or missing file makes the report incomplete; it is never silently
filtered into a favorable subset. Run --self-check for small exact fixtures.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path


DEFAULT_EVENT_RUNS = ["events_ce_seed17", "events_brier_seed17", "events_paired_seed17"]
EVENT_KINDS = ("programmatic_conditional_distribution", "observed_outcome")
EPSILON = 1e-12
SUM_TOLERANCE = 1e-5


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Nonfinite JSON constant: {value}")


def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def vector(value, candidate_ids, name):
    if isinstance(value, dict):
        if set(value) != set(candidate_ids):
            raise ValueError(f"{name}: candidate IDs differ")
        value = [value[key] for key in candidate_ids]
    if not isinstance(value, list) or len(value) != len(candidate_ids):
        raise ValueError(f"{name}: one probability for every offered candidate is required")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > 1 for v in value):
        raise ValueError(f"{name}: probabilities must be finite numbers in [0,1]")
    total = math.fsum(value)
    if total <= 0 or abs(total - 1) > SUM_TOLERANCE:
        raise ValueError(f"{name}: sum {total!r} exceeds floating-point normalization tolerance")
    return [float(v) / total for v in value], total


def checked_row(row, expected_split, mode):
    for key in ("id", "state_id", "qid", "family_id", "split", "type"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(f"Missing nonempty string: {key}")
    if row["split"] != expected_split:
        raise ValueError(f"Prediction split {row['split']!r} does not match file split {expected_split!r}")
    if row["type"] not in {"boolean", "choice", "score"}:
        raise ValueError("Unknown question type")
    ids = row.get("candidate_ids")
    if not isinstance(ids, list) or len(ids) < 2 or any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(ids):
        raise ValueError("Expected at least two distinct candidate IDs")
    if row["type"] == "boolean" and (len(ids) != 2 or set(ids) != {"false", "true"}):
        raise ValueError("Boolean questions must offer exactly false and true")
    y = row.get("gold_index")
    if type(y) is not int or not 0 <= y < len(ids):
        raise ValueError("gold_index must name an offered candidate")
    p, p_sum = vector(row.get("student_probs"), ids, "student_probs")
    raw_q = row.get("gold_probs")
    if raw_q is None:
        raise ValueError("Explicit gold_probs is required; a compatibility label is not a probability target")
    q, q_sum = vector(raw_q, ids, "gold_probs")
    if row.get("gold_distribution_probs") is not None:
        other, _ = vector(row["gold_distribution_probs"], ids, "gold_distribution_probs")
        if max(abs(a - b) for a, b in zip(q, other)) > 1e-10:
            raise ValueError("gold_probs and gold_distribution_probs disagree")
    kind = row.get("gold_probs_kind")
    label_kind = row.get("gold_label_kind")
    if mode == "event":
        if (kind, label_kind) != EVENT_KINDS:
            raise ValueError("Event metrics require gold_probs_kind=programmatic_conditional_distribution AND gold_label_kind=observed_outcome")
        if q[y] <= 0:
            raise ValueError("Observed outcome is impossible under the declared exact conditional distribution")
        category = "observed_event"
    elif kind == "deterministic_truth" and label_kind == "deterministic_truth":
        if q[y] != 1 or sum(v != 0 for v in q) != 1:
            raise ValueError("Deterministic truth must be one-hot and agree with gold_index")
        category = "deterministic_truth"
    elif kind == "optimal_action_policy" and label_kind == "reference_argmax_compatibility":
        if row["type"] != "choice" or q[y] <= 0:
            raise ValueError("Optimal-action policy requires a Choice and a representative in its support")
        category = "optimal_action_policy"
    elif kind == "programmatic_conditional_distribution" and label_kind == "reference_argmax_compatibility":
        if row["type"] != "choice" or q[y] <= 0:
            raise ValueError("Compatibility action preference requires a Choice and a representative in its support")
        category = "compatibility_action_preference"
    else:
        raise ValueError(f"Unsupported policy diagnostic semantics: {kind!r}/{label_kind!r}")
    return {**{key: row[key] for key in ("id", "state_id", "qid", "family_id", "split", "type")},
            "candidate_ids": ids, "gold_index": y, "gold_probs_kind": kind, "gold_label_kind": label_kind,
            "category": category, "p": p, "q": q,
            "student_sum_before_float_normalization": p_sum,
            "gold_sum_before_float_normalization": q_sum}


def row_metrics(row, epsilon):
    p, q, y = row["p"], row["q"], row["gold_index"]
    predicted = max(range(len(p)), key=p.__getitem__)
    clipped = [i for i, value in enumerate(p) if value < epsilon]
    result = {key: row[key] for key in ("id", "state_id", "qid", "family_id", "split", "type", "candidate_ids",
                                        "gold_index", "gold_probs_kind", "gold_label_kind", "category",
                                        "student_sum_before_float_normalization", "gold_sum_before_float_normalization")}
    result.update(student_probs=row["p"], gold_probs=row["q"],
                  log_floor_candidate_count=len(clipped),
                  zero_probability_candidate_count=sum(value == 0 for value in p),
                  observed_probability_floored=p[y] < epsilon,
                  positive_q_probability_floored_count=sum(q[i] > 0 for i in clipped))
    if row["category"] in {"observed_event", "deterministic_truth"}:
        result["observed_nll"] = -math.log(max(p[y], epsilon))
        result["observed_vector_brier"] = math.fsum((value - float(i == y)) ** 2 for i, value in enumerate(p))
        result["accuracy"] = float(predicted == y)
    if row["category"] == "observed_event":
        result["known_q_squared_l2"] = math.fsum((a - b) ** 2 for a, b in zip(q, p))
        result["known_q_kl"] = math.fsum(a * (math.log(a) - math.log(max(b, epsilon))) for a, b in zip(q, p) if a > 0)
    if row["category"] in {"optimal_action_policy", "compatibility_action_preference"}:
        # Snake's local heuristic target is not a globally optimal game policy,
        # even when its schema uses the generic optimal_action_policy kind.
        prefix = ("optimal_action" if row["category"] == "optimal_action_policy"
                  and not row["family_id"].startswith("snake") else "reference_action")
        result[prefix + "_mass"] = math.fsum(p[i] for i, value in enumerate(q) if value > 0)
        result[prefix + "_set_hit"] = float(q[predicted] > 0)
        result["target_support_size"] = sum(value > 0 for value in q)
        result["action_support_meaning"] = ("Saved reference-action support; Snake targets are local heuristic preferences, not globally optimal Snake play."
                                            if prefix == "reference_action" else "Saved declared optimal-action support; no new planner or closed-loop result is inferred.")
    return result


def boolean_ece(rows):
    eligible = [row for row in rows if row["type"] == "boolean"]
    bins = [{"lower": i / 10, "upper": (i + 1) / 10, "count": 0,
             "predicted_true_sum": 0.0, "observed_true_count": 0, "known_true_sum": 0.0} for i in range(10)]
    for row in eligible:
        true_index = row["candidate_ids"].index("true")
        p_true = row["student_probs"][true_index]
        slot = bins[min(int(p_true * 10), 9)]
        slot["count"] += 1
        slot["predicted_true_sum"] += p_true
        slot["observed_true_count"] += int(row["gold_index"] == true_index)
        slot["known_true_sum"] += row["gold_probs"][true_index]
    ece = 0.0
    for item in bins:
        n = item["count"]
        item["mean_predicted_p_true"] = item.pop("predicted_true_sum") / n if n else None
        item["observed_true_frequency"] = item["observed_true_count"] / n if n else None
        item["mean_known_p_true"] = item.pop("known_true_sum") / n if n else None
        item["absolute_gap"] = abs(item["mean_predicted_p_true"] - item["observed_true_frequency"]) if n else None
        item["weighted_gap"] = n / len(eligible) * item["absolute_gap"] if n else 0.0
        ece += item["weighted_gap"]
    return {"questions": len(eligible), "value": ece if eligible else None, "bins": bins,
            "definition": "10 fixed equal-width bins of p(true), compared with the observed true frequency; not top-label confidence ECE.",
            "interval_rule": "Lower inclusive, upper exclusive, except the last bin includes 1.",
            "finite_sample_note": "Observed frequencies and ECE depend on finite outcome draws and bin counts; this is not a population calibration guarantee or an independent-map confidence interval."}


def aggregate(rows):
    metrics = ("observed_nll", "observed_vector_brier", "known_q_squared_l2", "known_q_kl", "accuracy",
               "optimal_action_mass", "optimal_action_set_hit", "reference_action_mass", "reference_action_set_hit")
    result = {"questions": len(rows), "states": len({row["state_id"] for row in rows}),
              "by_question_type": dict(Counter(row["type"] for row in rows)), "metrics": {}}
    for metric in metrics:
        values = [row[metric] for row in rows if metric in row]
        if values:
            result["metrics"][metric] = {"questions": len(values), "mean": math.fsum(values) / len(values)}
    result["numeric_audit"] = {
        "rows_with_log_floor": sum(row["log_floor_candidate_count"] > 0 for row in rows),
        "floored_candidate_probabilities": sum(row["log_floor_candidate_count"] for row in rows),
        "zero_candidate_probabilities": sum(row["zero_probability_candidate_count"] for row in rows),
        "floored_observed_outcomes": sum(row["observed_probability_floored"] for row in rows),
        "floored_candidates_with_positive_q": sum(row["positive_q_probability_floored_count"] for row in rows),
        "student_rows_with_exact_nonunit_float_sum": sum(row["student_sum_before_float_normalization"] != 1 for row in rows),
        "gold_rows_with_exact_nonunit_float_sum": sum(row["gold_sum_before_float_normalization"] != 1 for row in rows),
        "maximum_student_absolute_sum_error": max((abs(row["student_sum_before_float_normalization"] - 1) for row in rows), default=None),
    }
    # ECE is deliberately absent from action-preference sections.
    if all(row["category"] in {"observed_event", "deterministic_truth"} for row in rows):
        result["boolean_ece"] = boolean_ece(rows)
    return result


def cohort_signature(rows):
    fields = ("id", "state_id", "qid", "family_id", "split", "type", "candidate_ids", "gold_index", "gold_probs_kind", "gold_label_kind", "q")
    targets = [{key: row[key] for key in fields} for row in rows]
    targets.sort(key=lambda row: (row["state_id"], row["qid"], row["id"]))
    return sha_json(targets)


def summarize_file(path, split, mode, epsilon):
    path = Path(path)
    if not path.is_file():
        return {"status": "missing", "path": str(path)}, []
    raw = path.read_bytes()
    rows, seen = [], set()
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
            row = checked_row(record, split, mode)
            identity = (row["state_id"], row["qid"])
            if identity in seen:
                raise ValueError("Duplicate state_id/qid in prediction file")
            seen.add(identity)
            rows.append(row)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ValueError(f"{path}:{lineno}: {error}") from error
    if not rows:
        raise ValueError(f"{path}: empty prediction file")
    derived = [row_metrics(row, epsilon) for row in rows]
    result = {"status": "complete", "path": str(path), "source_sha256": hashlib.sha256(raw).hexdigest(),
              "cohort_targets_sha256": cohort_signature(rows), "rows": len(rows), "per_row_metrics": derived}
    if mode == "event":
        result["overall"] = aggregate(derived)
        result["by_family"] = {family: aggregate([row for row in derived if row["family_id"] == family])
                               for family in sorted({row["family_id"] for row in derived})}
    else:
        # Do not produce a mixed overall average of truth and policy objectives.
        result["by_semantics"] = {}
        for category in sorted({row["category"] for row in derived}):
            selected = [row for row in derived if row["category"] == category]
            result["by_semantics"][category] = {
                "overall": aggregate(selected),
                "by_family": {family: aggregate([row for row in selected if row["family_id"] == family])
                              for family in sorted({row["family_id"] for row in selected})}}
    return result, rows


def summarize_runs(args):
    definitions = [(name, "event", False) for name in args.event_runs]
    if args.initial_run:
        definitions.append((args.initial_run, "event", True))
    definitions += [(name, "policy", False) for name in args.policy_runs]
    if not definitions:
        raise ValueError("At least one event, initial, or policy run is required")
    report = {"schema_version": "nanojev-scaled-probability-summary-v1", "status": "incomplete", "complete": False,
              "metric_contract": {
                  "weighting": "Arithmetic mean per complete question, with metric-specific counts; all valid rows retained, including zeros and incorrect outcomes.",
                  "event_gate": {"gold_probs_kind": EVENT_KINDS[0], "gold_label_kind": EVENT_KINDS[1]},
                  "log_unit": "nats", "log_epsilon": args.epsilon,
                  "log_floor_rule": "Replace p with max(p,epsilon) only inside logarithms; do not renormalize the floored vector. Zero-q KL terms contribute zero. NLL/KL with active floors are finite clipped diagnostics.",
                  "probability_normalization": f"Reject probability-sum errors greater than {SUM_TOLERANCE}; divide by the original sum within tolerance to correct export roundoff. Record both original sums. Brier, L2, action mass and ECE use these unfloored probabilities.",
                  "brier": "sum_k (p[k]-one_hot(observed_Y)[k])^2; for Boolean this is twice scalar Bernoulli Brier.",
                  "known_q_squared_l2": "sum_k (p[k]-q[k])^2 against the programmatic conditional distribution.",
                  "known_q_kl": "sum_{q[k]>0} q[k]*(log(q[k])-log(max(p[k],epsilon))).",
                  "boolean_ece": "10 fixed bins of positive-class p(true) versus observed true frequency; finite sample, not top-label ECE.",
                  "policy_separation": "Exact truth, declared maze optimal-action support, and reference action preferences are separate. Snake always uses reference_action_mass regardless of its generic target kind. Support mass is not an event-success probability; Snake local preferences are not globally optimal Snake actions.",
                  "tie_rule": "First candidate in the saved order for argmax ties; no reconstruction of an absent action sample.",
                  "selection": "Read-only reporting of the supplied runs; no winner selection or training changes.",
                  "scope": "Prediction artifacts permit target/cohort consistency and state-ID overlap checks, but not an independent training/map leakage audit or verification of simulator correctness.",
              }, "runs": {}, "errors": [], "missing_files": [], "cohort_checks": {}}
    reference_hashes = {}
    seen_names = set()
    for name, mode, initial in definitions:
        directory = Path(name) if Path(name).is_absolute() else args.runs_dir / name
        key = str(name)
        if key in seen_names:
            raise ValueError(f"Duplicate run identifier: {key}")
        seen_names.add(key)
        entry = {"mode": mode, "initial_control": initial, "directory": str(directory), "splits": {}}
        state_ids = {}
        for split in args.splits:
            path = directory / f"predictions_{split}.jsonl"
            try:
                summary, rows = summarize_file(path, split, mode, args.epsilon)
                entry["splits"][split] = summary
                if summary["status"] == "missing":
                    report["missing_files"].append(str(path))
                    continue
                state_ids[split] = {row["state_id"] for row in rows}
                if mode == "event":
                    signature = summary["cohort_targets_sha256"]
                    reference = reference_hashes.setdefault(split, (key, signature))
                    matches = signature == reference[1]
                    report["cohort_checks"].setdefault(split, []).append({"run": key, "reference_run": reference[0], "matches": matches,
                                                                         "cohort_targets_sha256": signature})
                    if not matches:
                        report["errors"].append(f"Event cohort or target mismatch: {key}/{split} vs {reference[0]}/{split}")
            except (ValueError, OSError, UnicodeError) as error:
                entry["splits"][split] = {"status": "invalid", "path": str(path), "error": str(error)}
                report["errors"].append(str(error))
        overlaps = []
        split_names = sorted(state_ids)
        for index, left in enumerate(split_names):
            for right in split_names[index + 1:]:
                overlap = sorted(state_ids[left] & state_ids[right])
                overlaps.append({"left": left, "right": right, "overlapping_state_count": len(overlap), "state_ids": overlap})
                if overlap:
                    report["errors"].append(f"Repeated state IDs across held-out splits: {key}/{left}/{right}")
        entry["heldout_state_overlap"] = overlaps
        report["runs"][key] = entry
    report["complete"] = not report["errors"] and not report["missing_files"]
    report["status"] = "complete" if report["complete"] else "invalid" if report["errors"] else "incomplete"
    report["summarizer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return report


def self_check():
    row = {"id": "s:q", "state_id": "s", "qid": "q", "family_id": "fixture", "split": "test", "type": "boolean",
           "candidate_ids": ["false", "true"], "gold_index": 1, "student_probs": [0.2, 0.8],
           "gold_probs": [0.7, 0.3], "gold_probs_kind": EVENT_KINDS[0], "gold_label_kind": EVENT_KINDS[1]}
    checked = checked_row(row, "test", "event")
    metrics = row_metrics(checked, EPSILON)
    assert abs(metrics["observed_nll"] + math.log(0.8)) < 1e-12
    assert abs(metrics["observed_vector_brier"] - 0.08) < 1e-12
    assert abs(metrics["known_q_squared_l2"] - 0.5) < 1e-12
    assert abs(metrics["known_q_kl"] - (0.7 * math.log(3.5) + 0.3 * math.log(0.375))) < 1e-12
    other = copy.deepcopy(row)
    other.update(id="other:q", state_id="other", student_probs=[0.8, 0.2])
    other_metrics = row_metrics(checked_row(other, "test", "event"), EPSILON)
    assert abs(boolean_ece([metrics, other_metrics])["value"] - 0.5) < 1e-12
    zero = copy.deepcopy(row)
    zero["student_probs"] = [1.0, 0.0]
    zero_metrics = row_metrics(checked_row(zero, "test", "event"), EPSILON)
    assert zero_metrics["observed_probability_floored"] and math.isfinite(zero_metrics["known_q_kl"])
    assert abs(zero_metrics["observed_nll"] + math.log(EPSILON)) < 1e-12
    assert zero_metrics["observed_vector_brier"] == 2
    for changed in [{"gold_label_kind": "reference_argmax_compatibility"}, {"gold_probs_kind": "optimal_action_policy"},
                    {"student_probs": [0.2, 0.9]}, {"student_probs": [-0.1, 1.1]}, {"gold_index": True},
                    {"gold_probs": [1.0, 0.0]}, {"candidate_ids": ["true", "true"]}]:
        candidate = {**row, **changed}
        try:
            checked_row(candidate, "test", "event")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid event fixture accepted: {changed}")
    policy = {**row, "type": "choice", "candidate_ids": ["a", "b", "c"], "gold_index": 0,
              "student_probs": [0.5, 0.3, 0.2], "gold_probs": [0.5, 0.5, 0.0],
              "gold_probs_kind": "optimal_action_policy", "gold_label_kind": "reference_argmax_compatibility"}
    policy_metrics = row_metrics(checked_row(policy, "test", "policy"), EPSILON)
    assert policy_metrics["optimal_action_mass"] == 0.8 and policy_metrics["optimal_action_set_hit"] == 1
    assert "observed_nll" not in policy_metrics and "boolean_ece" not in aggregate([policy_metrics])
    policy["gold_probs_kind"] = "programmatic_conditional_distribution"
    preference = row_metrics(checked_row(policy, "test", "policy"), EPSILON)
    assert "reference_action_mass" in preference and "optimal_action_mass" not in preference
    policy.update(gold_probs_kind="optimal_action_policy", family_id="snake_local_heuristic")
    snake = row_metrics(checked_row(policy, "test", "policy"), EPSILON)
    assert "reference_action_mass" in snake and "optimal_action_mass" not in snake
    assert cohort_signature([checked, checked_row(other, "test", "event")]) == cohort_signature([checked_row(other, "test", "event"), checked])
    print(json.dumps({"self_check": "passed", "checks": ["proper_metrics", "positive_class_ece", "zero_probability_retention", "invalid_event_rejection", "policy_separation", "order_independent_cohort_hash"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--output", type=Path, default=Path("results/scaled_probability_summary.json"))
    parser.add_argument("--event-runs", nargs="*", default=DEFAULT_EVENT_RUNS)
    parser.add_argument("--initial-run", help="Optional event baseline run name under runs-dir, or an absolute directory")
    parser.add_argument("--policy-runs", nargs="*", default=[])
    parser.add_argument("--splits", nargs="+", default=["test", "ood"])
    parser.add_argument("--epsilon", type=float, default=EPSILON)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    if not math.isfinite(args.epsilon) or not 0 < args.epsilon < 0.01:
        parser.error("epsilon must be finite and between 0 and 0.01")
    if len(set(args.splits)) != len(args.splits):
        parser.error("Repeated split names")
    report = summarize_runs(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), "runs": len(report["runs"]),
                      "missing_files": len(report["missing_files"]), "errors": report["errors"]}))
    raise SystemExit(0 if report["complete"] else 1 if report["errors"] else 2)


if __name__ == "__main__":
    main()
