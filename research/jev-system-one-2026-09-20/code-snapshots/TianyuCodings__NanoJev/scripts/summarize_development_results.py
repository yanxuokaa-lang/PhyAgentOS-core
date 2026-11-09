#!/usr/bin/env python3
"""Replay and summarize the complete preselected six-case development pilot.

Uses saved probabilities/actions only. No API, model execution, or new episode
selection. The reference planner and a future learned-judgment planner are
different systems; this script does not transfer credit between them.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

from compact_game_rollout import digest
from scaled_maze import step as maze_step, valid_actions as maze_actions, solve as maze_solve
from snake_game import step as snake_step, valid_actions as snake_actions


ROLES = [
    ("initial", "Initial NanoJev", "rollout_initial.json", "Existing NanoJev checkpoint before this game training; not untouched Qwen.", "checkpoint", "greedy"),
    ("gold", "Game-target NanoJev", "rollout_games_gold.json", "NanoJev trained on programmatic game-question targets.", "checkpoint", "greedy"),
    ("api", "API-target NanoJev", "rollout_games_api.json", "NanoJev trained on saved API-reference game-question targets.", "checkpoint", "greedy"),
    ("jev", "Jev", "rollout_jev.json", "Recorded Jev API decision controller.", "jev", "greedy"),
    ("reference", "Reference code", "rollout_reference.json", "Maze: exact shortest-path actions. Snake: local collision-avoidance/food-progress rule, not global optimal play.", "reference", "greedy"),
    ("random", "Uniform random", "rollout_random.json", "Uniform sampling over the offered action set.", "random", "sample"),
]


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def check_episode(episode, frozen, controller, horizon):
    if episode["initial_state"] != frozen["initial_state"]:
        raise ValueError("Initial state differs from the frozen episode input")
    for key in ("id", "game", "split", "size"):
        if episode[key] != frozen[key]:
            raise ValueError(f"Frozen episode field differs: {key}")
    if episode["horizon"] != horizon or not 0 <= len(episode["steps"]) <= horizon:
        raise ValueError("Episode horizon mismatch")
    state = episode["initial_state"]
    maze = episode["game"] == "scaled_maze"
    transition, valid = (maze_step, maze_actions) if maze else (snake_step, snake_actions)
    forced, greedy_checked = 0, 0
    for index, item in enumerate(episode["steps"]):
        if digest(state) != item["state_sha256"]:
            raise ValueError(f"Before-state hash mismatch at step {index}")
        if (state["position"] == state["goal"]) if maze else state["done"]:
            raise ValueError("Saved action after a terminal state")
        probabilities = item["probabilities"]
        offered = list(valid(state))
        if set(probabilities) != set(offered):
            raise ValueError("Saved probability support differs from offered actions")
        if any(type(p) not in {int, float} or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities.values()):
            raise ValueError("Invalid action probabilities")
        if abs(math.fsum(probabilities.values()) - 1) > 1e-5:
            raise ValueError("Action probability sum differs from one")
        if item["action"] not in probabilities or probabilities[item["action"]] <= 0:
            raise ValueError("Chosen action is outside positive probability support")
        if controller == "greedy":
            expected = max(sorted(probabilities), key=probabilities.__getitem__)
            if item["action"] != expected:
                raise ValueError("Recorded greedy action differs from the saved distribution")
            greedy_checked += 1
        if len(offered) == 1:
            forced += 1
            if item["actor"] != "forced_move":
                raise ValueError("A single legal action was not marked as a forced move")
        state = transition(state, item["action"])
        if digest(state) != item["next_state_sha256"]:
            raise ValueError(f"After-state hash mismatch at step {index}")
    if state != episode["final_state"] or episode["steps_count"] != len(episode["steps"]):
        raise ValueError("Final state or saved step count differs from replay")
    success = state["position"] == state["goal"] if maze else state.get("outcome") == "win"
    score = int(success) if maze else state["score"]
    if maze:
        outcome = "goal" if success else "no_legal_actions" if not valid(state) else "horizon_exhausted"
    else:
        outcome = state["outcome"] if state["done"] else "horizon_survived"
    if (success, score, outcome) != (episode["success"], episode["score"], episode["outcome"]):
        raise ValueError("Saved outcome differs from the final simulator state")
    if outcome.startswith("horizon_") and len(episode["steps"]) != horizon:
        raise ValueError("Horizon termination occurred before the frozen limit")
    distance = maze_solve(episode["initial_state"])["distance"] if maze else None
    if maze and distance != episode["initial_shortest_path"]:
        raise ValueError("Saved initial shortest path differs from the simulator")
    return {"id": episode["id"], "split": episode["split"], "game": episode["game"], "size": episode["size"],
            "topology": episode["initial_state"].get("topology"), "success": success, "score": score,
            "steps": len(episode["steps"]), "outcome": outcome, "initial_shortest_path": distance,
            "initial_state_sha256": digest(episode["initial_state"]), "final_state_sha256": digest(state),
            "forced_steps": forced, "greedy_actions_verified": greedy_checked,
            "transition_hashes_verified": len(episode["steps"])}


def atomic_label_audit(rows):
    confusion = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    for row in rows:
        true_index = row["candidate_ids"].index("true")
        actual = row["gold_index"] == true_index
        predicted = max(range(len(row["student_probs"])), key=row["student_probs"].__getitem__) == true_index
        key = ("true_positive" if actual else "false_positive") if predicted else ("false_negative" if actual else "true_negative")
        confusion[key] += 1
    positives = confusion["true_positive"] + confusion["false_negative"]
    negatives = confusion["true_negative"] + confusion["false_positive"]
    return {"questions": len(rows), "observed_true": positives, "observed_false": negatives,
            "accuracy": (confusion["true_positive"] + confusion["true_negative"]) / len(rows),
            "always_true_accuracy": positives / len(rows), "always_false_accuracy": negatives / len(rows),
            "confusion": confusion,
            "note": "Fixed constant-answer accuracy controls; these are not fitted event probabilities or evidence of balanced task coverage."}


def question_diagnostics(path):
    if not path.is_file():
        return {"status": "missing", "path": str(path), "runs": {}}
    source, sha = load(path)
    result = {"path": str(path), "source_sha256": sha, "runs": {}}
    for name in ["games_gold_seed17", "games_api_seed17"]:
        run = source.get("runs", {}).get(name)
        if not run:
            continue
        result["runs"][name] = {}
        for split, saved in run["splits"].items():
            groups = defaultdict(list)
            for row in saved.get("per_row_metrics", []):
                if row["category"] == "deterministic_truth":
                    family = "atomic_geometry" if row["qid"].startswith(("clear_", "safe_")) else "planning_truth"
                    groups[family].append(row)
                else:
                    groups["action_preference"].append(row)
            summary = {}
            for profile, rows in groups.items():
                metrics = {}
                for metric in ["accuracy", "observed_nll", "observed_vector_brier", "optimal_action_mass", "reference_action_mass"]:
                    values = [row[metric] for row in rows if metric in row]
                    if values:
                        metrics[metric] = {"questions": len(values), "mean": math.fsum(values) / len(values)}
                summary[profile] = {"questions": len(rows), "metrics": metrics}
                if profile == "atomic_geometry":
                    summary[profile]["label_audit"] = atomic_label_audit(rows)
                    summary[profile]["by_family"] = {
                        family: atomic_label_audit([row for row in rows if row["family_id"] == family])
                        for family in sorted({row["family_id"] for row in rows})}
            result["runs"][name][split] = summary
    result["status"] = "complete" if len(result["runs"]) == 2 else "pending"
    return result


def build(args):
    protocol_path = args.results_dir / "rollout_pilot_protocol.json"
    protocol, protocol_sha = load(protocol_path)
    frozen_raw = args.episodes.read_bytes()
    frozen_sha = hashlib.sha256(frozen_raw).hexdigest()
    frozen = [json.loads(line) for line in frozen_raw.decode().splitlines() if line.strip()]
    ids = [row["id"] for row in protocol["episodes"]]
    if len(ids) != 6 or len(set(ids)) != 6 or [row["id"] for row in frozen] != ids:
        raise ValueError("Expected exactly the six ordered preselected episodes")
    frozen_by_id = {row["id"]: row for row in frozen}
    if protocol["max_steps"] != 128:
        raise ValueError("The frozen pilot horizon must remain 128")
    report = {"schema_version": "nanojev-development-pilot-v1", "complete": False,
              "protocol": {"path": str(protocol_path), "sha256": protocol_sha, **protocol},
              "episode_source": {"path": str(args.episodes), "sha256": frozen_sha},
              "case_order": ids, "systems": {}, "missing": [],
              "scope": {"saved_transition_replay": True, "probability_support_and_greedy_actions": True,
                        "same_initial_states_and_horizon": True, "all_successes_and_failures_retained": True,
                        "new_api_calls": 0, "new_model_forwards": 0,
                        "api_receipt_reverification": False,
                        "random_draw_replay": False,
                        "random_draw_note": "The compact artifacts omit the controller seed/draws; this check verifies action support and deterministic state transitions, not an independent RNG replay.",
                        "hybrid_atomic_planner_measured": False}}
    for key, label, filename, role, engine, controller in ROLES:
        path = args.results_dir / filename
        if not path.is_file():
            report["missing"].append(filename)
            report["systems"][key] = {"label": label, "role": role, "status": "pending", "source": filename}
            continue
        source, sha = load(path)
        if (source["engine"], source["controller"], source["max_steps"], source["episodes_sha256"]) != (engine, controller, 128, frozen_sha):
            raise ValueError(f"Frozen protocol mismatch in {filename}")
        if [row["id"] for row in source["episodes"]] != ids:
            raise ValueError(f"Case selection or order changed in {filename}")
        cases = [check_episode(episode, frozen_by_id[episode["id"]], controller, 128) for episode in source["episodes"]]
        for case in cases:
            cell = f"{case['split']}/{case['game']}/{case['size']}/{case['topology'] or 'snake'}"
            actual = source["summary"][cell]
            expected = {"episodes": 1, "mean_score": float(case["score"]), "mean_steps": float(case["steps"]),
                        "goal_or_full_board_rate": float(case["success"]), "outcomes": {case["outcome"]: 1}}
            if actual != expected:
                raise ValueError(f"Saved summary differs from replay in {filename}/{cell}")
        report["systems"][key] = {"label": label, "role": role, "status": "complete", "source": filename,
                                  "source_sha256": sha, "raw_report_sha256_as_recorded": source.get("raw_report_sha256"),
                                  "engine": engine, "controller": controller, "checkpoint_as_recorded": source.get("checkpoint"),
                                  "episodes": cases, "verified_transitions": sum(c["transition_hashes_verified"] for c in cases)}
    report["complete"] = not report["missing"]
    report["verified_episodes"] = sum(len(item.get("episodes", [])) for item in report["systems"].values())
    report["verified_transitions"] = sum(item.get("verified_transitions", 0) for item in report["systems"].values())
    report["question_diagnostics"] = question_diagnostics(args.results_dir / "scaled_probability_summary.json")
    report["audit_source_sha256"] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                       for name in ["summarize_development_results.py", "scaled_maze.py", "snake_game.py", "compact_game_rollout.py"]}
    return report


def markdown(report):
    lines = ["# Development results: fixed maze and Snake pilot", "",
             "The primary pipeline combines **atomic judgments + code planning**: focused model propositions, exploration memory, and code that composes actions. This page preserves the separate **whole-map direct-action stress test**. See [atomic training](ATOMIC_PLANNING.md) and [model-guided exploration](MODEL_EDGE_RESULTS.md) for the implemented local pipeline. Planner success and event calibration have separate measurements.", "",
             "All six cases were selected before the new rollouts, with a shared **128-step limit** and identical initial states. See the [frozen protocol](../results/rollout_pilot_protocol.json), [machine-readable audit](../results/development_results_summary.json), and [environment/runbook](SCALED_GAMES.md). This is a bounded integration pilot, not a full-size completion benchmark or a population estimate.", "",
             "## Systems and roles", "", "| System | Role | Controller |", "|---|---|---|"]
    for _, label, _, role, _, controller in ROLES:
        lines.append(f"| {label} | {role} | {controller} |")
    lines += ["", "Initial NanoJev is the earlier trained checkpoint, not raw untrained Qwen. The two game-training arms begin from that same checkpoint. Reference-code wins are due to its explicit algorithm; they are not credited to a learned judgment model. Uniform random samples; the other five systems use greedy actions. This pilot does not compare both controllers for every system.", "",
              "## Maze: success / steps", "", "A success is reaching the goal. Every failure remains in the table. The three exact shortest-path lengths are 16, 24, and 96, so all three are feasible within 128 moves.", "",
              "| Case ID | Initial | Game targets | API targets | Jev | Reference | Random |", "|---|---:|---:|---:|---:|---:|---:|"]
    for case_id in report["case_order"]:
        if not case_id.startswith("maze:"):
            continue
        cells = []
        for key, *_ in ROLES:
            system = report["systems"][key]
            case = next((item for item in system.get("episodes", []) if item["id"] == case_id), None)
            cells.append(f"{int(case['success'])} / {case['steps']}" if case else "pending")
        lines.append("| `" + case_id + "` | " + " | ".join(cells) + " |")
    lines += ["", "## Snake: food score / steps / outcome", "",
              "Food score counts food eaten. Surviving to the time limit is distinct from filling the board, and is not a win. `wall` means wall collision; `body` means self-collision; `limit` means the snake remained alive at step 128.", "",
              "| Case ID | Initial | Game targets | API targets | Jev | Reference | Random |", "|---|---:|---:|---:|---:|---:|---:|"]
    short = {"wall_collision": "wall", "self_collision": "body", "horizon_survived": "limit", "win": "win"}
    for case_id in report["case_order"]:
        if not case_id.startswith("snake:"):
            continue
        cells = []
        for key, *_ in ROLES:
            case = next((item for item in report["systems"][key].get("episodes", []) if item["id"] == case_id), None)
            cells.append(f"{case['score']} / {case['steps']} / {short.get(case['outcome'], case['outcome'])}" if case else "pending")
        lines.append("| `" + case_id + "` | " + " | ".join(cells) + " |")
    lines += ["", "The learned direct-action models and Jev do not solve any of these three mazes within the shared 128-step limit. Local Snake behavior varies substantially, and no system fills a board. These results motivated the separate local-question training and code-exploration pipeline linked above.", "",
              "## Independent question and probability measurements", "",
              "[The probability report](../results/scaled_probability_summary.json) and [RLCD experiment](RLCD_EXPERIMENT.md) measure fixed question outputs separately from game trajectories. Atomic `clear_*`/`safe_*` truths, planning truth questions, action preferences, and stochastic events have different targets. Better one-step probability scores do not establish long-horizon game success."]
    diagnostics = report["question_diagnostics"]
    if diagnostics["status"] == "complete":
        lines += ["", "| Game model | Split | Atomic truth accuracy | Always-true accuracy | Questions |", "|---|---|---:|---:|---:|"]
        for name, splits in diagnostics["runs"].items():
            for split, profiles in splits.items():
                atomic = profiles.get("atomic_geometry")
                if atomic:
                    lines.append(f"| `{name}` | {split} | {atomic['metrics']['accuracy']['mean']:.6f} | {atomic['label_audit']['always_true_accuracy']:.6f} | {atomic['questions']} |")
        lines += ["", "The aggregate atomic accuracies of these full-map game-training arms do not exceed the fixed always-true control. The OOD Snake subset contains only true safety labels. The subsequent [local-maze experiment](ATOMIC_PLANNING.md) uses matching local training inputs and reports true/false cases separately from these full-map runs.", "",
                  "| Game model | Split | Atomic family | Accuracy | Always true | Questions |", "|---|---|---|---:|---:|---:|"]
        for name, splits in diagnostics["runs"].items():
            for split, profiles in splits.items():
                for family, audit in profiles.get("atomic_geometry", {}).get("by_family", {}).items():
                    lines.append(f"| `{name}` | {split} | `{family}` | {audit['accuracy']:.6f} | {audit['always_true_accuracy']:.6f} | {audit['questions']} |")
        lines += ["", "The small JSON audit retains confusion counts, separate planning-truth and action-support diagnostics; they are not pooled into atomic accuracy. Maze optimal-action mass and Snake local reference-action mass are separate metrics."]
    else:
        lines += ["", "The game-model question summaries are not yet present for both arms in the current probability report; no missing accuracy values are invented."]
    lines += ["", "## Verification and reproduction", "",
              f"The local audit replays **{report['verified_episodes']} episodes / {report['verified_transitions']} transitions**, checks every saved before/after hash, final outcome, offered probability support, greedy choice, cohort identity, and horizon. Source-file hashes are retained. This does not rerun model inference, verify private API receipts, or reconstruct random draws absent from the compact artifacts.", "",
              "```bash", "python scripts/summarize_development_results.py", "```", "",
              "This command reads the frozen compact reports and rebuilds the small JSON audit and this document without API/GPU calls. Keep all six source reports and the preselected episode file unchanged."]
    if report["missing"]:
        lines += ["", "Pending source reports: " + ", ".join(f"`{name}`" for name in report["missing"]) + "."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--episodes", type=Path, default=Path("results/rollout_pilot_episodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/development_results_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/DEVELOPMENT_RESULTS.md"))
    args = parser.parse_args()
    report = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown(report))
    print(json.dumps({"complete": report["complete"], "episodes": report["verified_episodes"], "transitions": report["verified_transitions"],
                      "missing": report["missing"], "question_diagnostics": report["question_diagnostics"]["status"]}))


if __name__ == "__main__":
    main()
