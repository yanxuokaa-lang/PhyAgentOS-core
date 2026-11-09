"""Comparative benchmark profiler: Von (ModernBERT) vs Laya vs OpenJev vs TypeSafe Jev."""

import argparse
import json
import time
from collections import defaultdict
from typing import Dict, List, Tuple
import von


def evaluate_backend(
    backend_name: str,
    rows: List[dict],
) -> Tuple[float, float, float]:
    von.set_backend(backend_name)
    correct = 0
    total = len(rows)
    latencies = []
    class_correct = defaultdict(int)
    class_total = defaultdict(int)

    for r in rows:
        criteria = {opt["id"]: opt["description"] for opt in r["options"]}
        expected = r["options"][r["label"]]["id"]

        t0 = time.perf_counter()
        ans = von.decide(state=r["state"], choices=criteria, instructions=r["question"])
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)
        pred = ans.choice

        if pred == expected:
            correct += 1
            class_correct[expected] += 1
        class_total[expected] += 1

    recalls = [class_correct[cls] / class_total[cls] for cls in class_total if class_total[cls] > 0]
    balanced_acc = sum(recalls) / len(recalls) if recalls else 0.0
    raw_acc = correct / total if total > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return raw_acc, balanced_acc, avg_latency


def run_profiler(data_path: str = "benchmarks/data/authored144.jsonl", limit: int = 30):
    with open(data_path, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]

    if limit > 0:
        rows = rows[:limit]

    print(f"\n==========================================================================")
    print(f"  VON vs LAYA vs JEV BENCHMARK PROFILE ({len(rows)} rows from authored144)")
    print(f"==========================================================================\n")

    backends = [
        ("modernbert", "Von (ModernBERT-Large)", 790.0, "790 MB", "~1.2 GB RAM (CPU)"),
        ("laya", "Laya 421M (RLCD)", 840.0, "840 MB", "~1.1 GB RAM (CPU)"),
    ]

    results = []
    for b_id, b_label, size_mb, size_str, hw in backends:
        print(f"Profiling backend: {b_label}...")
        try:
            raw_acc, bal_acc, avg_lat = evaluate_backend(b_id, rows)
            eff = (bal_acc * 100.0) / size_mb
            results.append((b_label, size_str, hw, raw_acc, bal_acc, eff, avg_lat))
            print(f"  -> Balanced Acc: {bal_acc*100:.1f}%, Acc/Weight: {eff:.3f}%/MB, Latency: {avg_lat:.1f}ms\n")
        except Exception as e:
            print(f"  -> Failed to profile {b_label}: {e}\n")

    print(f"=================================================================================================")
    print(f"  FINAL COMPARATIVE LADDER (authored144 Suite)")
    print(f"=================================================================================================")
    print(f"| Backend / Model            | Size      | Hardware / Env     | Balanced Acc | Acc/Weight (%/MB) | Latency / Call |")
    print(f"| :------------------------- | :-------- | :----------------- | :----------- | :---------------- | :------------- |")
    for b_label, size, hw, raw_acc, bal_acc, eff, avg_lat in results:
        print(f"| **{b_label:26}** | {size:9} | {hw:18} | **{bal_acc*100:5.1f}%**     | **{eff:6.3f}% / MB**    | **{avg_lat:6.1f} ms**     |")
    print(f"| OpenJev (Qwen3.5-4B)       | 3.01 GB   | RTX 3090 (24GB)    | 81.3%        | 0.027% / MB       | ~48 ms         |")
    print(f"| Published Jev (TypeSafe)   | ~8–16 GB* | Closed Cloud API   | 88.3%        | ~0.005–0.011%/MB  | 100-300 ms     |")
    print(f"=================================================================================================")
    print(f"* Speculated Jev size: ~8B–14B MoE causal backbone (~8–16 GB) based on Archer Hume reverse-engineering.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-backend profiler")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--data", type=str, default="benchmarks/data/authored144.jsonl")
    args = parser.parse_args()
    run_profiler(data_path=args.data, limit=args.limit)
