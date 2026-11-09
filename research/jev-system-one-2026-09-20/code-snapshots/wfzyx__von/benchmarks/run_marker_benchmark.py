"""Peer benchmark runner for the Phase 3 Option-Marker Joint Model."""

import time
from benchmarks.jabr_cases import ALL_TASK_FUNCTIONS
from von.backends.option_marker_backend import OptionMarkerBackend

def main():
    print("=" * 65)
    print("Phase 3 Option-Marker Peer Benchmark (jabr/classifier-benchmark)")
    print("Checkpoint: checkpoints/von-option-marker")
    print("=" * 65)

    backend = OptionMarkerBackend(checkpoint_dir="checkpoints/von-option-marker")
    
    t0_suite = time.perf_counter()
    micro_correct, micro_total = 0, 0
    macro_accs = []

    for fn in ALL_TASK_FUNCTIONS:
        task = fn()
        correct = 0
        total = len(task.cases)
        t0_task = time.perf_counter()

        for c in task.cases:
            if task.type == "choice":
                res = backend.evaluate_choice("c", c.state, task.question)
                pred = res.choice
                exp = c.expected
            elif task.type == "noul":
                res = backend.evaluate_noul("n", c.state, task.question)
                pred = "yes" if res.noul >= 0.5 else "no"
                exp = "yes" if c.expected else "no"
            elif task.type == "score":
                res = backend.evaluate_score("s", c.state, task.question)
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
        print(f"{task.id:<24} ({task.type:<6}): {acc:.3f} ({correct}/{total}) [{latency_ms:.1f}ms/case]")

    total_time = time.perf_counter() - t0_suite
    micro_acc = micro_correct / micro_total
    macro_acc = sum(macro_accs) / len(macro_accs)

    print("-" * 65)
    print(f"Option-Marker Micro Accuracy: {micro_acc:.3f} ({micro_correct}/{micro_total})")
    print(f"Option-Marker Macro Accuracy: {macro_acc:.3f}")
    print(f"Total Wall Time: {total_time:.2f}s ({total_time*1000/micro_total:.1f}ms mean/case)")
    print("=" * 65)

if __name__ == "__main__":
    main()
