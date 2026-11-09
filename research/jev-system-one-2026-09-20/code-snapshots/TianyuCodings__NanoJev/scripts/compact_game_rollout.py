#!/usr/bin/env python3
"""Store replayable game trajectories without repeating the full maze every step."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def compact(report):
    from scaled_maze import step as maze_step
    from snake_game import step as snake_step
    result = copy.deepcopy(report)
    count = 0
    for episode in result["episodes"]:
        state = episode["initial_state"]
        transition = maze_step if episode["game"] == "scaled_maze" else snake_step
        for item in episode["steps"]:
            following = transition(state, item["action"])
            if item["state"] != state or item["next_state"] != following:
                raise ValueError("Saved trajectory differs from deterministic environment replay")
            item["state_sha256"] = digest(item.pop("state"))
            item["next_state_sha256"] = digest(item.pop("next_state"))
            state = following
            count += 1
        if state != episode["final_state"]:
            raise ValueError("Final state does not match replay")
    result["trajectory_storage"] = "Replay initial_state with each action; verify both state hashes and final_state. Probabilities and outcomes are unchanged."
    result["verified_transitions"] = count
    return result


def verify(report):
    from scaled_maze import step as maze_step
    from snake_game import step as snake_step
    count = 0
    for episode in report["episodes"]:
        state = episode["initial_state"]
        transition = maze_step if episode["game"] == "scaled_maze" else snake_step
        for item in episode["steps"]:
            if digest(state) != item["state_sha256"]:
                raise ValueError("Before-state hash mismatch")
            state = transition(state, item["action"])
            if digest(state) != item["next_state_sha256"]:
                raise ValueError("After-state hash mismatch")
            count += 1
        if state != episode["final_state"]:
            raise ValueError("Final state mismatch")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    data = args.input.read_bytes()
    report = json.loads(data)
    if args.verify_only:
        print(json.dumps({"verified_transitions": verify(report), "file": str(args.input)}))
        return
    if args.output is None or args.output.exists():
        parser.error("Provide a new --output file")
    result = compact(report)
    result["raw_report_sha256"] = hashlib.sha256(data).hexdigest()
    verify(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"verified_transitions": result["verified_transitions"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
