# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=19", "numpy>=2"]
# ///
"""Compare capped Qwen reasoning and one-token final answers, without redeploying.

uv run evals/thinking_probe.py --container ta-... --output evals/runs/thinking-probe
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

BUDGETS = (0, 64, 256, 1024)
SEED = 20260919


async def remote(payload):
    import httpx

    from openjev.config import Settings
    from openjev.runtime import load_tokenizer

    tokenizer = load_tokenizer(Settings())
    think_end = tokenizer.encode("</think>", add_special_tokens=False)
    assert len(think_end) == 1
    semaphore = asyncio.Semaphore(16)
    async with httpx.AsyncClient(base_url="http://127.0.0.1:30000", timeout=180) as client:

        async def generate(ids, sampling, labels):
            response = await client.post(
                "/generate",
                json={
                    "input_ids": ids,
                    "sampling_params": sampling,
                    # Match production's selected-logprob path even for reasoning.
                    "return_logprob": True,
                    "token_ids_logprob": labels,
                    "logprob_start_len": -1,
                    "top_logprobs_num": 0,
                    "return_text_in_logprobs": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            assert result["meta_info"]["finish_reason"]["type"] != "abort"
            return result

        async def one(row, budget):
            content = (
                row["question"]
                + "\n\n"
                + "\n".join(f"{chr(65 + i)}. {option}" for i, option in enumerate(row["options"]))
            )
            content += (
                "\n\nSolve the multiple-choice question. Give your final answer "
                'as JSON with the key "answer" and only the choice letter.'
            )
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": content}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=budget > 0,
            )
            ids = tokenizer.encode(prompt, add_special_tokens=False)
            letters = [chr(65 + i) for i in range(len(row["options"]))]
            encoded = [tokenizer.encode(letter, add_special_tokens=False) for letter in letters]
            assert all(len(tokens) == 1 for tokens in encoded)
            labels = [tokens[0] for tokens in encoded]
            async with semaphore:
                started = time.monotonic()
                reasoning_ids = []
                natural_end = False
                reasoning_seconds = 0.0
                if budget:
                    thought = await generate(
                        ids,
                        {
                            "max_new_tokens": budget,
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 20,
                            "presence_penalty": 1.5,
                            "sampling_seed": SEED + row["index"],
                            "stop_token_ids": think_end,
                            "skip_special_tokens": False,
                        },
                        [0],
                    )
                    reasoning_seconds = time.monotonic() - started
                    reasoning_ids = thought["output_ids"]
                    assert len(reasoning_ids) <= budget
                    finish = thought["meta_info"]["finish_reason"]
                    # The Rust frontend can strip a matched stop token from output_ids.
                    natural_end = think_end[0] in reasoning_ids or (
                        finish["type"] == "stop"
                        and finish.get("matched") in (think_end[0], "</think>", think_end)
                    )
                    if think_end[0] in reasoning_ids:
                        reasoning_ids = reasoning_ids[: reasoning_ids.index(think_end[0])]
                    if not natural_end and finish["type"] != "length":
                        raise RuntimeError(f"Unexpected reasoning stop: {row['index']} {finish}")
                    ids += reasoning_ids
                    # Preserve generated token IDs and force the final-answer stage.
                    ids += tokenizer.encode("\n</think>\n\n", add_special_tokens=False)
                ids += tokenizer.encode('{"answer": "', add_special_tokens=False)
                answer = await generate(
                    ids,
                    {
                        "max_new_tokens": 1,
                        "temperature": 1.0,
                        "top_p": 1.0,
                        "top_k": -1,
                        "ignore_eos": True,
                    },
                    labels,
                )
                elapsed = time.monotonic() - started
            pairs = answer["meta_info"]["output_token_ids_logprobs"]
            assert len(pairs) == 1
            mapping = {p[1]: p[0] for p in pairs[0]}
            logprobs = [mapping[token] for token in labels]
            assert all(math.isfinite(p) for p in logprobs)
            result = {
                "index": row["index"],
                "budget": budget,
                "prediction": letters[max(range(len(labels)), key=logprobs.__getitem__)],
                "logprobs": logprobs,
                "reasoning_tokens": len(reasoning_ids),
                "natural_end": natural_end,
                "reasoning_finish": thought["meta_info"]["finish_reason"] if budget else None,
                "seconds": elapsed,
                "reasoning_seconds": reasoning_seconds,
                "reasoning": tokenizer.decode(reasoning_ids, skip_special_tokens=False),
                "final_prompt_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            }
            print("RESULT_JSON " + json.dumps(result), flush=True)

        # Separate homogeneous-budget runs: other budgets cannot inflate latency.
        for budget in BUDGETS:
            rows = payload["rows"].copy()
            random.Random(SEED).shuffle(rows)
            start = time.monotonic()
            await asyncio.gather(*(one(row, budget) for row in rows))
            print(
                "TIMING_JSON "
                + json.dumps({"budget": budget, "wall_seconds": time.monotonic() - start}),
                flush=True,
            )


def local():
    # Only the local launcher needs sibling modules; remote source stays self-contained.
    import numpy as np
    import pyarrow.parquet as pq
    from modal_probe import run_remote

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--count", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.count <= 256:
        parser.error("This small probe supports 1–256 questions")
    root = Path(__file__).parent
    data_path = root / "data/mmlu-pro-test.parquet"
    data = pq.read_table(data_path).to_pylist()
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert digest == "0e24a191921c2f453518a537a8b2117bd137e7714d4ef1565e9ba06c1ecb9ad8"
    excluded = set(random.Random(42).sample(range(len(data)), 1000))
    excluded.update(
        random.Random(20260918).sample([i for i in range(len(data)) if i not in excluded], 256)
    )
    indices = random.Random(SEED).sample(
        [i for i in range(len(data)) if i not in excluded], args.count
    )
    payload = {
        "rows": [
            {"index": i, "question": data[i]["question"], "options": data[i]["options"]}
            for i in indices
        ]
    }
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "dataset": "TIGER-Lab/MMLU-Pro",
        "revision": "b189ec765aa7ed75c8acfea42df31fdae71f97be",
        "test_sha256": digest,
        "indices": indices,
        "seed": SEED,
        "budgets": BUDGETS,
        "excluded": "Earlier 1000-question comparison and 256-question prompt probe",
        "concurrency": 16,
        "container": args.container,
        "latency": "Container-local reasoning plus final answer; excludes client queue",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    predictions, timings = run_remote(
        Path(__file__),
        args.container,
        payload,
        args.output,
        total=len(indices) * len(BUDGETS),
        progress_every=32,
    )
    assert len(predictions) == len(indices) * len(BUDGETS)
    assert len({(r["index"], r["budget"]) for r in predictions}) == len(predictions)
    for result in predictions:
        result.update(
            answer=data[result["index"]]["answer"], category=data[result["index"]]["category"]
        )
    (args.output / "predictions.json").write_text(json.dumps(predictions, indent=2) + "\n")
    baseline = {r["index"]: r["prediction"] == r["answer"] for r in predictions if r["budget"] == 0}
    metrics = {}
    for budget in BUDGETS:
        group = sorted((r for r in predictions if r["budget"] == budget), key=lambda r: r["index"])
        correct = np.array([r["prediction"] == r["answer"] for r in group])
        delta = correct.astype(int) - np.array([baseline[r["index"]] for r in group], dtype=int)
        draws = np.random.default_rng(SEED).choice(delta, size=(10000, len(group)))
        metrics[budget] = {
            "correct": int(correct.sum()),
            "n": len(group),
            "accuracy": float(correct.mean()),
            "delta": float(delta.mean()),
            "paired_95_ci": np.quantile(draws.mean(axis=1), [0.025, 0.975]).tolist(),
            "mean_reasoning_tokens": float(np.mean([r["reasoning_tokens"] for r in group])),
            "natural_end_count": sum(r["natural_end"] for r in group),
            "p50_seconds": float(np.median([r["seconds"] for r in group])),
            "p95_seconds": float(np.quantile([r["seconds"] for r in group], 0.95)),
            "wall_seconds": next(r["wall_seconds"] for r in timings if r["budget"] == budget),
        }
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--remote"]:
        asyncio.run(remote(json.loads(zlib.decompress(base64.b64decode(sys.argv[2])))))
    else:
        local()
