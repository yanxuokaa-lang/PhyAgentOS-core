# jevsim

A local simulator of the [TypeSafe System One](https://docs.typesafe.ai/api) API. It serves `POST /v1/systemone` and answers `noul`, `choice`, and `score` questions by scoring canonical tokens on an [SGLang](https://github.com/sgl-project/sglang) server.

This is **not** the hosted Jev model. It is an independent open implementation that speaks the same HTTP shape so you can run System One-style scoring locally.

## Credits

System One, Jev, and the `POST /v1/systemone` contract were created by the [TypeSafe AI](https://typesafe.ai) team. Thank you to TypeSafe AI for publishing the API and the ideas behind [System One models](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

This repository is not affiliated with TypeSafe AI. For the official product, use [api.typesafe.ai](https://docs.typesafe.ai/api).

## License

MIT. See [LICENSE](LICENSE).

## Step 1: Check prerequisites

You need:

- Python 3.11 or newer
- A GPU machine only if you want real model scores (the test suite does not need a GPU)

## Step 2: Install jevsim

From the repo root:

```bash
pip install -e ".[dev]"
```

That installs the `jevsim` CLI.

## Step 3: Install SGLang on the GPU machine

Install SGLang in the environment that has the GPU. Either use the copy in `sglang/` or follow the [SGLang install docs](https://docs.sglang.io).

Confirm the `sglang` module is importable in that environment before continuing.

## Step 4: Launch the SGLang server

```bash
python scripts/launch_sglang.py --model Qwen/Qwen2.5-7B-Instruct
```

Or:

```bash
jevsim launch-sglang --model Qwen/Qwen2.5-7B-Instruct -- --tp-size 1
```

The launcher always sets:

- `--grammar-backend xgrammar`
- `--enable-hierarchical-cache` with `write_through`, `page_first_direct`, and `--hicache-ratio 2`
- `--sampling-defaults openai` so request temperature is not overridden by a greedy `generation_config`

If GPU I/O kernels fail on your machine, add `--io-backend direct`. Add `--l3-file` to turn on the HiCache L3 file backend. Extra flags after `--` go to `sglang.launch_server`.

Wait until the server is listening. The default URL is `http://127.0.0.1:30000`.

## Step 5: Start the jevsim API

In a second terminal:

```bash
export SGLANG_BASE_URL=http://127.0.0.1:30000
# optional: export JEV_API_KEY=...
jevsim serve --port 8080
```

`GET /health` and `GET /v1/models` are also served. If `JEV_API_KEY` or `TYPESAFE_API_KEY` is set, requests must send `Authorization: Bearer <key>`.

## Step 6: Send a System One request

```bash
curl -s http://127.0.0.1:8080/v1/systemone \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JEV_API_KEY" \
  --data @examples/systemone.json
```

`examples/systemone.json` asks three questions against one shared `state`:

- `noul` — a yes/no probability (`is_urgent`)
- `choice` — one of several labeled options (`department`)
- `score` — a position on a short rubric (`frustration`)

`questions` is the TypeSafe field name for the struct. `struct` is accepted as an alias.

## Step 7 (optional): Run multimodal questions

`state` can mix text with images, audio, and video. Refs are URLs, file paths, or `data:` URIs. The package strips the bytes out of the prompt, leaves `[image]` / `[audio]` / `[video]` markers, and sends `image_data` / `audio_data` / `video_data` on every SGLang suffix job so HiCache still sees one shared prefix.

Serve a VLM and pass `--multimodal` when launching SGLang:

```bash
python scripts/launch_sglang.py --model Qwen/Qwen2.5-VL-7B-Instruct --multimodal
```

Then post `examples/systemone_multimodal.json`. Nested media in `state` looks like:

```json
{
  "type": "image_url",
  "image_url": {"url": "https://example.com/frame.jpg"}
}
```

`"type": "image" | "audio" | "video"` with `url`, `path`, or base64 `data` also works. OpenAI `image_url` / `audio_url` / `video_url` content-part lists work as `state` too.

Top-level attachments apply to every question:

```json
{
  "state": "Is the door open?",
  "images": ["https://example.com/door.jpg"],
  "audio": ["https://example.com/knock.wav"],
  "video": ["https://example.com/clip.mp4"],
  "model": "jev-latest",
  "questions": { "open": { "type": "noul", "instructions": "Is the door open?" } }
}
```

## Step 8 (optional): Run tests

No GPU. Simulated SGLang `/tokenize` and `/generate` payloads run through the real HTTP adapters.

```bash
pytest
```

## How scoring works

Questions share a STATE prefix and run as one SGLang batch so [RadixAttention + HiCache](https://docs.sglang.io/docs/advanced_features/hicache_design) reuse the KV cache. Each question is scored under one [XGrammar](https://github.com/mlc-ai/xgrammar) **union** over canonical tokens (`0`/`1`, `a`–`Z`, or `0…9`). The grammar mask leaves only that question's tokens, so next-token logprobs are already `P(option | prefix, option in set)`.

1. Render `STATE` then `STRUCT` into one chat prefix (state first, so questions share a long cached span).
2. Fan **questions** (not options) out in one SGLang `/generate` batch. Each item has `max_new_tokens: 0`, a union GBNF (`root ::= "0" | "1"`), and `token_ids_logprob` for those canonical ids.
3. Read `output_token_ids_logprobs` (masked log-softmax), then `softmax` over the option set.
4. **Noul (regression):** canonical tokens `0` and `1`. `noul` is `P(1)` in `[0, 1]`.
5. **Choice:** map option keys onto `a…z` then `A…Z`. `choice` is the original key of the argmax; `confidence` is `1 - H(p)/log(n)`.
6. **Score:** canonical tokens `0…k-1` (at most 10 levels). `score` is the expected index; `legend` maps index → rubric text.

## Layout

Each module does one job:

| module | role |
| --- | --- |
| `validate` / `media` / `canonical` / `plans` / `prompt` / `grammar` | pure compile of state+struct+media → prefix + GBNF suffixes |
| `sglang_http` | tokenize chat prefix + labels, batch union `/generate` |
| `math_ops` / `answers` / `usage` | logprobs → TypeSafe JSON |
| `evaluate` | function pipeline |
| `app` | FastAPI wire format |
| `launch_sglang` | SGLang argv |
