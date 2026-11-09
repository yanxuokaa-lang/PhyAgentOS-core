#!/usr/bin/env python3
"""冻结 toy 模型的追加 OOD 解析概率诊断；不训练、不调参、不调用教师。"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time

from predict_toy_decisions import (
    answer_from_probabilities, load_decision_model_class, local_checkpoint_files,
    prepare_examples, read_json, validate_request,
)

FLOOR = 1e-12


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def distribution_metrics(reference, student):
    if len(reference) != len(student) or not reference:
        raise ValueError("参考与学生分布的维度不一致")
    for values in (reference, student):
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError("概率必须有限且在[0,1]")
        if abs(math.fsum(values) - 1) > 1e-5:
            raise ValueError("概率总和不为1")
    # 这里只修正FP32 softmax导出至JSON的浮点总和误差；不处理教师舍入概率。
    student_sum = math.fsum(student)
    student = [p / student_sum for p in student]
    entropy = lambda p: -math.fsum(x * math.log(x) for x in p if x > 0)
    h_ref, h_student = entropy(reference), entropy(student)
    return {
        "tv": 0.5 * math.fsum(abs(a-b) for a, b in zip(reference, student)),
        "kl_reference_to_student_nats": math.fsum(
            a * (math.log(a) - math.log(max(b, FLOOR)))
            for a, b in zip(reference, student) if a > 0),
        "reference_entropy_nats": h_ref, "student_entropy_nats": h_student,
        "student_normalized_entropy": h_student / math.log(len(student)),
        "student_sum_before_float_normalization": student_sum,
        "student_probabilities_floored_for_log": sum(p < FLOOR for p in student),
    }


def summarize(cases, rows, execution):
    case_by_id = {case["id"]: case for case in cases}
    if len(case_by_id) != len(cases):
        raise ValueError("case ID 重复")
    successful = []
    for row in rows:
        if row["status"] != "ok":
            continue
        case = case_by_id[row["id"]]
        ids = case["canonical_candidate_ids"]
        if set(ids) != set(row["probabilities"]) or set(ids) != set(case["reference_distribution"]):
            raise ValueError("候选 ID 与参考分布不匹配")
        successful.append({"id": row["id"], "case_family": case["case_family"],
                           "K": case["K"], "permutation": case["permutation"],
                           "max_path_tokens": row["max_path_tokens"],
                           **distribution_metrics([case["reference_distribution"][i] for i in ids],
                                                  [row["probabilities"][i] for i in ids])})

    def aggregate(selected):
        names = ["tv", "kl_reference_to_student_nats", "reference_entropy_nats",
                 "student_entropy_nats", "student_normalized_entropy"]
        return {"n": len(selected), **{
            name + "_mean": math.fsum(row[name] for row in selected) / len(selected)
            for name in names}} if selected else {"n": 0}

    predictions = {row["id"]: row for row in rows if row["status"] == "ok"}
    pairs = {}
    for case in cases:
        pairs.setdefault((case["case_family"], case["K"]), {})[case["permutation"]] = case
    permutation_results = []
    for (family, k), pair in pairs.items():
        a, b = pair.get("original"), pair.get("reverse")
        if a is None or b is None or a["id"] not in predictions or b["id"] not in predictions:
            permutation_results.append({"case_family": family, "K": k, "status": "incomplete"})
            continue
        pa, pb = predictions[a["id"]]["probabilities"], predictions[b["id"]]["probabilities"]
        delta = [abs(pa[cid] - pb[cid]) for cid in a["canonical_candidate_ids"]]
        permutation_results.append({"case_family": family, "K": k, "status": "ok",
                                    "max_probability_delta_after_id_alignment": max(delta),
                                    "tv_after_id_alignment": 0.5 * math.fsum(delta)})
    return {
        "schema_version": "openjev-known-distribution-diagnostic-v1",
        "purpose": "训练结束后追加OOD解析概率诊断；不用于模型选择或调参；不等于真实事件校准评估",
        "reference_kind": "analytically_defined_conditional_distribution_not_observed_outcome",
        "metric_definition": {"weighting": "question mean", "entropy_unit": "nats",
                              "kl": "KL(reference || student)", "log_probability_floor": FLOOR,
                              "floor_rule": "仅log内max(p,1e-12)，不重新归一化clipped分布；零参考项贡献0",
                              "student_normalization": "仅在总和偏差<=1e-5时除以原总和，原始输出和总和保留"},
        "execution": execution, "requested_cases": len(cases), "successful_cases": len(successful),
        "failed_or_unrun_cases": [row for row in rows if row["status"] != "ok"],
        "overall": aggregate(successful),
        "by_family": {family: aggregate([r for r in successful if r["case_family"] == family])
                      for family in sorted({c["case_family"] for c in cases})},
        "by_K": {str(k): aggregate([r for r in successful if r["K"] == k])
                 for k in sorted({c["K"] for c in cases})},
        "cases": successful, "permutation_pairs": permutation_results,
    }


def run(cases, checkpoint_dir, max_seconds):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "7":
        raise ValueError("此次诊断只授权 CUDA_VISIBLE_DEVICES=7")
    payload = {"states": [{key: case[key] for key in ("id", "state", "questions")} for case in cases]}
    validate_request(payload)
    if any(len(case["questions"]) != 1 for case in cases):
        raise ValueError("此次诊断要求每case恰好一个question")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    rows, token_stats = [], {}
    execution = {"checkpoint": str(checkpoint_dir), "precision": "bf16", "temperature": 1.0,
                 "temperature_fitted": False, "batch_questions": 1, "max_length": 4096,
                 "candidate_truncation": False, "native_triton_disabled": True,
                 "autoregressive_decode_steps": 0, "training_steps": 0, "teacher_calls": 0,
                 "max_runtime_seconds": max_seconds, "physical_gpu": 7}
    started = time.monotonic()

    def deadline(signum, frame):
        raise TimeoutError(f"达到{max_seconds}秒截止；不重试或修改题目")

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(max_seconds)
    active_id = None
    try:
        import torch
        from safetensors.torch import load_file
        from transformers import AutoConfig, AutoModel, AutoTokenizer
        from torch._native import triton_utils
        triton_utils.deregister_op_overrides()
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported():
            raise RuntimeError("需要且仅允许一个可见的BF16 CUDA设备")
        torch.backends.cuda.matmul.allow_tf32 = False
        _, files = local_checkpoint_files(checkpoint_dir)
        config = read_json(files["run_config"])
        tokenizer = AutoTokenizer.from_pretrained(str(files["tokenizer"]), local_files_only=True,
                                                 trust_remote_code=False)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        # 逐case做静态编码并记录超长失败，不修改或截断该题；其余原题继续。
        examples = []
        for case in cases:
            active_id = case["id"]
            try:
                ex = prepare_examples({"states": [{key: case[key] for key in ("id", "state", "questions")}]},
                                      tokenizer, 4096)[0]
                lengths = list(map(len, ex["leaf_tokens"]))
                token_stats[case["id"]] = {"max_path_tokens": max(lengths),
                                          "min_path_tokens": min(lengths),
                                          "candidate_paths": len(lengths),
                                          "padded_tokens": len(lengths) * max(lengths)}
                examples.append(ex)
            except ValueError as exc:
                rows.append({"id": case["id"], "status": "failed", "error_type": type(exc).__name__,
                             "message": str(exc)})
        active_id = None
        body_config = AutoConfig.from_pretrained(str(files["body_config"]), local_files_only=True,
                                                trust_remote_code=False)
        body_config.use_cache = False
        if getattr(body_config, "max_position_embeddings", 4096) < 4096:
            raise ValueError("checkpoint配置的上下文上限小于4096")
        body = AutoModel.from_config(body_config, attn_implementation="sdpa", trust_remote_code=False).float()
        model = load_decision_model_class()(body, config["set_head"])
        weights = load_file(str(files["weights"]), device="cpu")
        model.load_state_dict(weights, strict=True)
        del weights
        model.to(device="cuda:0", dtype=torch.float32).eval()
        torch.cuda.reset_peak_memory_stats()
        inference_started = time.monotonic()
        with torch.inference_mode():
            for ex in examples:
                active_id = ex["state_id"]
                before = time.monotonic()
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits, _ = model([ex], tokenizer.pad_token_id)
                k = len(ex["candidate_ids"])
                values = logits[0, :k].float()
                if not torch.isfinite(values).all():
                    raise ValueError("模型产生非有限logits")
                probabilities = values.softmax(-1).cpu().tolist()
                answer = answer_from_probabilities(ex, probabilities)
                rows.append({"id": active_id, "qid": ex["qid"], "status": "ok",
                             "probabilities": answer["probabilities"], "logits": values.cpu().tolist(),
                             **token_stats[active_id], "forward_seconds": time.monotonic() - before})
                print(json.dumps({"completed": active_id, "K": k, **token_stats[active_id]}, ensure_ascii=False), flush=True)
        execution.update(inference_seconds=time.monotonic() - inference_started,
                         peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
                         peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved())
    except Exception as exc:
        execution["stopped_on_error"] = {"active_case": active_id, "error_type": type(exc).__name__, "message": str(exc)}
        if active_id is not None and active_id not in {row["id"] for row in rows}:
            rows.append({"id": active_id, "status": "failed", "error_type": type(exc).__name__,
                         "message": str(exc), **token_stats.get(active_id, {})})
    finally:
        signal.alarm(0)
        execution["total_seconds"] = time.monotonic() - started
    recorded = {row["id"] for row in rows}
    rows.extend({"id": case["id"], "status": "not_run", "reason": "运行在此前失败或截止后停止",
                 **token_stats.get(case["id"], {})} for case in cases if case["id"] not in recorded)
    execution["actual_max_path_tokens"] = max((r["max_path_tokens"] for r in token_stats.values()), default=None)
    execution["forward_passes_completed"] = sum(row["status"] == "ok" for row in rows)
    return rows, execution


def brief(summary):
    lines = ["# 冻结学生模型的追加解析概率诊断", "",
             "这是训练结束后新增的 OOD 诊断，不用于选择模型、checkpoint、温度或超参数，也不等于实际事件频率上的校准评测。",
             "参考分布来自自写概率实验的明示规则；没有教师调用、训练、原生基线重跑或温度拟合。", "",
             f"完成 {summary['successful_cases']}/{summary['requested_cases']} 题。固定 instruct_teacher、GPU 7、BF16、T=1，每次前向保留一道题的全部候选。",
             f"实际最长候选路径 {summary['execution']['actual_max_path_tokens']} token；max_length=4096，无输入或候选截断。",
             f"全流程耗时 {summary['execution']['total_seconds']:.2f} 秒。KL 方向为 reference→student；仅对 log 中的学生概率使用 {FLOOR:g} 下限。", "",
             "| 题族 | 题数 | 平均 TV | 平均 KL（nat） | 学生平均归一化熵 |", "|---|---:|---:|---:|---:|"]
    for family, values in summary["by_family"].items():
        if values["n"]:
            lines.append(f"| {family} | {values['n']} | {values['tv_mean']:.6f} | {values['kl_reference_to_student_nats_mean']:.6f} | {values['student_normalized_entropy_mean']:.6f} |")
    lines += ["", "| 候选数 K | 题数 | 平均 TV | 平均 KL（nat） |", "|---|---:|---:|---:|"]
    for k, values in summary["by_K"].items():
        if values["n"]:
            lines.append(f"| {k} | {values['n']} | {values['tv_mean']:.6f} | {values['kl_reference_to_student_nats_mean']:.6f} |")
    pairs = [r for r in summary["permutation_pairs"] if r["status"] == "ok"]
    if pairs:
        max_delta = max(r["max_probability_delta_after_id_alignment"] for r in pairs)
        lines += ["", f"原序/倒序候选按语义 ID 还原后，共 {len(pairs)} 对；最大单候选概率差 {max_delta:.9g}。",
                  "小顺序差只说明置换稳定性，不能抵消参考分布误差，也不能证明模型学到了条件概率语义。"]
    if summary["failed_or_unrun_cases"]:
        lines += ["", "存在失败或未运行题，已在 JSON 中逐项保留；汇总只包含成功题，不代表完整覆盖。"]
    lines += ["", "此训练集只有少量客服规则题；大候选数和解析随机实验是额外分布外输入。本结果仅描述冻结模型在这 40 个预定自写题上的行为。 候选数与state长度共同增长，题族和符号标签也不同，不能将退化解释为K的独立因果效应；均匀题TV低不证明一般校准更好。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("research"))
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 120:
        raise ValueError("截止必须在1至120秒，超过预算不重试")
    inputs = read_json(args.input)
    cases = inputs["cases"]
    rows, execution = run(cases, args.checkpoint_dir, args.max_seconds)
    execution["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    summary = summarize(cases, rows, execution)
    write_json(args.output_dir / "student_distribution_probe_raw.json", {"execution": execution, "cases": rows})
    write_json(args.output_dir / "student_distribution_probe_summary.json", summary)
    (args.output_dir / "student_distribution_probe_brief_zh.md").write_text(brief(summary), encoding="utf-8")
    print(json.dumps({"successful_cases": summary["successful_cases"], "requested_cases": len(cases),
                      "execution": execution, "overall": summary["overall"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
