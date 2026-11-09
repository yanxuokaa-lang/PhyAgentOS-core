#!/usr/bin/env python3
"""Rebuild docs/ATOMIC_PLANNING.md from committed results/composed_*.json reports.

The input directory is always the repository's results directory. Fresh
runs_repro evaluations are separate artifacts and are not loaded by this script.
"""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    systems = [
        ("Starting NanoJev", "composed_initial.json"),
        ("Full-map game training", "composed_games_api.json"),
        ("Local-question training", "composed_local_atomic.json"),
        ("Jev", "composed_jev.json"),
        ("Geometry reference", "composed_reference.json"),
    ]
    reports = [(name, filename, json.loads((root / "results" / filename).read_text()))
               for name, filename in systems if (root / "results" / filename).exists()]
    if not reports:
        raise ValueError("No completed composed-maze reports")
    first = reports[0][2]
    for _, _, report in reports:
        for key in ("source_episodes_sha256", "selected_episode_ids", "audit_inputs_sha256",
                    "planner_trajectories_sha256", "question_template"):
            if report[key] != first[key]:
                raise ValueError(f"Unmatched fixed diagnostic protocol: {key}")
        if report["model_role"] != "diagnostic_only" or report["protocol"]["model_controls_actions"]:
            raise ValueError("Diagnostic and controlling model roles must stay separate")
    truths = [int(y) for row in first["audits"] for y in row["truth"].values()]
    majority = max(sum(truths), len(truths) - sum(truths)) / len(truths)
    lines = [
        "# Atomic maze judgments and code planning", "",
        "The pipeline separates local perception from route composition. Each model request contains "
        "an agent-centered **5×5 ASCII window**, its coordinates, and four independent Boolean "
        "questions: is a one-cell north/east/south/west attempt traversable? Goal coordinates, "
        "shortest-path actions, route lengths, and oracle labels are absent from model inputs.", "",
        "## Fixed-route question benchmark", "",
        "Code executes the same shortest routes on the preselected 8×8, 16×16, and 50×50 maps: "
        "**16, 24, and 96 moves**, respectively. Every eighth pre-move state contributes four "
        "questions, giving **17 states / 68 questions**. Input and route hashes match across systems.", "",
        "This benchmark gives the model **diagnostic-only** authority. Its outputs cannot change "
        "the route, so the 3/3 BFS completion result belongs to the planner. The model measurement "
        "is its atomic probability quality on those fixed states.", "",
        "| System | Accuracy | Scalar Brier ↓ | NLL ↓ | Safe planner moves predicted unsafe |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, filename, report in reports:
        m = report["summary"]
        lines.append(f"| [{name}](../results/{filename}) | {m['atomic_accuracy']:.2%} | "
                     f"{m['atomic_brier']:.5f} | {m['atomic_nll']:.5f} | "
                     f"{m['would_veto_count']}/{m['audited_states']} |")
    lines += ["", f"The majority-class baseline is **{majority:.2%}** ({sum(truths)} true / "
              f"{len(truths)-sum(truths)} false). Brier here is scalar Bernoulli squared error; "
              "the event experiment reports the two-class summed Brier, which is twice this value. "
              "The fixed route sample is small and contains correlated states from three maps.", "",
              "## Matching local training inputs", "",
              "`build_local_maze_data.py` transforms existing maze snapshots using exactly the "
              "inference renderer. It preserves map groups and train/dev/calibration/test/OOD "
              "assignments. Labels describe one-step geometry; no route action is a training target. "
              "The 50×50 split tests local judgments at held-out board sizes, not reasoning over "
              "all 2,500 cells at once.", "",
              "Use fresh data/run directories. The released checkpoint download and CUDA setup are "
              "in the [README](../README.md); these commands reproduce the local pilot from generated inputs.", "",
              "```bash", "python3 scripts/build_scaled_games.py --output-dir data/scaled_games_v4b",
              "python3 scripts/build_local_maze_data.py --input data/scaled_games_v4b/policy \\",
              "  --output data/local_maze_v1", "CUDA_VISIBLE_DEVICES=0 python scripts/train_pipeline_decisions.py \\",
              "  --input data/local_maze_v1 --output-dir runs_repro/local_atomic_seed17 \\",
              "  --init-checkpoint checkpoints/NanoJev --objective gold_distribution --loss ce \\",
              "  --steps 300 --head-steps 0 --seed 17 --eval-every 50 --batch-questions 16 \\",
              "  --microbatch-questions 4 --max-microbatch-tokens 16384 --max-length 2048 \\",
              "  --gradient-checkpointing --precision bf16 --disable-native-triton",
              "python3 scripts/evaluate_composed_maze.py \\",
              "  --episodes results/rollout_pilot_episodes.jsonl --engine checkpoint \\",
              "  --checkpoint runs_repro/local_atomic_seed17 --output runs_repro/composed_local_atomic.json",
              "```", "",
              "The new evaluation is saved to `runs_repro/composed_local_atomic.json`. The table above "
              "describes the committed `results/composed_*.json` reports. "
              "`python3 scripts/summarize_composed_maze.py` reads those committed reports and rewrites "
              "`docs/ATOMIC_PLANNING.md`; it does not consume `runs_repro` outputs.", "",
              "Whole-map direct-action results remain a separate [planning stress test](DEVELOPMENT_RESULTS.md).", ""]
    manifest_path = root / "results" / "local_maze_data_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        counts = ", ".join(f"{split}: {row['questions']}" for split, row in manifest["outputs"].items())
        lines += ["## Frozen local dataset", "",
                  f"The [dataset manifest](../results/{manifest_path.name}) records **{manifest['total_rows']} "
                  f"states / {manifest['total_questions']} questions** ({counts}). Source-map assignments "
                  "are retained, with no cross-split source groups. Only state and question fields enter "
                  "the model; full environment geometry stays in metadata for reproducible simulation.", ""]
    local_summary = root / "results" / "local_atomic_question_summary.json"
    if local_summary.exists():
        local = json.loads(local_summary.read_text())["runs"]["local_atomic_seed17"]["splits"]
        lines += ["The local model starts from the released NanoJev checkpoint and trains for 300 "
                  "CE updates, with dev-NLL checkpoint selection (selected step 300). All held-out "
                  "questions are retained in the [question report](../results/local_atomic_question_summary.json).", "",
                  "| Split | Questions | Accuracy | Constant true | Scalar Brier ↓ | NLL ↓ |",
                  "|---|---:|---:|---:|---:|---:|"]
        for split, row in local.items():
            metrics = row["by_semantics"]["deterministic_truth"]["overall"]["metrics"]
            prevalence = manifest["outputs"][split]["labels"]["all"]["true_prevalence"]
            lines.append(f"| {split} | {row['rows']} | {metrics['accuracy']['mean']:.2%} | "
                         f"{prevalence:.2%} | {metrics['observed_vector_brier']['mean']/2:.5f} | "
                         f"{metrics['observed_nll']['mean']:.5f} |")
        lines += ["", "## Model-guided execution", "",
                  "The [edge-exploration controller](../scripts/evaluate_model_edges_maze.py) makes "
                  "model judgments part of execution. It stores attempted edges, ranks unknown "
                  "directions using predicted safety and goal distance, and uses BFS only on "
                  "already traversed open edges to find another exploration frontier. A collision "
                  "leaves the agent in place and marks that edge blocked. Low-probability probes "
                  "allow recovery from false-negative judgments.", "",
                  "```mermaid", "flowchart LR", "  S[Local 5x5 state] --> M[Four parallel Boolean judgments]",
                  "  M --> P[Safety probabilities]", "  P --> C[Edge memory and exploration code]",
                  "  C --> A[Attempt one move]", "  A --> E[Environment feedback]", "  E --> S", "  E --> C",
                  "```", "",
                  "See [the model-guided results](MODEL_EDGE_RESULTS.md) for the five-system comparison, "
                  "including constant-0.5 perception and perfect local perception under the same "
                  "exploration code. This experiment is separate from the diagnostic-only BFS table above.", "",
                  "```bash", "python3 scripts/evaluate_model_edges_maze.py \\",
                  "  --episodes results/rollout_pilot_episodes.jsonl --engine checkpoint \\",
                  "  --checkpoint runs_repro/local_atomic_seed17 --max-steps 0 \\",
                  "  --output runs_repro/model_edges_local_atomic.json", "```", ""]
    lines += ["## API probability records", "",
              "Jev measurements use the gateway's rounded Boolean probabilities, converted to a "
              "unit-sum controller distribution by the existing worker. All 68 native vectors in "
              "this fixed diagnostic run already sum to one within 1e-12. Local journal entries "
              "retain API call and request hashes; the report's `input_sha256` instead identifies "
              "the full local request including its transport ID.", ""]
    (root / "docs" / "ATOMIC_PLANNING.md").write_text("\n".join(lines))
    print(json.dumps({"systems": len(reports), "questions": len(truths),
                      "audit_inputs_sha256": first["audit_inputs_sha256"]}))


if __name__ == "__main__":
    main()
