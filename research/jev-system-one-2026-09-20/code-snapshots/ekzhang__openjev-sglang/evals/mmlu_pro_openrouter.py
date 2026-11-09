# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28,<1", "pyarrow>=20,<24", "numpy>=2,<3", "matplotlib>=3.10,<4"]
# ///
"""One-token hosted MMLU-Pro accuracy, paired with the saved Jev/OpenJev sample."""

import argparse
import asyncio
import hashlib
import json
import math
import time
from pathlib import Path

import httpx
from run_files import load_predictions, save_manifest

INSTRUCTION = (
    "Choose the correct answer to the multiple-choice question. "
    "Answer with only the uppercase option letter, without explanation."
)
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def messages(row):
    # Select only question/options: gold labels and dataset rationales stay local.
    choices = "\n".join(f"{chr(65 + i)}: {s}" for i, s in enumerate(row["options"]))
    return [{"role": "user", "content": f"{INSTRUCTION}\n\n{row['question']}\n\n{choices}"}]


def score_response(data, labels):
    usage = data["usage"]
    if usage["completion_tokens"] != 1:
        raise ValueError("Provider did not generate exactly one token")
    if usage.get("completion_tokens_details", {}).get("reasoning_tokens") != 0:
        raise ValueError("Provider did not explicitly report zero reasoning tokens")
    choice = data["choices"][0]
    if choice["message"].get("reasoning") or choice["message"].get("reasoning_details"):
        raise ValueError("Unexpected generated reasoning")
    content = (choice.get("logprobs") or {}).get("content") or []
    if len(content) != 1 or not content[0].get("top_logprobs"):
        raise ValueError("Expected exactly one position with top-token logprobs")
    top = content[0]["top_logprobs"]
    if any(not math.isfinite(t["logprob"]) for t in top):
        raise ValueError("Nonfinite logprob")
    # Exact single-token A-J labels, without stripping whitespace or merging variants.
    found = {t["token"]: t["logprob"] for t in top if t["token"] in labels}
    # A returned valid label beats every omitted label, because this is a top-k list.
    # No valid label means unresolved, counted wrong rather than silently excluded.
    prediction = max(found, key=found.get) if found else None
    return prediction, found


async def main(args):
    import pyarrow.parquet as pq

    reference = json.loads((args.reference / "manifest.json").read_text())
    data_path = Path(__file__).parent / "data/mmlu-pro-test.parquet"
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != reference["sha256"]:
        raise ValueError("Dataset hash differs from baseline")
    dataset = pq.read_table(data_path).to_pylist()
    settings = {
        "model": "qwen/qwen3.8-27b",
        "max_tokens": 1,
        "temperature": 1,
        "top_p": 1,
        "logprobs": True,
        "top_logprobs": 20,
        "reasoning": {"enabled": False},
        "provider": {"only": ["parasail"], "allow_fallbacks": False, "require_parameters": True},
    }
    if not 1 <= args.count <= len(reference["indices"]):
        raise ValueError("Count outside reference sample")
    manifest = {
        k: reference[k] for k in ["dataset", "split", "revision", "sha256", "seed", "population"]
    }
    manifest.update(
        indices=reference["indices"][: args.count],
        count=args.count,
        settings=settings,
        endpoint=ENDPOINT,
        instruction=INSTRUCTION,
        prompt="{instruction}\\n\\n{question}\\n\\n{A: option...}",
        shots=0,
        concurrency=args.concurrency,
        scoring="argmax exact uppercase labels in top-20; no label counts wrong",
    )
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = save_manifest(args.output / "manifest.json", manifest)
    path = args.output / "predictions.jsonl"
    rows = load_predictions(path, manifest["indices"])
    done = {r["index"] for r in rows}
    queue = asyncio.Queue()
    for i in manifest["indices"]:
        if i not in done:
            queue.put_nowait(i)
    key = Path("~/.openrouter-api-key").expanduser().read_text().strip()
    headers = {"Authorization": "Bearer " + key, "X-OpenRouter-Title": "OpenJev one-token MMLU-Pro"}
    started = time.monotonic()
    # No redirects: credentials are sent only to the fixed OpenRouter endpoint.
    async with httpx.AsyncClient(headers=headers, timeout=120) as client:
        with path.open("a", buffering=1) as stream:

            async def worker():
                while not queue.empty():
                    i = queue.get_nowait()
                    row = dataset[i]
                    body = {**settings, "messages": messages(row)}
                    for attempt in range(6):
                        call_started = time.monotonic()
                        try:
                            response = await client.post(ENDPOINT, json=body)
                            response.raise_for_status()
                            data = response.json()
                            if "error" in data:
                                raise ValueError(f"Provider error: {data['error']}")
                            break
                        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                            if isinstance(
                                exc, httpx.HTTPStatusError
                            ) and exc.response.status_code not in {
                                429,
                                500,
                                502,
                                503,
                                504,
                                520,
                                529,
                            }:
                                raise
                            if attempt == 5:
                                raise
                            print(f"Transient retry index={i}, attempt={attempt + 1}", flush=True)
                            await asyncio.sleep(min(30, 2 ** (attempt + 1)))
                    labels = list("ABCDEFGHIJ"[: len(row["options"])])
                    if data["model"] != settings["model"] or data["provider"] != "Parasail":
                        raise ValueError("Unexpected model/provider routing")
                    prediction, found = score_response(data, labels)
                    record = {
                        "index": i,
                        "question_id": row["question_id"],
                        "category": row["category"],
                        "answer": row["answer"],
                        "prediction": prediction,
                        "label_logprobs": found,
                        "all_labels_returned": len(found) == len(labels),
                        "model": data["model"],
                        "provider": data["provider"],
                        "usage": data["usage"],
                        "attempts": attempt + 1,
                        "latency_s": time.monotonic() - call_started,
                        "response": data,
                    }
                    stream.write(json.dumps(record) + "\n")
                    rows.append(record)
                    if len(rows) % 100 == 0 or len(rows) == args.count:
                        print(
                            f"Completed {len(rows)}/{args.count} "
                            f"in {time.monotonic() - started:.1f}s",
                            flush=True,
                        )

            async with asyncio.TaskGroup() as group:
                for _ in range(args.concurrency):
                    group.create_task(worker())
    from report_mmlu_pro_openrouter import report

    report(args.output, args.report, args.reference, args.jev)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=16, choices=range(1, 65))
    parser.add_argument(
        "--reference", type=Path, default=Path("evals/runs/mmlu-pro-openjev-simple-options")
    )
    parser.add_argument("--jev", type=Path, default=Path("evals/runs/mmlu-pro-jev"))
    parser.add_argument("--output", type=Path, default=Path("evals/runs/qwen38-27b"))
    parser.add_argument("--report", type=Path, default=Path("evals/results/qwen38-27b"))
    asyncio.run(main(parser.parse_args()))
