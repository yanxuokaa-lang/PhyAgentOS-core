#!/usr/bin/env python3
"""Build a separate three-system replay with a real native-Qwen maze run.

The original arcade and media are read-only inputs. All selected source episodes
are replayed on CPU; no API call, model forward, or episode search is performed.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import build_arcade_demo as arcade
import evaluate_model_edges_maze as maze
from evaluate_composed_maze import digest, local_questions


ORDER = ("jev", "nanojev", "base")
QWEN_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frame_hash(system):
    raw = json.dumps(system["frames"], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def load_cohort(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(len({row["id"] for row in rows}) == len(rows), "Duplicate frozen cohort IDs")
    return {row["id"]: row for row in rows}


def native_maze(path, frozen, controller_protocol, input_path, original_cohort_sha):
    source, episode, receipt = arcade.read_source(path, arcade.MAZE_CASE)
    require(source["schema"] == "nanojev-model-edges-maze-v1", "Unsupported native maze schema")
    require(source["model_role"] == "model_guided_local_edge_exploration", "Native maze control authority differs")
    require(source["source_episodes_sha256"] == arcade.sha_file(input_path), "Native input episode file SHA differs")
    require(source["source_cohort_sha256"] == [original_cohort_sha], "Native input does not reference the frozen original cohort")
    require(source["selected_episode_ids"] == [arcade.MAZE_CASE] and len(source["episodes"]) == 1,
            "Native run must preserve the explicitly selected single case")
    model = source["model"]
    require(model.get("engine") == "native" and model.get("model") == "Qwen/Qwen3-0.6B" and
            model.get("revision") == QWEN_REVISION and model.get("backend") == "untrained_qwen_lm_option_logits",
            "The maze baseline must be the recorded original Qwen model, not a trained checkpoint")
    require(source["implementation_sha256"] == arcade.sha_file(Path(maze.__file__)), "Frozen maze implementation SHA differs")
    renderer = Path(maze.__file__).with_name("evaluate_composed_maze.py")
    require(source["local_renderer_sha256"] == arcade.sha_file(renderer), "Native maze renderer SHA differs")
    runner = Path(source["native_runner"])
    require(runner.resolve().parent == Path(__file__).resolve().parent and runner.suffix == ".py", "Native runner is outside the scripts directory")
    require(source["native_runner_sha256"] == arcade.sha_file(runner), "Native wrapper SHA differs")
    predictor = Path(maze.__file__).with_name("evaluate_native_qwen_navigation.py")
    require(model.get("native_predictor_sha256") == arcade.sha_file(predictor), "Native LM predictor SHA differs")
    require(model.get("decision_adapter") == "boolean_as_native_option_choice" and model.get("token_ids") == {"A": 32, "B": 33},
            "Native Boolean adapter or vocabulary-token mapping differs")
    require(source["execution"].get("autoregressive_decode_steps") == 0 and source["execution"].get("generated_tokens") == 0,
            "Native maze report includes generated answer tokens")
    require(source["protocol"] == controller_protocol, "Native and trained maze controllers differ")
    require(source["question_template"] == local_questions(), "Native maze question template differs")
    initial = copy.deepcopy(episode["initial_state"])
    require(initial == frozen["initial_state"], "Native maze does not start from the frozen case")
    require(episode["horizon"] == 2 * initial["size"] ** 2 and source["protocol"]["max_steps"] == 0,
            "Native maze must use the same complete attempt budget")
    env = maze.MazeEnvironment(initial, source["protocol"]["window_size"])
    policy = maze.EdgeExplorer(**env.public_coordinates())
    observations = {}
    native_receipts = 0
    for row in episode["observations"]:
        coordinate = tuple(row["position"])
        require(coordinate not in observations, "Repeated native prediction for a static maze node")
        observations[coordinate] = row
        native_receipts += verify_native_probabilities(row)
    consumed, collisions = set(), 0
    frames = [{"position": initial["position"], "score": 0, "action": None, "probabilities": {},
               "collision": False, "decision_source": "initial", "done": env.reached_goal()}]
    for index, step in enumerate(episode["steps"]):
        require(index < episode["horizon"] and not env.reached_goal(), "Native maze continues after its stopping condition")
        require(step["step_index"] == index, "Native maze step ordering differs")
        coordinate = tuple(policy.position)
        require(coordinate in observations, "Native maze action lacks a recorded prediction")
        observed = observations[coordinate]
        values = arcade.probabilities(observed["probabilities"], maze.DIRECTIONS, normalized=False)
        request = {"id": observed["id"], **env.observe()}
        require(observed["local_state"] == request["state"] and observed["input_sha256"] == digest(request),
                "Native visible request does not match the simulated state")
        if policy.needs_prediction():
            require(coordinate not in consumed, "Native maze observation is consumed twice")
            policy.remember_prediction(values)
            consumed.add(coordinate)
        decision = policy.choose()
        require(decision is not None and all(step[key] == value for key, value in decision.items()),
                "Native maze controller decision differs")
        feedback = env.attempt(step["action"])
        require(all(step[key] == value for key, value in feedback.items()), "Native maze physical feedback differs")
        policy.observe_transition(step["action"], feedback["next_position"], feedback["collision"])
        collisions += int(feedback["collision"])
        frames.append({"position": feedback["next_position"], "decision_position": list(coordinate),
                       "score": int(feedback["goal_reached"]), "action": step["action"], "probabilities": values,
                       "collision": feedback["collision"], "decision_source": step["mode"],
                       "done": feedback["goal_reached"] or index + 1 == len(episode["steps"])})
    require(consumed == set(observations), "Native maze has unused or missing recorded predictions")
    require(len(episode["steps"]) == episode["attempts"] and collisions == episode["collisions"], "Native maze counts differ")
    if env.reached_goal():
        outcome = "goal"
    elif len(episode["steps"]) == episode["horizon"]:
        outcome = "horizon_exhausted"
    else:
        require(policy.choose() is None, "Native maze is truncated before a stopping condition")
        outcome = "frontier_exhausted"
    require(episode["status"] == outcome and episode["goal_completion"] == env.reached_goal(), "Native maze final outcome differs")
    system = {"id": "base", "name": "Untuned Qwen", "detail": "Native Qwen safety probabilities + the same verified-edge exploration",
              "color": arcade.COLORS["base"], "probability_kind": "independent_safety",
              "summary": {"steps": len(episode["steps"]), "score": int(env.reached_goal()), "collisions": collisions, "outcome": outcome},
              "frames": frames}
    receipt.update(system_id="base", role=system["detail"], model=arcade.model_identity(source),
                   model_adapter=model.get("decision_adapter"), policy="Deterministic exploration",
                   runner_sha256=source["implementation_sha256"], native_runner=str(runner), native_runner_sha256=source["native_runner_sha256"],
                   native_predictor_sha256=model["native_predictor_sha256"],
                   original_weight_files_sha256_as_recorded=model.get("original_weight_files_sha256"),
                   renderer_sha256=source["local_renderer_sha256"], source_episode_file_sha256=source["source_episodes_sha256"],
                   original_cohort_sha256_as_recorded=source.get("source_cohort_sha256"),
                   initial_state_sha256=digest(initial), frame_json_sha256=frame_hash(system),
                   verified_transitions=len(episode["steps"]), recorded_nodes=len(consumed), final_outcome=outcome,
                   native_receipts_verified=native_receipts, native_softmax_probability_tolerance=2e-6,
                   replay="Exact visible requests, policy choices, physical feedback and final stopping condition")
    return system, receipt


def verify_native_probabilities(observed):
    from evaluate_native_qwen_navigation import build_prompt
    receipts = observed["primitive_receipts"]
    require(set(receipts) == set(local_questions()), "Native receipt coverage differs")
    for qid, question in local_questions().items():
        receipt = receipts[qid]
        require(receipt.get("backend") == "untrained_qwen_lm_option_logits" and
                receipt.get("decision_adapter") == "boolean_as_native_option_choice", "Native receipt backend differs")
        require(receipt["candidate_to_token"] == {"false": {"text": "A", "id": 32}, "true": {"text": "B", "id": 33}},
                "Native false/true option mapping differs")
        logits = receipt["native_option_logits"]
        unconditional = receipt["native_option_unconditional_probs"]
        require(set(logits) == set(unconditional) == {"false", "true"}, "Native receipt options differ")
        require(all(type(value) in (int, float) and math.isfinite(value) for value in logits.values()), "Invalid native logits")
        require(all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1 for value in unconditional.values()),
                "Invalid native vocabulary probability")
        offset = max(logits.values())
        weights = {key: math.exp(value - offset) for key, value in logits.items()}
        p_true = weights["true"] / math.fsum(weights.values())
        mass = math.fsum(unconditional.values())
        require(0 < mass <= 1 + 1e-5 and math.isclose(mass, receipt["offered_token_mass"], rel_tol=1e-12, abs_tol=1e-12),
                "Native offered-token mass differs")
        observed_p = observed["probabilities"][qid.removeprefix("clear_")]
        require(abs(observed_p - p_true) <= 2e-6 and abs(observed_p - unconditional["true"] / mass) <= 2e-6,
                "Recorded safety probability differs from native conditional logits")
        public = {"state": observed["local_state"], "questions": {"action": {"type": "choice",
                  "instructions": question["instructions"], "criteria": {key: question["criteria"][key] for key in ("false", "true")}}}}
        prompt, _ = build_prompt(public)
        require(hashlib.sha256(prompt.encode()).hexdigest() == receipt["prompt_sha256"], "Native complete prompt hash differs")
        require(type(receipt["prompt_tokens"]) is int and receipt["prompt_tokens"] > 0, "Invalid recorded prompt length")
    return len(receipts)


def build(args):
    original_bytes = args.arcade_data.read_bytes()
    original = json.loads(original_bytes)
    manifest = json.loads(args.arcade_manifest.read_text(encoding="utf-8"))
    require(original["schema"] == "nanojev-arcade-v1", "Unsupported original arcade format")
    require(manifest["output"]["sha256"] == hashlib.sha256(original_bytes).hexdigest(), "Original arcade data hash differs")
    require(manifest["builder_sha256"] == arcade.sha_file(Path(arcade.__file__)), "Original arcade builder changed")
    maze_cohort, snake_cohort = load_cohort(args.maze_cohort), load_cohort(args.snake_cohort)
    native_cohort = load_cohort(args.native_maze_cohort)
    require(set(native_cohort) == {arcade.MAZE_CASE} and
            native_cohort[arcade.MAZE_CASE]["initial_state"] == maze_cohort[arcade.MAZE_CASE]["initial_state"],
            "Native input is not the same frozen 50x50 initial state")
    require(native_cohort[arcade.MAZE_CASE]["source_cohort_sha256"] == arcade.sha_file(args.maze_cohort),
            "Native single-case provenance differs from the original cohort")
    examples, audits, protected = [], [], {args.arcade_data.resolve(), args.arcade_manifest.resolve(), args.maze_native.resolve(),
                                          args.maze_cohort.resolve(), args.native_maze_cohort.resolve(),
                                          args.snake_cohort.resolve(), Path(arcade.__file__).resolve()}
    for old in original["examples"]:
        matches = [item for item in manifest["examples"] if item["case_id"] == old["id"]]
        require(len(matches) == 1, "Original arcade manifest case mismatch")
        old_audit = matches[0]
        require(len(old["systems"]) == len(old_audit["sources"]) == 3, "Expected three recorded systems")
        require({system["id"] for system in old["systems"]} == set(ORDER), "Unknown recorded system identity")
        example = copy.deepcopy(old)
        systems, sources, initial = {}, {}, None
        for system, source in zip(old["systems"], old_audit["sources"]):
            identity, path = system["id"], Path(source["path"])
            protected.add(path.resolve())
            require(arcade.sha_file(path) == source["sha256"], "An original source report changed")
            if old["game"] == "maze" and identity == "base":
                continue
            if old["game"] == "maze":
                state, fresh, receipt, protocol = arcade.maze_system(path, identity, system["name"], system["detail"])
                frozen = maze_cohort[old["id"]]
            elif old["game"] == "snake":
                state, fresh, receipt, protocol = arcade.snake_system(path, old["id"], identity, system["name"], system["detail"])
                frozen = snake_cohort[old["id"]]
            else:
                raise ValueError("Unsupported original game")
            require(state == frozen["initial_state"], "A source differs from the frozen initial state")
            require(fresh == system, "Replayed frames differ from the retained original arcade system")
            require(protocol == old_audit["controller"], "A retained controller differs")
            if initial is None:
                initial = state
            require(initial == state, "Compared systems have different initial states")
            systems[identity] = copy.deepcopy(system)
            sources[identity] = {**receipt, "system_id": identity, "initial_state_sha256": digest(state),
                                 "frame_json_sha256": frame_hash(system), "frames_unchanged_from_original_arcade": True,
                                 "final_outcome": system["summary"]["outcome"]}
        if old["game"] == "maze":
            require(old["id"] == arcade.MAZE_CASE, "The fixed maze case changed")
            native, native_receipt = native_maze(args.maze_native, maze_cohort[old["id"]], old_audit["controller"],
                                                 args.native_maze_cohort, arcade.sha_file(args.maze_cohort))
            require({key: initial[key] for key in ("walls", "position", "goal")} == old["initial"], "Maze public initial state differs")
            systems["base"], sources["base"] = native, native_receipt
            role = "All three models provide independent local safety probabilities. The same code explores and remembers verified edges; the baseline is original Qwen, not Starting NanoJev."
        else:
            require({key: initial[key] for key in ("body", "food")} == old["initial"], "Snake public initial state differs")
            role = old_audit["role_boundary"]
        example["systems"] = [systems[identity] for identity in ORDER]
        examples.append(example)
        audits.append({"case_id": old["id"], "game": old["game"], "initial_state_sha256": digest(initial),
                       "controller": old_audit["controller"], "role_boundary": role,
                       "probabilities": old_audit["probabilities"], "selection": old_audit["selection"],
                       "sources": [sources[identity] for identity in ORDER]})
    require({item["game"] for item in examples} == {"maze", "snake"} and len(examples) == 2, "Expected one maze and one Snake case")
    return {"schema": "nanojev-arcade-v1", "examples": examples}, audits, manifest, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arcade-data", type=Path, default=Path("web/arcade_results.json"))
    parser.add_argument("--arcade-manifest", type=Path, default=Path("assets/arcade_data_manifest.json"))
    parser.add_argument("--maze-native", type=Path, default=Path("results/model_edges_native.json"))
    parser.add_argument("--maze-cohort", type=Path, default=Path("results/rollout_pilot_episodes.jsonl"))
    parser.add_argument("--native-maze-cohort", type=Path, default=Path("results/side_by_side_maze_episode.jsonl"))
    parser.add_argument("--snake-cohort", type=Path, default=Path("results/arcade_snake_cohort.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("web/side_by_side_results.json"))
    parser.add_argument("--manifest", type=Path, default=Path("assets/side_by_side_data_manifest.json"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for path in (args.output, args.manifest):
        require(args.overwrite or not path.exists(), f"Output exists; pass --overwrite: {path}")
    require(args.output.resolve() != args.manifest.resolve(), "Output and manifest paths must differ")
    before = {path: arcade.sha_file(path) for path in (args.arcade_data, args.arcade_manifest)}
    output, audits, original_manifest, protected = build(args)
    require(not {args.output.resolve(), args.manifest.resolve()} & protected, "An output would overwrite an input")
    raw = (json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    manifest = {"schema": "nanojev-side-by-side-data-v1", "builder_sha256": arcade.sha_file(Path(__file__)),
                "reused_arcade_builder_sha256": arcade.sha_file(Path(arcade.__file__)),
                "output": {"path": str(args.output), "sha256": hashlib.sha256(raw).hexdigest()},
                "original_arcade": {"data_path": str(args.arcade_data), "data_sha256": before[args.arcade_data],
                                    "manifest_path": str(args.arcade_manifest), "manifest_sha256": before[args.arcade_manifest]},
                "cohorts": {str(path): arcade.sha_file(path) for path in (args.maze_cohort, args.native_maze_cohort, args.snake_cohort)},
                "system_order": list(ORDER), "examples": audits, "selection_protocol": original_manifest["selection_protocol"],
                "frame_semantics": original_manifest["frame_semantics"], "playback": original_manifest["playback"],
                "verification": {"all_selected_source_transitions_replayed": True,
                                 "retained_systems_have_identical_serialized_frames": 5,
                                 "maze_baseline_replaced_by_new_native_measurement": True,
                                 "verified_transitions": sum(source["verified_transitions"] for item in audits for source in item["sources"]),
                                 "original_arcade_files_unchanged": True, "new_model_calls": 0, "new_api_calls": 0}}
    for path, expected in before.items():
        require(arcade.sha_file(path) == expected, "Original arcade changed during this build")
    for path in (args.output, args.manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "examples": len(output["examples"]), **manifest["verification"]}))


if __name__ == "__main__":
    main()
