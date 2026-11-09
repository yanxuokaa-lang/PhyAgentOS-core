# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=19", "numpy>=2"]
# ///
"""Small one-token prompt ablation, executed inside an existing Modal container.

uv run evals/prompt_probe.py --container ta-... --output evals/runs/prompt-research
No deployment changes. All variants use selected-token logprobs, concurrency 16,
and exactly one generated token. Test labels never enter the remote payload.
"""

import argparse
import asyncio
import base64
import hashlib
import json
import math
import random
import subprocess
import sys
import time
import zlib
from pathlib import Path

VARIANTS = ("current", "plain", "json", "five_shot", "five_shot_rationales")
REVISION = "b189ec765aa7ed75c8acfea42df31fdae71f97be"


async def remote(payload):
    import httpx

    from openjev.config import Settings
    from openjev.models import SystemOneRequest
    from openjev.prompts import PromptCompiler
    from openjev.runtime import load_tokenizer

    tokenizer = load_tokenizer(Settings())
    compiler = PromptCompiler(tokenizer)
    semaphore = asyncio.Semaphore(16)

    def question_text(row, json_answer=False):
        text = (
            row["question"]
            + "\n\n"
            + "\n".join(f"{chr(65 + i)}. {option}" for i, option in enumerate(row["options"]))
        )
        instruction = (
            'Choose the correct answer. Reply in JSON with the key "answer" and its letter.'
            if json_answer
            else "Choose the correct answer. Reply with only its letter."
        )
        return text + "\n\n" + instruction

    def compile_prompt(row, variant):
        if variant == "current":
            request = SystemOneRequest.model_validate(
                {
                    "model": "Qwen/Qwen3.6-35B-A3B",
                    "state": row["question"],
                    "questions": {
                        "answer": {
                            "type": "choice",
                            "instructions": (
                                "Choose the correct answer to the multiple-choice "
                                "question in the state."
                            ),
                            "criteria": {chr(65 + i): v for i, v in enumerate(row["options"])},
                        }
                    },
                }
            )
            return compiler.prepare(request).branches[0].input_ids
        messages = []
        if variant.startswith("five_shot"):
            # Official validation examples only; no test labels or test rationales.
            for demo in payload["demos"][row["category"]]:
                answer = "Answer:\n" + demo["answer"]
                if variant == "five_shot_rationales":
                    answer = demo["cot_content"] + "\n\n" + answer
                messages.extend(
                    [
                        {"role": "user", "content": question_text(demo)},
                        {"role": "assistant", "content": answer},
                    ]
                )
        messages.append({"role": "user", "content": question_text(row, variant == "json")})
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        text += '{"answer": "' if variant == "json" else "Answer:\n"
        return tokenizer.encode(text, add_special_tokens=False)

    async with httpx.AsyncClient(base_url="http://127.0.0.1:30000", timeout=120) as client:
        for _ in range(120):
            try:
                response = await client.get("/health")
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            await asyncio.sleep(5)
        else:
            raise RuntimeError("SGLang did not become ready")

        async def one(row, variant):
            ids = compile_prompt(row, variant)
            labels = [chr(65 + i) for i in range(len(row["options"]))]
            encoded = [tokenizer.encode(label, add_special_tokens=False) for label in labels]
            assert all(len(tokens) == 1 for tokens in encoded)
            token_ids = [tokens[0] for tokens in encoded]
            assert len(ids) < 32768
            async with semaphore:
                started = time.monotonic()
                response = await client.post(
                    "/generate",
                    json={
                        "input_ids": ids,
                        "sampling_params": {
                            "max_new_tokens": 1,
                            "temperature": 1.0,
                            "ignore_eos": True,
                        },
                        "return_logprob": True,
                        "token_ids_logprob": token_ids,
                        "logprob_start_len": -1,
                        "top_logprobs_num": 0,
                        "return_text_in_logprobs": False,
                    },
                )
                response.raise_for_status()
                elapsed = time.monotonic() - started
            pairs = response.json()["meta_info"]["output_token_ids_logprobs"][0]
            logprobs = {p[1]: p[0] for p in pairs}
            scores = [logprobs[token] for token in token_ids]
            assert all(math.isfinite(score) for score in scores)
            result = {
                "index": row["index"],
                "variant": variant,
                "prediction": labels[max(range(len(scores)), key=scores.__getitem__)],
                "logprobs": scores,
                "label_mass": sum(math.exp(s) for s in scores),
                "input_tokens": len(ids),
                "seconds": elapsed,
                "prompt_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            }
            print("RESULT_JSON " + json.dumps(result), flush=True)

        jobs = [(row, variant) for row in payload["rows"] for variant in VARIANTS]
        random.Random(payload["seed"]).shuffle(jobs)
        await asyncio.gather(*(one(row, variant) for row, variant in jobs))


def local():
    # Only the local launcher needs sibling modules; remote source stays self-contained.
    import numpy as np
    import pyarrow.parquet as pq
    from modal_probe import run_remote

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260918)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data = Path(__file__).parent / "data"
    rows = pq.read_table(data / "mmlu-pro-test.parquet").to_pylist()
    validation = pq.read_table(data / "mmlu-pro-validation.parquet").to_pylist()
    excluded = set(random.Random(42).sample(range(len(rows)), 1000))
    indices = random.Random(args.seed).sample(
        [i for i in range(len(rows)) if i not in excluded],
        args.count,
    )
    # Gold labels stay in the local scoring process; demos belong to validation.
    test_rows = [
        {"index": i, **{k: rows[i][k] for k in ("question", "options", "category")}}
        for i in indices
    ]
    demos = {
        category: [r for r in validation if r["category"] == category]
        for category in {r["category"] for r in test_rows}
    }
    assert all(len(group) == 5 for group in demos.values())
    payload = {"rows": test_rows, "demos": demos, "seed": args.seed}
    manifest = {
        "revision": REVISION,
        "indices": indices,
        "seed": args.seed,
        "excluded": "1000 original test indices from random.Random(42)",
        "variants": VARIANTS,
        "container": args.container,
        "concurrency": 16,
        "max_new_tokens": 1,
        "enable_thinking": False,
        "test_sha256": hashlib.sha256((data / "mmlu-pro-test.parquet").read_bytes()).hexdigest(),
        "validation_sha256": hashlib.sha256(
            (data / "mmlu-pro-validation.parquet").read_bytes()
        ).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    predictions, _ = run_remote(
        Path(__file__),
        args.container,
        payload,
        args.output,
        total=len(indices) * len(VARIANTS),
        progress_every=128,
    )
    assert len(predictions) == len(indices) * len(VARIANTS)
    assert len({(r["index"], r["variant"]) for r in predictions}) == len(predictions)
    for result in predictions:
        result["answer"] = rows[result["index"]]["answer"]
        result["category"] = rows[result["index"]]["category"]
    (args.output / "predictions.json").write_text(json.dumps(predictions, indent=2) + "\n")
    baseline = {
        r["index"]: r["prediction"] == r["answer"] for r in predictions if r["variant"] == "current"
    }
    summary = {}
    for variant in VARIANTS:
        group = sorted(
            (r for r in predictions if r["variant"] == variant), key=lambda r: r["index"]
        )
        correct = np.array([r["prediction"] == r["answer"] for r in group])
        delta = correct.astype(int) - np.array([baseline[r["index"]] for r in group], dtype=int)
        draws = np.random.default_rng(args.seed).choice(delta, size=(10000, len(group)))
        summary[variant] = {
            "n": len(group),
            "correct": int(correct.sum()),
            "accuracy": float(correct.mean()),
            "delta": float(delta.mean()),
            "paired_95_ci": np.quantile(draws.mean(axis=1), [0.025, 0.975]).tolist(),
            "mean_label_mass": float(np.mean([r["label_mass"] for r in group])),
            "mean_input_tokens": float(np.mean([r["input_tokens"] for r in group])),
            "predicted_A": sum(r["prediction"] == "A" for r in group),
        }
    (args.output / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--remote"]:
        asyncio.run(remote(json.loads(zlib.decompress(base64.b64decode(sys.argv[2])))))
    else:
        local()
