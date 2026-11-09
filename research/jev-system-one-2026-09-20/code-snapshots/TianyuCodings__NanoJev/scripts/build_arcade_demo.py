#!/usr/bin/env python3
"""Build a compact showcase from complete recorded runs, with CPU-only replay.

No model inference, API calls, episode search, or target generation is performed.
The fixed maze and explicitly selected Snake case remain selected showcases.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random

import evaluate_model_edges_maze as maze
from evaluate_composed_maze import digest, local_questions
import snake_game as snake


MAZE_CASE = "maze:ood:50:24310922"
COLORS = {"nanojev": "#72f1b8", "jev": "#ffbd6a", "base": "#a9b6d0"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_identity(source):
    """Keep useful model lineage without copying machine-local cache paths."""
    allowed = {"engine", "model", "revision", "backend", "precision", "checkpoint", "checkpoint_sha256",
               "probability_semantics", "token_ids"}
    return {key: copy.deepcopy(value) for key, value in source["model"].items() if key in allowed}


def read_source(path, case):
    value = json.loads(path.read_text(encoding="utf-8"))
    matches = [row for row in value["episodes"] if row["id"] == case]
    require(len(matches) == 1, f"Expected exactly one case {case} in {path}")
    return value, matches[0], {"path": str(path), "sha256": sha_file(path), "case_id": case}


def probabilities(values, offered=None, normalized=False):
    require(isinstance(values, dict) and values, "Missing probability map")
    require(set(values) <= set(snake.DIRECTIONS), "Unknown direction in probability map")
    if offered is not None:
        require(set(values) == set(offered), "Probability/action coverage mismatch")
    require(all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in values.values()),
            "Invalid probability")
    if normalized:
        require(abs(math.fsum(values.values()) - 1) <= 1e-5, "Action probability mass is not one")
    return dict(values)


def maze_system(path, identity, name, detail):
    source, episode, receipt = read_source(path, MAZE_CASE)
    require(source["schema"] == "nanojev-model-edges-maze-v1", "Unsupported maze schema")
    require(source["model_role"] == "model_guided_local_edge_exploration", "Wrong maze control authority")
    require(source["protocol"]["max_steps"] == 0, "Use full-horizon maze reports")
    require(source["implementation_sha256"] == sha_file(Path(maze.__file__)), "Maze runner SHA mismatch")
    require(source["local_renderer_sha256"] == sha_file(Path(maze.__file__).with_name("evaluate_composed_maze.py")),
            "Maze local renderer SHA mismatch")
    require(source["model"]["engine"] == ("jev" if identity == "jev" else "checkpoint"), "Wrong maze model role")
    require(source["question_template"] == local_questions(), "Maze questions changed")
    initial = copy.deepcopy(episode["initial_state"])
    env = maze.MazeEnvironment(initial, source["protocol"]["window_size"])
    policy = maze.EdgeExplorer(**env.public_coordinates())
    observations, consumed = {}, set()
    for row in episode["observations"]:
        position = tuple(row["position"])
        require(position not in observations, "Duplicate static-maze observation")
        observations[position] = row
    frames = [{"position": initial["position"], "score": 0, "action": None, "probabilities": {},
               "collision": False, "decision_source": "initial", "done": env.reached_goal()}]
    collisions = 0
    for index, step in enumerate(episode["steps"]):
        require(not env.reached_goal(), "Maze trace continues after goal")
        require(step["step_index"] == index, "Maze step ordering mismatch")
        coordinate = tuple(policy.position)
        require(coordinate in observations, "Maze action has no recorded local prediction")
        observed = observations[coordinate]
        values = probabilities(observed["probabilities"], snake.DIRECTIONS)
        request = {"id": observed["id"], **env.observe()}
        require(request["state"] == observed["local_state"] and digest(request) == observed["input_sha256"],
                "Maze visible input does not match simulator position")
        if policy.needs_prediction():
            require(coordinate not in consumed, "Static-maze prediction was consumed twice")
            policy.remember_prediction(values)
            consumed.add(coordinate)
        decision = policy.choose()
        require(decision is not None and all(step[k] == v for k, v in decision.items()), "Maze policy decision differs")
        feedback = env.attempt(step["action"])
        require(all(step[k] == v for k, v in feedback.items()), "Maze collision/transition feedback differs")
        policy.observe_transition(step["action"], feedback["next_position"], feedback["collision"])
        collisions += int(feedback["collision"])
        last = index + 1 == len(episode["steps"])
        frames.append({"position": feedback["next_position"], "decision_position": list(coordinate),
                       "score": int(feedback["goal_reached"]), "action": step["action"], "probabilities": values,
                       "collision": feedback["collision"], "decision_source": step["mode"],
                       "done": feedback["goal_reached"] or last})
    require(consumed == set(observations), "Maze has unused or missing observations")
    require(len(frames) - 1 == episode["attempts"] and collisions == episode["collisions"], "Maze summary counts differ")
    require(episode["horizon"] == 2 * initial["size"] ** 2, "Maze horizon differs")
    if env.reached_goal():
        outcome = "goal"
    elif len(episode["steps"]) == episode["horizon"]:
        outcome = "horizon_exhausted"
    else:
        require(policy.choose() is None, "Maze trace ends before a valid stopping condition")
        outcome = "frontier_exhausted"
    require(outcome == episode["status"] and env.reached_goal() == episode["goal_completion"], "Maze outcome differs")
    receipt.update(role=detail, policy="Deterministic exploration", model=model_identity(source),
                   runner_sha256=source["implementation_sha256"], renderer_sha256=source["local_renderer_sha256"],
                   original_cohort_sha256=source["source_episodes_sha256"], verified_transitions=len(episode["steps"]),
                   recorded_nodes=len(consumed), replay="exact visible input, policy action and environment feedback")
    system = {"id": identity, "name": name, "detail": detail, "color": COLORS[identity],
              "probability_kind": "independent_safety",
              "summary": {"steps": episode["attempts"], "score": int(env.reached_goal()), "collisions": collisions,
                          "outcome": outcome}, "frames": frames}
    return initial, system, receipt, source["protocol"]


def build_maze(args):
    inputs = [(args.maze_trained, "nanojev", "NanoJev", "Local safety judgments + verified-edge exploration"),
              (args.maze_jev, "jev", "Jev", "API safety judgments + the same exploration code"),
              (args.maze_base, "base", "Starting NanoJev", "Existing trained checkpoint + the same exploration code")]
    systems, receipts, initial, protocol = [], [], None, None
    for path, identity, name, detail in inputs:
        state, system, receipt, actual_protocol = maze_system(path, identity, name, detail)
        if initial is None:
            initial, protocol = state, actual_protocol
        require(state == initial and actual_protocol == protocol, "Maze systems do not share initial state and controller")
        systems.append(system)
        receipts.append(receipt)
    example = {"id": MAZE_CASE, "game": "maze", "title": "50 × 50 · Find the exit",
               "subtitle": "Local model judgments. Remembered edges. A real route to the goal.",
               "size": initial["size"], "controller": "Deterministic exploration",
               "probability_kind": "independent_safety",
               "initial": {key: initial[key] for key in ("walls", "position", "goal")}, "systems": systems}
    record = {"case_id": MAZE_CASE, "selection": "Explicit fixed 50x50 showcase; complete source episodes retained.",
              "initial_state_sha256": digest(initial), "sources": receipts,
              "role_boundary": "Models provide local Boolean predictions. Shared code explores and repositions only on physically verified edges. Starting NanoJev is not untouched Qwen.",
              "probabilities": "Four independent next-step safety probabilities, without cross-direction normalization.",
              "controller": protocol}
    return example, record


def build_snake(args):
    inputs = [(args.snake_trained, "nanojev", "NanoJev", "Trained model tie-breaking + common safety and food planner"),
              (args.snake_jev, "jev", "Jev", "API tie-breaking + the same safety and food planner"),
              (args.snake_base, "base", "Untuned Qwen", "Native Qwen option probabilities + the same safety and food planner")]
    systems, receipts, initial, protocol = [], [], None, None
    for path, identity, name, detail in inputs:
        state, system, receipt, actual_protocol = snake_system(path, args.snake_case, identity, name, detail)
        if initial is None:
            initial, protocol = state, actual_protocol
        require(state == initial and actual_protocol == protocol, "Snake systems do not share initial state and controller")
        systems.append(system)
        receipts.append(receipt)
    require(len({row["original_cohort_sha256"] for row in receipts}) == 1, "Snake source cohorts differ")
    example = {"id": args.snake_case, "game": "snake", "title": f"{initial['size']} × {initial['size']} · Keep growing",
               "subtitle": "A shared safety and food planner. Model choices at the remaining forks.",
               "size": initial["size"], "controller": protocol["controller"], "probability_kind": "categorical_choice",
               "initial": {key: initial[key] for key in ("body", "food")}, "systems": systems}
    record = {"case_id": args.snake_case, "selection": "Explicitly selected composed-Snake showcase; source controller preserved for all systems.",
              "initial_state_sha256": digest(initial), "sources": receipts, "controller": protocol,
              "role_boundary": "The shared code planner filters immediate collisions and ranks static food paths. Models choose only among remaining candidates. Forced moves are code decisions, not model decisions.",
              "probabilities": "Conditional action probabilities over the actual planner-offered candidates; excluded directions have no model probability."}
    return example, record


def snake_system(path, case, identity, name, detail):
    import evaluate_composed_snake as composed
    source, episode, receipt = read_source(path, case)
    require(source["schema"] == "nanojev-composed-snake-v1", "Unsupported Snake schema: use the composed runner")
    require(source["model_role"] == "common_code_planner_with_model_tiebreak", "Wrong Snake control authority")
    require(source["implementation_sha256"] == sha_file(Path(composed.__file__)), "Snake runner SHA mismatch")
    require(source["environment_sha256"] == sha_file(Path(snake.__file__)), "Snake environment SHA mismatch")
    expected_engines = {"nanojev": {"checkpoint"}, "jev": {"jev"}, "base": {"native", "native_qwen"}}
    require(source["model"]["engine"] in expected_engines[identity], "Wrong Snake model role")
    if identity == "base":
        require(source["model"].get("model") == "Qwen/Qwen3-0.6B" and
                source["model"].get("backend") == "untrained_qwen_lm_option_logits",
                "Snake baseline must be the recorded native Qwen option-logit model")
    protocol = source["protocol"]
    controller = protocol["controller"]
    require(controller in {"greedy", "sample"} and episode["controller"] == controller, "Snake controller differs")
    require(episode["horizon"] == protocol["max_steps"], "Snake attempt limit differs")
    seed = int(composed.digest([case, protocol["seed"]])[:8], 16)
    require(episode["controller_seed"] == seed, "Snake per-episode sampling seed differs")
    rng = random.Random(seed)
    initial = copy.deepcopy(episode["initial_state"])
    snake.validate_state(initial)
    state = copy.deepcopy(initial)
    frames = [{"body": copy.deepcopy(state["body"]), "food": copy.deepcopy(state["food"]), "score": state["score"],
               "action": None, "probabilities": {}, "collision": False, "decision_source": "initial", "done": state["done"]}]
    forced, decisions, collisions = 0, 0, 0
    for index, step in enumerate(episode["steps"]):
        require(not state["done"] and index < episode["horizon"], "Snake trace continues beyond its stopping condition")
        require(step["step_index"] == index and step["state"] == composed.physical_state(state), "Snake pre-action state differs")
        plan = composed.plan_candidates(state)
        require(step["planner"] == plan and plan["offered_actions"], "Snake planner candidates differ")
        values = probabilities(step["probabilities"], plan["offered_actions"], normalized=True)
        require(list(values) == step["candidate_order"] == plan["offered_actions"], "Snake candidate order differs")
        total = sum(values.values())
        sampling = {key: value / total for key, value in values.items()}
        require(step["sampling_probabilities"] == sampling, "Snake sampling distribution differs")
        actor = "forced_move" if len(values) == 1 else "model_tiebreak"
        require(step["actor"] == actor, "Forced and model decisions are mislabeled")
        if actor == "forced_move":
            action, draw = next(iter(values)), None
            require(step["input_sha256"] is None and step["primitive_receipt"] == {}, "Forced move carries a model request")
            forced += 1
        else:
            request = {"id": f"{case}:step:{index}", **composed.render_composed_request(state, plan["offered_actions"])}
            require(composed.digest(request) == step["input_sha256"], "Snake model input hash differs")
            if controller == "greedy":
                action, draw = max(values, key=values.__getitem__), None
            else:
                draw, cumulative = rng.random(), 0.0
                action = list(sampling)[-1]
                for candidate, p in sampling.items():
                    cumulative += p
                    if draw < cumulative:
                        action = candidate
                        break
            decisions += 1
        require(step["action"] == action and step["controller_draw"] == draw, "Snake selected action or sampling RNG differs")
        next_state = snake.step(state, action)
        collision = next_state["outcome"] in {"wall_collision", "self_collision"}
        require(not collision, "Safety-filtered Snake report unexpectedly contains a colliding action")
        require(step["next_state"] == composed.physical_state(next_state), "Snake transition or food RNG differs")
        require(step["ate_food"] == (next_state["score"] > state["score"]), "Snake food event differs")
        collisions += int(collision)
        frames.append({"body": copy.deepcopy(next_state["body"]), "food": copy.deepcopy(next_state["food"]),
                       "score": next_state["score"], "action": action, "probabilities": values,
                       "collision": collision, "decision_source": actor,
                       "done": next_state["done"] or index + 1 == len(episode["steps"])})
        state = next_state
    if state["done"]:
        outcome = state["outcome"]
    elif len(episode["steps"]) == episode["horizon"]:
        outcome = "horizon_survived"
    else:
        require(not composed.plan_candidates(state)["offered_actions"], "Snake trace ends before a valid stopping condition")
        outcome = "trapped"
    require(composed.physical_state(state) == episode["final_state"], "Snake final physical state differs")
    expected = {"outcome": outcome, "full_board_win": outcome == "win", "horizon_survived": outcome == "horizon_survived",
                "survival_steps": len(frames) - 1, "food_score": state["score"], "food_collected": state["score"] - initial["score"],
                "forced_moves": forced, "model_decisions": decisions}
    require(all(episode[key] == value for key, value in expected.items()), "Snake terminal summary differs")
    frames[-1]["done"] = True
    receipt.update(role=detail, policy=controller, model=model_identity(source), runner_sha256=source["implementation_sha256"],
                   environment_sha256=source["environment_sha256"], original_cohort_sha256=source["source_episodes_sha256"],
                   verified_transitions=len(episode["steps"]), forced_moves=forced, model_decisions=decisions,
                   replay="exact planner candidates, physical states, food RNG, visible input hashes and controller sampling")
    system = {"id": identity, "name": name, "detail": detail, "color": COLORS[identity], "probability_kind": "categorical_choice",
              "summary": {"steps": len(episode["steps"]), "score": state["score"], "collisions": collisions, "outcome": outcome,
                          "forced_moves": forced, "model_decisions": decisions}, "frames": frames}
    return initial, system, receipt, protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maze-trained", type=Path, default=Path("results/model_edges_local_atomic.json"))
    parser.add_argument("--maze-jev", type=Path, default=Path("results/model_edges_jev.json"))
    parser.add_argument("--maze-base", type=Path, default=Path("results/model_edges_initial.json"))
    parser.add_argument("--snake-trained", type=Path)
    parser.add_argument("--snake-jev", type=Path)
    parser.add_argument("--snake-base", type=Path)
    parser.add_argument("--snake-case")
    parser.add_argument("--selection-protocol", type=Path, default=Path("results/arcade_selection_protocol.json"))
    parser.add_argument("--output", type=Path, default=Path("web/arcade_results.json"))
    parser.add_argument("--manifest", type=Path, default=Path("assets/arcade_data_manifest.json"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    selected = [args.snake_trained, args.snake_jev, args.snake_base, args.snake_case]
    if any(selected) and not all(selected):
        parser.error("Supply all four Snake arguments together")
    for path in (args.output, args.manifest):
        require(args.overwrite or not path.exists(), f"Output exists; pass --overwrite: {path}")
    require(args.output.resolve() != args.manifest.resolve(), "Output and manifest paths must differ")
    input_paths = [args.maze_trained, args.maze_jev, args.maze_base, args.selection_protocol,
                   args.snake_trained, args.snake_jev, args.snake_base]
    require(not {args.output.resolve(), args.manifest.resolve()} & {path.resolve() for path in input_paths if path is not None},
            "An output path would overwrite a source artifact")
    example, record = build_maze(args)
    examples, records = [example], [record]
    if all(selected):
        example, record = build_snake(args)
        examples.append(example)
        records.append(record)
    selection = None
    if args.selection_protocol.is_file():
        selection = {"path": str(args.selection_protocol), "sha256": sha_file(args.selection_protocol),
                     "protocol": json.loads(args.selection_protocol.read_text(encoding="utf-8")),
                     "verification_scope": "The supplied winner and complete selected traces are replayed. This builder does not independently rerun or select among alternate controllers."}
        if all(selected):
            frozen = selection["protocol"]
            require(all(row["original_cohort_sha256"] == frozen["cohort_sha256"] for row in records[-1]["sources"]),
                    "Snake results differ from the selection protocol's frozen cohort")
            require(records[-1]["controller"]["max_steps"] == frozen["horizon"] and
                    records[-1]["controller"]["seed"] == frozen["seed"], "Snake horizon or seed differs from selection protocol")
    output = {"schema": "nanojev-arcade-v1", "examples": examples}
    raw = (json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    manifest = {"schema": "nanojev-arcade-manifest-v1", "builder_sha256": sha_file(Path(__file__)),
                "output": {"path": str(args.output), "sha256": hashlib.sha256(raw).hexdigest()},
                "examples": records, "selection_protocol": selection,
                "frame_semantics": "Frame zero is initial state. Every subsequent frame follows one actual attempt, including collisions and the final outcome. Probabilities describe the decision that produced that frame. done marks playback completion, including a live Snake at horizon or trapped, not necessarily a full-board win.",
                "playback": "Environment-step playback; not a model latency race.",
                "selection_scope": "Selected showcase cases and controllers; not an unbiased benchmark subset.",
                "source_mutations": False, "new_model_calls": 0, "new_api_calls": 0}
    for path in (args.output, args.manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "manifest": str(args.manifest), "examples": len(examples),
                      "verified_transitions": sum(len(system["frames"]) - 1 for item in examples for system in item["systems"])}))


if __name__ == "__main__":
    main()
