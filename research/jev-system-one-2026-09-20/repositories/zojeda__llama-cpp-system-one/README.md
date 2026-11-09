# llama-cpp-system-one

A Rust implementation of the System One API for structured question answering with DiffusionGemma and llama.cpp.
> OpenJev - Open, Jev Compatible

This independent learning project builds on the work at [codiv.ai](https://codiv.ai/). Credit goes to Codiv for the System One approach and API design, Google DeepMind for [DiffusionGemma](https://ai.google.dev/gemma/docs/diffusiongemma/model_card), and [llama.cpp](https://github.com/ggml-org/llama.cpp) contributors for native inference support. Rust handles request validation, prompt construction, and response mapping.

Run structured questions with DiffusionGemma through llama.cpp on AMD ROCm/HIP hardware. Send a state and questions; get yes/no probabilities, choices, or rubric scores through the System One API. Image questions also require a compatible vision projector.

## The masked canvas

A canvas is a block of token positions. For this API, we fix the question labels and leave one answer position per question:

```text
Prompt: state + questions + answer codes (A = yes, B = no, ...)

Canvas: Question 1       Question 2
        Answer: [ ? ]   Answer: [ ? ]
                 ^               ^
             answer slot     answer slot
```

The brackets mark unknown answers. We fill those positions with seeded random vocabulary tokens, excluding the special mask token. After caching the prompt, we evaluate the whole canvas once. Bidirectional attention lets each slot use the surrounding canvas and prompt context. We read the logits at each slot and normalize them over its allowed answer codes.

DiffusionGemma's full text generator refines a noisy canvas over multiple denoising steps. By default, this service takes one read with fixed surrounding text and returns the answer distributions. Optional extensions add denoising steps, noise samples, a bounded thought, sequential question chunks, and images. See [diffusion and canvas inference](docs/inference.md) for the model explanation, a worked example, and the limits of these probabilities.

## Run

You need Rust 1.88+, a C/C++ compiler, CMake 3.24+, Make or Ninja, libclang, and a DiffusionGemma GGUF model. Obtain the model yourself; Cargo builds the pinned llama.cpp sources. For AMD GPUs, install ROCm/HIP and follow the [build guide](docs/build.md#rocmhip).

```bash
git submodule update --init --recursive
export DIFFUSION_MODEL="$HOME/models/diffusiongemma/diffusiongemma-26B-A4B-it-Q4_K_M.gguf"
export DIFFUSION_MMPROJ="$HOME/models/diffusiongemma/mmproj-diffusiongemma-26b-a4b-f16.gguf"

# CPU
cargo run --release --locked -p llama-cpp-system-one -- --bind 127.0.0.1:8080

# AMD GPU: after configuring ROCm/HIP
export AMDGPU_TARGETS=gfx1151
cargo run --release --locked -p llama-cpp-system-one --features hip,native -- --bind 127.0.0.1:8080

```

For images, start the service with a compatible projector (see [image setup](docs/build.md#image-input)):

```bash
cargo run --release --locked -p llama-cpp-system-one --features hip,native -- -m "$DIFFUSION_MODEL" --mmproj "$DIFFUSION_MMPROJ"
```

Choose one server command. In another terminal:

```bash
curl http://127.0.0.1:8080/v1/systemone \
  -H "Content-Type: application/json" \
  --data-binary @examples/system-one.json
```

The example asks three questions about a construction material. Set `TYPESAFE_API_KEY` on the server to enable bearer authentication, then add `-H "Authorization: Bearer $TYPESAFE_API_KEY"` to client calls. The default listener is `127.0.0.1:8080`.

Try the [hot dog photo example](docs/api.md#hot-dog-photo), including the [bundled JPEG](examples/hotdog.jpg), [ready-to-send request](examples/hotdog.json), and startup instructions for the vision projector.

Use [JavaScript SDK examples](examples/javascript/README.md) for application code. The [API reference](docs/api.md) covers request types, model aliases, and errors. Use the [extensions](docs/api.md#extensions) for `steps`, `samples`, `think`, `sequential`, and `images`. Text defaults remain `steps=1`, `samples=1`, and `think=0`; image requests require `--mmproj` or `DIFFUSION_MMPROJ`.

## Benchmark

On 2026-09-19, we compared 72 requests and 84 questions per endpoint in one round, with concurrency one and no benchmark warmups or retries.

| Metric | Local `gemmadiffusion-0.1` | Hosted TypeSafe `jev-1.13.0` |
| --- | --- | --- |
| Question accuracy | 65/84 (77.4%) | 80/84 (95.2%) |
| Valid responses | 72/72 | 71/72 |
| p50 latency, valid responses | 588.4 ms | 339.9 ms |
| p95 latency, valid responses | 1,314.6 ms | 881.0 ms |
| Mean latency, all attempts | 683.6 ms | 838.4 ms |

The hosted endpoint timed out once at 30 seconds. We count that answer as incorrect and include the timeout in the all-attempt mean. Timings include network travel and SDK parsing. The saved run lacks hardware and quantization details; treat it as an exploratory result on this synthetic corpus. See [results and methodology](benchmarks/system-one/README.md#recorded-results-2026-09-19) and the [data snapshot](benchmarks/system-one/results-2026-09-19.json).

## Documentation

| Guide | Contents |
| --- | --- |
| [Build and hardware](docs/build.md) | ROCm/WSL, CUDA, native library overrides |
| [Diffusion and canvas inference](docs/inference.md) | Denoising, answer slots, probability math |
| [HTTP API](docs/api.md) | Question types, authentication, limits, errors |
| [Development](docs/development.md) | Crate layout, tests, recipes, SCM CLI |
| [Benchmark](benchmarks/system-one/README.md) | Results, corpus, scoring, runner settings |
