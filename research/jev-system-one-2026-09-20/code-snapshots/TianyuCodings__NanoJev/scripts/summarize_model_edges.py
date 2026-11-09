#!/usr/bin/env python3
"""Verify saved per-node predictions by controller replay, then report all cases.

No inference, API request, new episode selection, or training is performed.
The main comparison uses 2*size^2 attempts. The original 128-attempt pilot remains
an independently labeled archive and is replayed when its files are present.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import evaluate_model_edges_maze as controller
from evaluate_composed_maze import digest, local_questions


SYSTEMS = [
    ("initial", "Initial NanoJev", "checkpoint"),
    ("local_atomic", "Local-atomic NanoJev", "checkpoint"),
    ("jev", "Jev", "jev"),
    ("reference", "Perfect local geometry", "reference"),
    ("constant", "Constant 0.5 perception", "constant"),
]


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def same_numbers(actual, expected, context):
    if set(actual) != set(expected):
        raise ValueError(f"Summary keys differ: {context}")
    for key, value in actual.items():
        reference = expected[key]
        if isinstance(value, float) or isinstance(reference, float):
            if value is None or reference is None or not math.isclose(value, reference, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Derived numeric value differs: {context}/{key}")
        elif value != reference:
            raise ValueError(f"Derived value differs: {context}/{key}")


class RecordedEngine:
    """Return saved predictions only for an exact recorded request; consume once."""

    def __init__(self, source):
        self.template = source["question_template"]
        self.rows, self.used = {}, set()
        self.native_receipts_verified = 0
        for episode in source["episodes"]:
            for row in episode["observations"]:
                if row["id"] in self.rows:
                    raise ValueError("Duplicate recorded observation ID")
                self.rows[row["id"]] = row

    def predict(self, payload, **kwargs):
        if set(payload) != {"states"} or not isinstance(payload["states"], list):
            raise ValueError("Unexpected replay payload")
        returned = []
        for request in payload["states"]:
            if set(request) != {"id", "state", "questions"}:
                raise ValueError("Model request contains unrecorded fields")
            identity = request["id"]
            if identity not in self.rows or identity in self.used:
                raise ValueError("Replay requested a missing or already consumed node")
            saved = self.rows[identity]
            if request["state"] != saved["local_state"] or request["questions"] != self.template:
                raise ValueError("Recorded state or questions differ from the replay request")
            if digest(request) != saved["input_sha256"]:
                raise ValueError("Recorded request hash differs from the replay request")
            answers = {}
            for action in controller.DIRECTIONS:
                qid = "clear_" + action
                p = saved["probabilities"][action]
                if type(p) not in (float, int) or not math.isfinite(p) or not 0 <= p <= 1:
                    raise ValueError("Invalid recorded Boolean probability")
                receipt = copy.deepcopy(saved.get("primitive_receipts", {}).get(qid, {}))
                if receipt.get("native_probabilities") is not None:
                    native = receipt["native_probabilities"]
                    if set(native) != {"false", "true"} or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in native.values()):
                        raise ValueError("Invalid embedded native Boolean receipt")
                    total = math.fsum(native.values())
                    if total <= 0 or abs(native["true"] / total - p) > 1e-12:
                        raise ValueError("Stored prediction is not the receipt's normalized rounded proxy")
                    if abs(receipt["native_sum"] - total) > 1e-12:
                        raise ValueError("Embedded native sum disagrees")
                    # Match the worker's insertion-order JSON input hash. The
                    # documented local renderer produces ordinary ASCII text.
                    api_input = {"model": "typesafe-ai/jev", "state": request["state"], "questions": request["questions"]}
                    api_sha = hashlib.sha256(json.dumps(api_input, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
                    if receipt["source_input_sha256"] != api_sha or not isinstance(receipt["source_api_call_id"], str):
                        raise ValueError("Embedded API input identity disagrees with the visible request")
                    self.native_receipts_verified += 1
                answers[qid] = {"type": "boolean", "probabilities": {"false": 1 - p, "true": p}, "p_true": p, **receipt}
            self.used.add(identity)
            returned.append({"id": identity, "answers": answers})
        return {"states": returned, "execution": {"forward_passes": 0, "network_model_calls": 0}}


def verify_source(path, source, sha, episodes, episode_sha, max_steps):
    implementation = hashlib.sha256(Path(controller.__file__).read_bytes()).hexdigest()
    renderer = hashlib.sha256(Path(controller.__file__).with_name("evaluate_composed_maze.py").read_bytes()).hexdigest()
    if source["implementation_sha256"] != implementation or source["local_renderer_sha256"] != renderer:
        raise ValueError("Execution implementation or renderer SHA differs from the available frozen code")
    if source["source_episodes_sha256"] != episode_sha:
        raise ValueError("Frozen episode-file SHA mismatch")
    if source["selected_episode_ids"] != [row["id"] for row in episodes]:
        raise ValueError("Episode selection or order differs from the frozen cohort")
    if source["model_role"] != "model_guided_local_edge_exploration" or source["protocol"]["max_steps"] != max_steps:
        raise ValueError("Wrong controller role or horizon protocol")
    if source["question_template"] != local_questions():
        raise ValueError("Question template differs from the frozen implementation")
    if len(source["episodes"]) != len(episodes):
        raise ValueError("Missing or extra episode")
    for row, original in zip(source["episodes"], episodes):
        if row["id"] != original["id"] or row["initial_state"] != original["initial_state"]:
            raise ValueError("Initial state differs from the frozen cohort")
        expected_horizon = max_steps or 2 * original["size"] ** 2
        if row["horizon"] != expected_horizon:
            raise ValueError("Episode attempt limit differs from the protocol")
    recorded = RecordedEngine(source)
    replay = controller.run_exploration(episodes, recorded, window_size=source["protocol"]["window_size"],
                                       max_steps=max_steps, batch_states=2, batch_questions=0)
    if recorded.used != set(recorded.rows):
        raise ValueError("Some recorded observation was not consumed by replay")
    if replay["protocol"] != source["protocol"] or replay["audit_inputs_sha256"] != source["audit_inputs_sha256"]:
        raise ValueError("Replay protocol or ordered input hash differs")
    cases = []
    for old, new in zip(source["episodes"], replay["episodes"]):
        # These include every action, model probability, transition feedback,
        # collision, receipt, memory edge and end status, with exact equality.
        exact_old = {key: value for key, value in old.items() if key != "atomic_metrics"}
        exact_new = {key: value for key, value in new.items() if key != "atomic_metrics"}
        if exact_old != exact_new:
            raise ValueError(f"Recorded trajectory differs from controller replay: {old['id']}")
        same_numbers(old["atomic_metrics"], new["atomic_metrics"], old["id"])
        final = copy.deepcopy(old["initial_state"])
        if old["steps"]:
            final["position"] = old["steps"][-1]["next_position"]
        if old["goal_completion"] != (final["position"] == final["goal"]):
            raise ValueError("Final reconstructed simulator state disagrees with completion")
        cases.append({**{key: old[key] for key in ("id", "split", "size", "status", "goal_completion", "horizon", "attempts",
                       "successful_moves", "collisions", "probe_count", "fallback_count", "visited_cells", "revisited_cell_entries", "atomic_metrics")},
                      "initial_state_sha256": digest(old["initial_state"]), "final_state_sha256": digest(final)})
    same_numbers(source["summary"], replay["summary"], str(path))
    return {"status": "verified", "source": path.name, "source_sha256": sha,
            "implementation_sha256": implementation, "local_renderer_sha256": renderer,
            "model": source["model"], "protocol": source["protocol"], "cases": cases,
            "summary": source["summary"], "execution_as_recorded": source["execution"],
            "verification": {"recorded_engine_replay": True, "all_actions_and_feedback_exact": True,
                             "all_visible_inputs_and_questions_exact": True, "all_recorded_nodes_consumed_once": len(recorded.used),
                             "native_receipt_proxy_and_input_hash_checks": recorded.native_receipts_verified,
                             "api_journal_or_provider_receipt_authenticated": False,
                             "final_state_reconstructed_from_complete_feedback": True,
                             "new_model_forwards": 0, "new_api_calls": 0,
                             "derived_float_metric_tolerance": {"absolute": 1e-12, "relative": 1e-12}}}


def build(args):
    raw = args.episodes.read_bytes()
    all_episodes = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    episodes = [row for row in all_episodes if row["game"] == "scaled_maze" and row["split"] in {"test", "ood"}]
    if len(episodes) != 3 or len({row["id"] for row in episodes}) != 3:
        raise ValueError("Expected the frozen three-maze cohort")
    episode_sha = hashlib.sha256(raw).hexdigest()
    report = {"schema_version": "nanojev-model-edge-comparison-v1", "complete": False,
              "episode_source": {"path": str(args.episodes), "sha256": episode_sha},
              "case_ids": [row["id"] for row in episodes], "full_horizon": {}, "pilot_128": {}, "errors": [],
              "metric_scope": {"main_horizon": "2*size^2 attempts, including collisions",
                               "pilot_horizon": "128 attempts; original reports retained with model_edges_128_ prefix",
                               "atomic_metrics": "On each controller's own first-visit states, not a shared model-independent question cohort.",
                               "brier": "Scalar Bernoulli squared error, not two-class summed Brier.",
                               "constant_control": "p(true)=0.5 for every local proposition; the same deterministic exploration code still selects actions.",
                               "reference_control": "Perfect local geometry predictions with the same exploration policy; no full-map BFS route.",
                               "failure_handling": "Every selected episode is retained; missing or invalid sources are never assigned fabricated outcomes."}}
    for section, prefix, horizon in [("full_horizon", "model_edges_", 0), ("pilot_128", "model_edges_128_", 128)]:
        protocols = []
        for key, label, engine in SYSTEMS:
            path = args.results_dir / f"{prefix}{key}.json"
            entry = {"label": label, "status": "missing", "source": path.name}
            if path.is_file():
                try:
                    source, sha = load(path)
                    if source["model"]["engine"] != engine:
                        raise ValueError("Model/control engine identity mismatch")
                    entry = {"label": label, **verify_source(path, source, sha, episodes, episode_sha, horizon)}
                    protocols.append(entry["protocol"])
                except (ValueError, TypeError, KeyError, RuntimeError) as error:
                    entry.update(status="invalid", error=str(error))
                    report["errors"].append({"source": path.name, "error": str(error)})
            report[section][key] = entry
        if protocols and any(protocol != protocols[0] for protocol in protocols[1:]):
            report["errors"].append({"section": section, "error": "Cross-system controller protocols differ"})
    report["complete"] = not report["errors"] and all(row["status"] == "verified" for row in report["full_horizon"].values())
    report["pilot_archive_complete"] = all(row["status"] == "verified" for row in report["pilot_128"].values())
    report["status"] = "complete" if report["complete"] else "invalid" if report["errors"] else "pending"
    report["summarizer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return report


def markdown(report):
    lines = ["# Model-guided edge exploration: measured results", "",
             "The model supplies four local safety probabilities. Code orders untried edges, records actual collision feedback, and repositions using only physically verified open edges. The policy receives no wall map, full-map solver, or hidden route. Every selected maze is retained.", "",
             "The main comparison uses **2 × size² attempts**, including collisions: 128 for 8×8, 512 for 16×16, and 5,000 for 50×50. It supplements the original 128-attempt integration pilot on the same initial states; both sets remain available. See the [frozen cases](../results/rollout_pilot_episodes.jsonl), [original case-selection protocol](../results/rollout_pilot_protocol.json), and [replay audit](../results/model_edges_summary.json).", "",
             "## System roles", "",
             "Initial NanoJev is the existing trained checkpoint, not untouched Qwen. Local-atomic NanoJev adds focused local-question training. Jev supplies its recorded API probabilities. **Perfect local geometry** is an exact local parser using the same exploration controller, not a full-map BFS planner. **Constant 0.5 perception** always returns 0.5 for each Boolean proposition; it is not uniform random action selection.", "",
             "All systems use the same threshold and code: among untried edges with p≥0.5, prioritize goal Manhattan distance, visits, then probability; otherwise physically probe the highest-ranked low-probability edge. Known-open graph search is used only to reach a remaining frontier. Probes and collisions count toward the attempt limit."]
    for section, heading in [("full_horizon", "Full-horizon results"), ("pilot_128", "Original 128-attempt pilot, retained")]:
        lines += ["", "## " + heading, "", "Each cell is **attempts / collisions / status**. `goal` means completed; `limit` means the attempt budget expired.", "",
                  "| Case ID | Initial | Local atomic | Jev | Perfect local | Constant 0.5 |", "|---|---:|---:|---:|---:|---:|"]
        for identity in report["case_ids"]:
            cells = []
            for key, _, _ in SYSTEMS:
                source = report[section][key]
                if source["status"] != "verified":
                    cells.append(source["status"])
                    continue
                row = next(row for row in source["cases"] if row["id"] == identity)
                status = {"goal": "goal", "horizon_exhausted": "limit", "frontier_exhausted": "exhausted"}.get(row["status"], row["status"])
                cells.append(f"{row['attempts']} / {row['collisions']} / {status}")
            lines.append("| `" + identity + "` | " + " | ".join(cells) + " |")
        links = [f"[{entry['label']}](../results/{entry['source']})" for entry in report[section].values() if entry["status"] == "verified"]
        lines += ["", "Source reports: " + (", ".join(links) if links else "pending") + "."]
        if section == "full_horizon":
            lines += ["", "| System | Completed | Total attempts | Successful moves | Collisions |",
                      "|---|---:|---:|---:|---:|"]
            for key, label, _ in SYSTEMS:
                entry = report[section][key]
                if entry["status"] == "verified":
                    row = entry["summary"]
                    lines.append(f"| {label} | {row['goal_completed']}/3 | {row['attempts']} | {row['successful_moves']} | {row['collisions']} |")
                else:
                    lines.append(f"| {label} | {entry['status']} | — | — | — |")
            initial, local = report[section]["initial"], report[section]["local_atomic"]
            if initial["status"] == local["status"] == "verified":
                first, trained = initial["summary"], local["summary"]
                lines += ["", f"Local-atomic NanoJev records {trained['collisions']} collisions versus {first['collisions']} for Initial NanoJev, but {trained['attempts']} total attempts versus {first['attempts']}. In this cohort, fewer collisions do not translate into better overall navigation efficiency."]
    reference, constant = report["full_horizon"]["reference"], report["full_horizon"]["constant"]
    if reference["status"] == constant["status"] == "verified":
        ref, const = reference["summary"], constant["summary"]
        lines += ["", f"The full-horizon controls complete {ref['goal_completed']}/3 with perfect local predictions and {const['goal_completed']}/3 with constant perception. Their total attempts are {ref['attempts']} and {const['attempts']}; collisions are {ref['collisions']} and {const['collisions']}. Constant-perception completion shows that code exploration contributes substantially. Model value must be assessed through actual efficiency and error reduction, not completion alone."]
    lines += ["", "## Interpretation and verification", "",
              "Each controller visits different states. Its recorded atomic accuracy, scalar Brier, and NLL therefore describe its own visited-state distribution; they are not a direct comparison on identical questions. Use a separate fixed question cohort for model probability quality. This small three-maze study also does not establish generalization to arbitrary 50×50 maps.", "",
              "The verifier reconstructs each original request from the simulator and uses a `RecordedEngine` to return only that node's saved probabilities. It checks state/question hashes, consumes every saved node once, and reproduces all actions, collisions, memory edges, and final states. It verifies source, renderer, and implementation hashes and embedded API-input/proxy consistency. It does not rerun inference or independently authenticate private API journals.", "",
              "```bash", "python scripts/summarize_model_edges.py", "```", "",
              "This command reads tracked artifacts and rebuilds the report without model or API calls. The earlier [direct-action pilot](DEVELOPMENT_RESULTS.md) asked models for whole-map actions. The separate `composed_*` diagnostic used full-map BFS with model judgments scored separately; neither should be conflated with this probability-guided exploration."]
    if not report["complete"]:
        lines += ["", "Status: the full comparison is pending or invalid; missing entries are not results. Inspect the JSON audit before drawing a system ranking."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--episodes", type=Path, default=Path("results/rollout_pilot_episodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/model_edges_summary.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/MODEL_EDGE_RESULTS.md"))
    args = parser.parse_args()
    report = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown(report))
    print(json.dumps({"status": report["status"], "full_complete": report["complete"],
                      "pilot_archive_complete": report["pilot_archive_complete"], "errors": report["errors"]}))
    raise SystemExit(0 if report["complete"] else 1 if report["errors"] else 2)


if __name__ == "__main__":
    main()
