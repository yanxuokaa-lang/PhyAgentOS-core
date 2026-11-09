# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28,<1", "pyarrow>=20,<24"]
# ///
"""Seeded, zero-shot MMLU-Pro evaluation through Jev or OpenJev's choice endpoint."""

import argparse
import asyncio
import hashlib
import json
import random
import time
from pathlib import Path

import httpx
import pyarrow.parquet as pq
from run_files import load_predictions, save_manifest

REVISION = "b189ec765aa7ed75c8acfea42df31fdae71f97be"
DATA_URL = (
    f"https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/resolve/{REVISION}/"
    "data/test-00000-of-00001.parquet"
)
MODEL = "~typesafe/jev-latest"
OPENJEV_MODEL = "Qwen/Qwen3.6-35B-A3B"
OPENJEV_URL = "https://ekzhang--openjev-sglang-openjev.us-west.modal.direct"
INSTRUCTIONS = "Choose the correct answer to the multiple-choice question in the state."


def payload(row, model=MODEL):
    # Deliberately select input fields; never send answer, answer_index or cot_content.
    return {
        "model": model,
        "state": row["question"],
        "questions": {
            "answer": {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": {chr(65 + i): text for i, text in enumerate(row["options"])},
            }
        },
    }


async def main(args):
    is_jev = args.provider == "jev"
    model = MODEL if is_jev else OPENJEV_MODEL
    endpoint = "https://openrouter.ai" if is_jev else OPENJEV_URL
    route = "/api/alpha/decisions" if is_jev else "/v1/systemone"
    args.output = args.output or Path(f"evals/runs/mmlu-pro-{args.provider}")
    args.report = args.report or Path(f"evals/runs/mmlu-pro-{args.provider}-report")
    data_path = Path(__file__).parent / "data/mmlu-pro-test.parquet"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as downloader:
        if not data_path.exists():
            response = await downloader.get(DATA_URL)
            response.raise_for_status()
            data_path.write_bytes(response.content)
    dataset = pq.read_table(data_path).to_pylist()
    indices = random.Random(args.seed).sample(range(len(dataset)), args.count)
    manifest = {
        "dataset": "TIGER-Lab/MMLU-Pro",
        "split": "test",
        "revision": REVISION,
        "data_url": DATA_URL,
        "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "population": len(dataset),
        "count": args.count,
        "seed": args.seed,
        "indices": indices,
        "model": model,
        "instructions": INSTRUCTIONS,
        "state": "{question}",
        "criteria": "Original letters A… mapped to options in order",
        "shots": 0,
        "endpoint": endpoint + route,
        "concurrency": args.concurrency,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = save_manifest(args.output / "manifest.json", manifest)
    path = args.output / "predictions.jsonl"
    rows = load_predictions(path, indices)
    done = {r["index"] for r in rows}
    queue = asyncio.Queue()
    for i in indices:
        if i not in done:
            queue.put_nowait(i)
    headers = {"Modal-Session-ID": "openjev-mmlu-pro-eval"}
    if is_jev:
        headers = {
            "Authorization": "Bearer "
            + Path("~/.openrouter-api-key").expanduser().read_text().strip(),
            "X-OpenRouter-Title": "OpenJev MMLU-Pro evaluation",
        }
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=endpoint, headers=headers, timeout=150) as client:
        deadline = time.monotonic() + 1200
        while not is_jev and not queue.empty():
            try:
                ready = await client.get("/health", timeout=10)
                if ready.is_success:
                    (args.output / "health.json").write_text(ready.text + "\n")
                    break
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("Backend did not become ready in 20 minutes")
            await asyncio.sleep(5)
        with path.open("a", buffering=1) as stream:

            async def worker():
                while not queue.empty():
                    i = queue.get_nowait()
                    row = dataset[i]
                    body = payload(row, model)
                    for attempt in range(9):
                        try:
                            response = await client.post(route, json=body)
                            response.raise_for_status()
                            data = response.json()
                            if not is_jev:
                                assert data["model"] == model
                                assert data["usage"]["output_tokens"] == 2
                            answer = data["answers"]["answer"]
                            if answer["choice"] not in body["questions"]["answer"]["criteria"]:
                                raise ValueError("Unexpected answer choice")
                            break
                        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                            retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                                exc.response.status_code in {429, 500, 502, 503, 504, 520, 529}
                            )
                            if not retryable or attempt == 8:
                                raise
                            print(f"Retry index={i}, attempt={attempt + 1}: {exc}", flush=True)
                            await asyncio.sleep(min(30, 2 ** (attempt + 1)))
                    record = {
                        "index": i,
                        "question_id": row["question_id"],
                        "category": row["category"],
                        "answer": row["answer"],
                        "prediction": answer["choice"],
                        "probabilities": answer.get("probabilities"),
                        "model": data.get("model", model),
                        "usage": data.get("usage", {}),
                        "attempts": attempt + 1,
                    }
                    rows.append(record)
                    stream.write(json.dumps(record) + "\n")
                    if len(rows) % 100 == 0 or len(rows) == args.count:
                        print(
                            f"Completed {len(rows)}/{args.count} in "
                            f"{time.monotonic() - started:.1f}s",
                            flush=True,
                        )
                    await asyncio.sleep(0.1)

            async with asyncio.TaskGroup() as group:
                for _ in range(args.concurrency):
                    group.create_task(worker())
    from report_mmlu_pro import summarize

    summarize(rows, manifest, args.report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--concurrency", type=int, default=16, choices=range(1, 65))
    parser.add_argument("--provider", choices=["jev", "openjev"], default="jev")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    asyncio.run(main(parser.parse_args()))
