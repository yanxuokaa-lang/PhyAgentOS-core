#!/usr/bin/env python3
"""Untuned native-Qwen Boolean judgments with the frozen maze exploration code.

No answer tokens are generated. Each complete local proposition is mapped to
false=A / true=B, and its probability is conditional on these offered tokens.
"""
import argparse
import hashlib
import json
from pathlib import Path

from evaluate_composed_maze import _validate_answer, file_digest
import evaluate_model_edges_maze as core


class NativeBooleanPredictor:
    """Batch Boolean propositions through the untouched native LM A/B head.

Each proposition becomes its own complete two-option prompt. The existing
native predictor sorts labels as false=A and true=B, reads one next-token
distribution, and performs no autoregressive decoding. Four directions remain
four independent Bernoulli judgments, not one categorical action distribution.
"""

    def __init__(self, native_predictor):
        self.native_predictor = native_predictor
        self.receipts = {}

    def predict(self, payload, batch_questions=0, temperature=1.0):
        if batch_questions != 0 or temperature != 1.0:
            raise ValueError("Native Boolean protocol requires batch_questions=0 and T=1")
        states = payload["states"]
        if not states or len({row["id"] for row in states}) != len(states):
            raise ValueError("Expected nonempty uniquely identified states")
        requests, mapping = [], {}
        outputs = {row["id"]: {"id": row["id"], "answers": {}} for row in states}
        for state_index, row in enumerate(states):
            for question_index, (qid, question) in enumerate(row["questions"].items()):
                criteria = question.get("criteria")
                if (question.get("type") != "boolean" or not isinstance(criteria, dict)
                        or set(criteria) != {"false", "true"}
                        or any(not isinstance(value, str) or not value for value in criteria.values())):
                    raise ValueError("Native Boolean adapter needs explicit complete false/true criteria")
                identifier = f"native_boolean_{state_index}_{question_index}"
                requests.append({"id": identifier, "state": row["state"], "questions": {"action": {
                    "type": "choice", "instructions": question["instructions"],
                    "criteria": {key: criteria[key] for key in ("false", "true")}}}})
                mapping[identifier] = row["id"], qid
        response = self.native_predictor.predict({"states": requests}, batch_questions=0, temperature=1.0)
        returned = response.get("states", [])
        ids = [row.get("id") for row in returned]
        if len(ids) != len(set(ids)) or set(ids) != set(mapping):
            raise ValueError("Native Boolean response coverage mismatch")
        for row in returned:
            source = row["answers"]["action"]
            probabilities = source.get("probabilities")
            if source.get("type") != "choice" or not isinstance(probabilities, dict):
                raise ValueError("Expected native two-option probabilities")
            answer = {key: value for key, value in source.items() if key not in ("choice", "type")}
            answer.update(type="boolean", p_true=probabilities.get("true"),
                target_kind="native_token_conditional_probabilities",
                decision_adapter="boolean_as_native_option_choice")
            _validate_answer(answer)
            state_id, qid = mapping[row["id"]]
            outputs[state_id]["answers"][qid] = answer
            self.receipts.setdefault(state_id, {})[qid] = {key: answer[key] for key in (
                "backend", "decision_adapter", "target_kind", "probability_semantics", "candidate_to_token",
                "native_option_logits", "native_option_unconditional_probs", "offered_token_mass",
                "prompt_tokens", "prompt_sha256") if key in answer}
        execution = dict(response.get("execution", {}))
        execution.update(active_state_batch_size=len(states), boolean_questions=len(requests),
                         native_option_prompts=len(requests), autoregressive_decode_steps=0)
        return {"states": list(outputs.values()), "execution": execution}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--splits", default="test,ood")
    parser.add_argument("--window-size", type=int, choices=(3, 5), default=5)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--batch-states", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--precision", choices=("bf16", "fp32"), default="bf16")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output file")
    if args.max_steps < 0 or args.batch_states < 1 or args.max_length < 1:
        parser.error("Invalid horizon, batch, or context limit")
    source = args.episodes.read_bytes()
    splits = {value.strip() for value in args.splits.split(",")}
    selected = [row for row in map(json.loads, filter(str.strip, source.decode().splitlines()))
                if row["game"] == "scaled_maze" and row["split"] in splits]
    if not selected:
        raise ValueError("No selected maze episodes")
    from evaluate_native_qwen_navigation import NativeQwenPredictor, load_tokenizer, MODEL, REVISION, BACKEND
    tokenizer, snapshot, token_ids = load_tokenizer()
    identity = {"engine": "native", "model": MODEL, "revision": REVISION, "backend": BACKEND,
        "precision": args.precision, "decision_adapter": "boolean_as_native_option_choice",
        "token_ids": {key: token_ids[key] for key in "AB"},
        "original_weight_files_sha256": {path.name: file_digest(path) for path in sorted(snapshot.glob("*.safetensors"))},
        "native_predictor_sha256": file_digest(Path(__file__).with_name("evaluate_native_qwen_navigation.py")),
        "probability_semantics": "Independent false=A/true=B next-token conditional probabilities for each Boolean proposition; zero output decoding"}
    engine = NativeBooleanPredictor(NativeQwenPredictor(tokenizer, snapshot, token_ids,
        args.max_length, args.precision, disable_native_triton=True))
    result = core.run_exploration(selected, engine, args.window_size, args.max_steps, args.batch_states, 0)
    for episode in result["episodes"]:
        for observation in episode["observations"]:
            observation["primitive_receipts"] = engine.receipts[observation["id"]]
    result["execution"].update(autoregressive_decode_steps=0, generated_tokens=0,
        backend=BACKEND, native_vocabulary_projection=True)
    result.update(model=identity, selected_episode_ids=[row["id"] for row in selected],
        source_episodes_sha256=hashlib.sha256(source).hexdigest(),
        source_cohort_sha256=sorted({row["source_cohort_sha256"] for row in selected if "source_cohort_sha256" in row}),
        implementation_sha256=file_digest(Path(core.__file__)),
        native_runner="scripts/evaluate_native_qwen_maze.py", native_runner_sha256=file_digest(Path(__file__)),
        local_renderer_sha256=file_digest(Path(__file__).with_name("evaluate_composed_maze.py")),
        selection="all maze episodes in requested input and splits; no filtering by native-model outcomes")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": result["summary"], "execution": result["execution"]}), flush=True)


if __name__ == "__main__":
    main()
