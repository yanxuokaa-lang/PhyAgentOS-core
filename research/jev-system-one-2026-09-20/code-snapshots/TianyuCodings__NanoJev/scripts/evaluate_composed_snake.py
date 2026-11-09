#!/usr/bin/env python3
"""Common safety/food planner with model Choice tie-breaking in Snake.

The same code planner filters immediate collisions and ranks static paths to
the currently visible food for every engine. Models choose only when at least
two candidates remain. This is not a standalone learned Snake controller.
"""

import argparse
from collections import Counter, deque
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import time

import snake_game as snake


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def food_distance(next_body, food, size):
    """Static BFS; the next tail stays blocked, a conservative approximation."""
    start, target = tuple(next_body[0]), tuple(food)
    if start == target:
        return 0
    blocked = set(map(tuple, next_body[1:]))
    queue, seen = deque([(start, 0)]), {start}
    while queue:
        position, distance = queue.popleft()
        for dr, dc in snake.DIRECTIONS.values():
            cell = position[0] + dr, position[1] + dc
            if cell in seen or cell in blocked or not all(0 <= x < size for x in cell):
                continue
            if cell == target:
                return distance + 1
            seen.add(cell)
            queue.append((cell, distance + 1))
    return None


def plan_candidates(state):
    """Planning uses current food, actual next body, and immediate collision only."""
    snake.validate_state(state)
    safe, distances = [], {}
    for action in snake.valid_actions(state):
        after = snake.step(state, action)
        if after["done"] and after["outcome"] != "win":
            continue
        safe.append(action)
        # Never inspect after['food'] or after['rng_state']: they can be future information.
        remaining = food_distance(after["body"], state["food"], state["size"])
        distances[action] = None if remaining is None else remaining + 1
    reachable = [action for action in safe if distances[action] is not None]
    offered = ([action for action in reachable if distances[action] == min(distances[a] for a in reachable)]
               if reachable else list(safe))
    return {"safe_actions": safe, "offered_actions": offered, "static_total_distances": distances,
            "mode": "shortest_static_food_path" if reachable else "all_safe_no_static_food_path"}


def render_composed_request(state, offered_actions):
    """Stable model input: physical state and one dynamic Choice; no planner scores."""
    base = snake.render_request(state)
    candidates = base["questions"]["action"]["criteria"]
    if len(offered_actions) < 2 or len(set(offered_actions)) != len(offered_actions) or not set(offered_actions) <= set(candidates):
        raise ValueError("A model Choice requires at least two distinct non-reverse candidates")
    question = {"type": "choice", "instructions":
        "Choose the offered move that best preserves space for subsequent movement while collecting the currently visible food. "
        "A common code planner has selected the offered candidates. Use only the current physical state; tied moves are equivalent.",
        "criteria": {action: candidates[action] for action in offered_actions}}
    return {"state": base["state"], "questions": {"action": question}}


def physical_state(state):
    return {key: copy.deepcopy(state[key]) for key in
            ("game", "size", "body", "direction", "food", "done", "outcome", "score", "steps")}


class UniformChoice:
    """Information-free chooser, conditional on the common planner's candidates."""

    def predict(self, payload, **kwargs):
        result = []
        for row in payload["states"]:
            candidates = row["questions"]["action"]["criteria"]
            result.append({"id": row["id"], "answers": {"action": {"type": "choice",
                "probabilities": {action: 1 / len(candidates) for action in candidates}}}})
        return {"states": result, "execution": {"forward_passes": 0, "network_model_calls": 0}}


def validate_choice(answer, candidates):
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        raise ValueError("Expected a Choice answer")
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(candidates):
        raise ValueError("Choice probabilities must cover exactly the offered candidates")
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities.values()):
        raise ValueError("Invalid Choice probability")
    if abs(sum(probabilities.values()) - 1) > 1e-5:
        raise ValueError("Choice probabilities must sum to one")
    return {action: probabilities[action] for action in candidates}


def choose_action(probabilities, controller, rng):
    actions = list(probabilities)
    if controller == "greedy":
        return max(actions, key=probabilities.__getitem__), None
    draw, cumulative = rng.random(), 0.0
    total = sum(probabilities.values())
    for action in actions:
        cumulative += probabilities[action] / total
        if draw < cumulative:
            return action, draw
    return actions[-1], draw


def run_composed_snake(episodes, engine, controller="greedy", max_steps=256, batch_states=2, batch_questions=0, seed=17):
    if controller not in ("greedy", "sample") or type(max_steps) is not int or max_steps < 1:
        raise ValueError("Invalid controller or horizon")
    if type(batch_states) is not int or batch_states < 1 or type(batch_questions) is not int or batch_questions < 0:
        raise ValueError("Invalid batching")
    if len({row["id"] for row in episodes}) != len(episodes):
        raise ValueError("Duplicate episode IDs")
    started, sessions = time.perf_counter(), []
    execution = {"predict_calls": 0, "choice_queries": 0, "model_forward_passes": 0, "network_model_calls": 0}
    for row in episodes:
        snake.validate_state(row["initial_state"])
        controller_seed = int(digest([row["id"], seed])[:8], 16)
        sessions.append({"source": row, "state": copy.deepcopy(row["initial_state"]), "steps": [],
                         "status": None, "rng": random.Random(controller_seed), "controller_seed": controller_seed})
    while any(session["status"] is None for session in sessions):
        pending, plans, decisions = [], {}, {}
        for index, session in enumerate(sessions):
            if session["status"] is not None:
                continue
            state = session["state"]
            if state["done"]:
                session["status"] = state["outcome"]
                continue
            if len(session["steps"]) >= max_steps:
                session["status"] = "horizon_survived"
                continue
            plan = plan_candidates(state)
            plans[index] = plan
            actions = plan["offered_actions"]
            if not actions:
                session["status"] = "trapped"
                continue
            if len(actions) == 1:
                decisions[index] = ({actions[0]: 1.0}, "forced_move", {}, None)
            else:
                request = {"id": f"{session['source']['id']}:step:{len(session['steps'])}",
                           **render_composed_request(state, actions)}
                pending.append((index, request))
        for offset in range(0, len(pending), batch_states):
            batch = pending[offset:offset + batch_states]
            requests = [request for _, request in batch]
            response = engine.predict({"states": copy.deepcopy(requests)}, batch_questions=batch_questions, temperature=1.0)
            returned = response.get("states", [])
            ids = [row.get("id") for row in returned]
            if len(ids) != len(set(ids)) or set(ids) != {request["id"] for request in requests}:
                raise ValueError("Choice response IDs mismatch")
            indexed = {row["id"]: row for row in returned}
            for index, request in batch:
                answers = indexed[request["id"]].get("answers")
                if not isinstance(answers, dict) or set(answers) != {"action"}:
                    raise ValueError("Expected the single action question")
                answer = answers["action"]
                probabilities = validate_choice(answer, plans[index]["offered_actions"])
                receipt = {key: answer[key] for key in ("native_probabilities", "native_sum", "normalization_applied",
                    "target_kind", "source_api_call_id", "source_input_sha256", "cache_hit", "backend",
                    "probability_semantics", "candidate_to_token", "native_option_logits", "native_option_unconditional_probs",
                    "offered_token_mass", "prompt_tokens", "prompt_sha256") if key in answer}
                decisions[index] = probabilities, "model_tiebreak", receipt, digest(request)
            execution["predict_calls"] += 1
            execution["choice_queries"] += len(batch)
            counts = response.get("execution", {})
            execution["network_model_calls"] += counts.get("network_model_calls", 0) or 0
            forwards = counts.get("forward_passes")
            if forwards is None:
                execution["model_forward_passes"] = None
            elif execution["model_forward_passes"] is not None:
                execution["model_forward_passes"] += forwards
            if "cumulative_cost_usd" in counts:
                execution["cumulative_api_cost_usd"] = counts["cumulative_cost_usd"]
        for index, (probabilities, actor, receipt, input_hash) in decisions.items():
            session, plan = sessions[index], plans[index]
            before = session["state"]
            action, draw = choose_action(probabilities, controller, session["rng"]) if actor != "forced_move" else (next(iter(probabilities)), None)
            after = snake.step(before, action)
            if after["done"] and after["outcome"] != "win":
                raise RuntimeError("Common planner admitted an immediately colliding action")
            total = sum(probabilities.values())
            session["steps"].append({"step_index": len(session["steps"]), "state": physical_state(before),
                "action": action, "actor": actor, "probabilities": probabilities,
                "sampling_probabilities": {key: value / total for key, value in probabilities.items()},
                "controller_draw": draw, "candidate_order": list(probabilities), "planner": plan,
                "input_sha256": input_hash, "primitive_receipt": receipt, "ate_food": after["score"] > before["score"],
                "next_state": physical_state(after)})
            session["state"] = after
    results = []
    for session in sessions:
        source, trace, state = session["source"], session["steps"], session["state"]
        results.append({"id": source["id"], "split": source["split"], "game": "snake", "size": state["size"],
            "initial_state": copy.deepcopy(source["initial_state"]), "final_state": physical_state(state),
            "controller_seed": session["controller_seed"], "controller": controller, "horizon": max_steps,
            "outcome": session["status"], "full_board_win": session["status"] == "win",
            "horizon_survived": session["status"] == "horizon_survived", "survival_steps": len(trace),
            "food_score": state["score"], "food_collected": state["score"] - source["initial_state"]["score"],
            "forced_moves": sum(row["actor"] == "forced_move" for row in trace),
            "model_decisions": sum(row["actor"] == "model_tiebreak" for row in trace), "steps": trace})
    return {"schema": "nanojev-composed-snake-v1", "model_role": "common_code_planner_with_model_tiebreak",
        "protocol": {"controller": controller, "seed": seed, "temperature": 1.0, "max_steps": max_steps,
            "planner": "actual next-step collision filter, then shortest static next-head path to current food; next body except head is blocked",
            "no_path_rule": "all immediately safe actions remain", "single_candidate_rule": "forced move without model call",
            "zero_candidate_rule": "trapped, not a win", "model_input": "current physical state, action question, candidate descriptions only",
            "future_food_used_for_planning": False, "greedy_tie_order": "offered N/E/S/W order",
            "sample_rng": "independent Python Random per episode, SHA256([episode_id, seed]) first 32 bits; one recorded draw per model decision",
            "attribution": "food collection and survival use a common code planner; models choose only residual ties"},
        "summary": {"episodes": len(results), "outcomes": dict(Counter(row["outcome"] for row in results)),
            **{key: sum(row[key] for row in results) for key in ("survival_steps", "food_collected", "forced_moves", "model_decisions")},
            "mean_food_score": sum(row["food_score"] for row in results) / len(results) if results else None},
        "execution": execution, "elapsed_seconds": time.perf_counter() - started, "episodes": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--engine", required=True, choices=("checkpoint", "jev", "native", "constant", "reference"))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--env-file")
    parser.add_argument("--journal-dir", type=Path)
    parser.add_argument("--budget-usd", type=float, default=1)
    parser.add_argument("--controller", choices=("greedy", "sample"), default="greedy")
    parser.add_argument("--max-steps", type=int, default=256)
    parser.add_argument("--batch-states", type=int, default=2)
    parser.add_argument("--batch-questions", type=int, default=0)
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--precision", choices=("bf16", "fp32"), default="bf16")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--splits", default="test,ood")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output file")
    if args.max_steps < 1 or args.batch_states < 1 or args.batch_questions < 0 or args.max_length < 1:
        parser.error("Invalid horizon, batching, or context limit")
    if args.engine == "native" and args.batch_questions != 0:
        parser.error("Native Qwen requires --batch-questions 0")
    source = args.episodes.read_bytes()
    splits = {value.strip() for value in args.splits.split(",")}
    episodes = [row for row in map(json.loads, filter(str.strip, source.decode().splitlines()))
                if row["game"] == "snake" and row["split"] in splits]
    if not episodes:
        raise ValueError("No selected Snake episodes")
    engine, identity = None, {"engine": args.engine}
    try:
        if args.engine == "checkpoint":
            if args.checkpoint is None:
                parser.error("--checkpoint is required")
            from predict_toy_decisions import DecisionPredictor
            identity.update(checkpoint=str(args.checkpoint), checkpoint_sha256=file_digest(args.checkpoint / "best.safetensors"), precision=args.precision)
            engine = DecisionPredictor(args.checkpoint, max_length=args.max_length, precision=args.precision, disable_native_triton=True)
        elif args.engine == "native":
            from evaluate_native_qwen_navigation import NativeQwenPredictor, load_tokenizer, MODEL, REVISION, BACKEND
            tokenizer, snapshot, token_ids = load_tokenizer()
            identity.update(model=MODEL, revision=REVISION, backend=BACKEND, precision=args.precision,
                            token_ids=token_ids, cached_snapshot=str(snapshot),
                            probability_semantics="Original LM next-token probabilities conditional on the offered A-D tokens; zero output decoding")
            engine = NativeQwenPredictor(tokenizer, snapshot, token_ids, args.max_length, args.precision, disable_native_triton=True)
        elif args.engine == "jev":
            if not args.env_file or args.journal_dir is None or not math.isfinite(args.budget_usd) or not 0 < args.budget_usd <= 24:
                parser.error("Jev requires env/journal paths and a budget in (0,24]")
            from evaluate_scaled_games import LiveJev
            engine = LiveJev(args.env_file, args.journal_dir, args.budget_usd)
            identity["model"] = "typesafe-ai/jev"
        else:
            engine = UniformChoice()
            identity["chooser"] = "uniform over common-planner candidates; no learned or optimal tie preference"
        result = run_composed_snake(episodes, engine, args.controller, args.max_steps, args.batch_states, args.batch_questions, args.seed)
        result.update(model=identity, source_episodes_sha256=hashlib.sha256(source).hexdigest(),
            selected_episode_ids=[row["id"] for row in episodes], implementation_sha256=file_digest(Path(__file__)),
            environment_sha256=file_digest(Path(snake.__file__)), selection="all Snake episodes in requested splits, original order")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "summary": result["summary"], "execution": result["execution"]}))
    finally:
        if args.engine == "jev" and engine is not None:
            engine.close()


if __name__ == "__main__":
    main()
