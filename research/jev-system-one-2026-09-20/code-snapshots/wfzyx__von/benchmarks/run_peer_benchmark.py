"""Peer benchmark runner using Justin Bradford's (jabr) classifier-benchmark suite.

Evaluates Von-1.0 across 8 tasks and 78 cases covering Choice, Noul, and Score.
Source: https://github.com/jabr/classifier-benchmark
"""

import time
import von
from benchmarks.jabr_cases import ALL_TASK_FUNCTIONS


def main():
    print("=" * 60)
    print("Running Peer Benchmark (jabr/classifier-benchmark)")
    print("Model: wfzyx/von-1.0 (local)")
    print("=" * 60)

    t0_suite = time.perf_counter()
    micro_correct, micro_total = 0, 0
    macro_accs = []
    task_results = []

    for fn in ALL_TASK_FUNCTIONS:
        task = fn()
        correct = 0
        total = len(task.cases)
        t0_task = time.perf_counter()

        for c in task.cases:
            if task.type == "choice":
                res = von.decide(
                    c.state,
                    choices=dict(task.question.criteria),
                    instructions=task.question.instructions,
                )
                pred = res.choice
                exp = c.expected
            elif task.type == "noul":
                p = von.judge(c.state, instructions=task.question.instructions)
                pred = "yes" if p >= 0.5 else "no"
                exp = "yes" if c.expected else "no"
            elif task.type == "score":
                res = von.rate(
                    c.state,
                    criteria=list(task.question.criteria),
                    instructions=task.question.instructions,
                )
                probs = res.probabilities
                pred = max(probs, key=lambda k: probs[k]) if probs else "0"
                exp = str(c.expected)
            else:
                raise ValueError(f"Unknown task type: {task.type}")

            if pred == exp:
                correct += 1

        latency_ms = (time.perf_counter() - t0_task) * 1000 / total
        acc = correct / total
        micro_correct += correct
        micro_total += total
        macro_accs.append(acc)
        task_results.append((task.id, task.type, acc, correct, total, latency_ms))
        print(f"{task.id:<22} ({task.type:<6}): {acc:.3f} ({correct}/{total}) [{latency_ms:.1f}ms/case]")

    total_time = time.perf_counter() - t0_suite
    micro_acc = micro_correct / micro_total
    macro_acc = sum(macro_accs) / len(macro_accs)

    print("-" * 60)
    print(f"Micro Accuracy: {micro_acc:.3f} ({micro_correct}/{micro_total})")
    print(f"Macro Accuracy: {macro_acc:.3f}")
    print(f"Total Wall Time: {total_time:.2f}s ({total_time*1000/micro_total:.1f}ms mean/case)")
    print("=" * 60)


if __name__ == "__main__":
    main()
