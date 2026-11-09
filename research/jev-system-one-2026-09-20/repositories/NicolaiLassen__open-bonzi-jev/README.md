<h1 align="center">open-bonzi-jev</h1>

<p align="center">
  <b>Typed decisions from a 27B model, read out of one forward pass, from a 5.95&nbsp;GB file on a laptop.</b><br>
  <sub>openjev's mechanism &middot; Bonsai's weights &middot; runs on CPU, Metal, CUDA or Vulkan</sub>
</p>

<p align="center">
  <a href="#results"><img alt="WANLI-256 74.6%" src="https://img.shields.io/badge/WANLI--256-74.6%25-2a78d6"></a>
  <a href="#results"><img alt="5.95 GB" src="https://img.shields.io/badge/weights-5.95_GB-eb6834"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/code-MIT-informational"></a>
  <a href="https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf"><img alt="Apache 2.0 weights" src="https://img.shields.io/badge/weights-Apache_2.0-informational"></a>
</p>

```console
$ ./openjev/score.sh -q "Is the user angry?" --state '{"msg":"this is broken AGAIN and nobody replies"}'
{"choice": "true", "probabilities": {"true": 0.991651, "false": 0.008349},
 "label_mass": 0.994205, "prompt_tokens": 112, "forward_s": 1.852, "backend": "llama.cpp"}
```

Nothing is generated. Nothing is parsed. The model is handed a lettered
multiple-choice question, and the scorer reads the probability of `A` versus
`B` straight off the next-token distribution. One forward pass, a real number
out, an `if` you can branch on.

---

## Where this came from

None of the ideas here are mine.

**[TypeSafe](https://typesafe.ai/blog/introducing-system-one-models-and-jev)**
built **Jev** and gave the category a name: "System One" models that return
typed probabilistic decisions instead of text. It is closed, hosted, and behind
a waitlist.

**[TheoLeeCJ](https://github.com/TheoLeeCJ)** then showed you don't need any of
that. **[SemIf](https://github.com/TheoLeeCJ/SemIf)**, first released under the
name **OpenJev**, gets the same interface out of ordinary frozen open models by
reading the option logits directly, no training involved. It's MIT, and it runs
in your browser at [openjev.com](https://openjev.com).

What I did was point that mechanism at **[PrismML's Bonsai](https://prismml.com)**
models, so the whole decision loop fits in 5.95 GB and runs on a laptop GPU.
That's the contribution: wiring, packaging, and the measurements below.

If you actually want to use this idea, **start with
[SemIf](https://github.com/TheoLeeCJ/SemIf), not here.** It has the browser
build, shared-prefix reuse, a reranker comparison, perturbation tests and a far
more careful eval harness than anything in this repo.

`openjev/score.py` is an **independent re-implementation** of SemIf's "direct"
mode with its own prompt, and no SemIf code is vendored. Since the prompt differs,
**the numbers here aren't directly comparable to theirs.** Full accounting in
[CREDITS.md](CREDITS.md).

> Not affiliated with, endorsed by, or connected to TypeSafe, PrismML, or
> TheoLeeCJ. Jev and TypeSafe are referenced only to say what kind of thing
> this is.

---

## Results

Apple M4 Pro, GPU, context 4096, warmup excluded, one loaded model per run.
Every number below was produced by [`scripts/benchmark.py`](scripts/benchmark.py)
in this repo. Re-run it and you should get the same thing.

### Decision quality

<img src="docs/charts/wanli256-accuracy.svg" alt="WANLI-256 accuracy by Bonsai model" width="100%">

**WANLI-256** is the real measurement: 256 rows of adversarial natural-language
inference from [WANLI](https://huggingface.co/datasets/alisawuffles/WANLI),
label-balanced so chance is 33.3% rather than the majority-class rate.

| Model | Quant | On disk | Runtime | easy100 | **WANLI-256** | q/min | median latency |
|---|---|---|---|---|---|---|---|
| **Bonsai 1 1.7B** | `Q1_0` | 0.25 GB | stock | 79% | **52.0%** | 925 | 57 ms |
| **Bonsai 1 4B** | `Q1_0` | 0.57 GB | stock | 97% | **60.2%** | 398 | 140 ms |
| **Bonsai 1 8B** | `Q1_0` | 1.16 GB | stock | 98% | **64.5%** | 230 | 245 ms |
| **Bonsai 1 27B** | `Q1_0` | 3.80 GB | stock | 100% | **71.1%** | 31 | 1911 ms |
| **Ternary Bonsai 1 8B** | `PQ2_0` | 2.18 GB | fork | 100% | **65.2%** | 200 | 281 ms |
| **Bonsai 2 27B** | `PTQ1_0` | 5.95 GB | fork | 100% | **74.6%** | 24 | 2443 ms |

For scale, SemIf reports **0.637 balanced accuracy on WANLI-256 with
Qwen3.5-4B** at 3.01 GB. Bonsai 1 8B lands at 64.5% from 1.16 GB and Bonsai 2
27B at 74.6% from 5.95 GB. But **this is indicative, not a like-for-like
comparison**: different rows, different prompt, different model. Treat it as a
sanity range, not a leaderboard.

### Size and speed

<img src="docs/charts/accuracy-vs-size.svg" alt="WANLI-256 accuracy against weights on disk, by model" width="100%">

<img src="docs/charts/throughput.svg" alt="Decisions per minute by model, log scale" width="100%">

The trade is stark and worth internalising: **Bonsai 1 1.7B is 38× faster than
Bonsai 2 27B and barely above chance.** Quality costs throughput, roughly
linearly in parameters, and the 1-bit family buys size, not speed.

### The `easy100` column is a smoke test, not a benchmark

It is 100 trivial true/false facts, and everything from 4B up saturates it. It
exists to catch a broken prompt or a broken backend. It is in the table only so
you can see it saturate.

It does show one thing worth knowing. Asked *"does a spider have two legs?"*:

| Model | Answer | Confidence | `label_mass` |
|---|---|---|---|
| Bonsai 1 8B | `true` ❌ | **0.998** | 0.9997 |
| Bonsai 1 1.7B | `true` ❌ | 0.754 | 0.9775 |
| Bonsai 2 27B | `false` ✅ | 0.996 | 0.9932 |

**Bonsai 1 8B is wrong at 0.998 confidence**, with a `label_mass` of 0.9997.
The model was unambiguously answering the question asked, and was unambiguously
wrong. This is the single most important caveat in this repo: **`label_mass`
tells you that you got an answer, never that it is right.** A confident wrong
number and a confident right one are the same shape.

---

## Install

Python 3.10+, `cmake`, a C++ toolchain, ~7 GB of disk.

```bash
git clone https://github.com/NicolaiLassen/open-bonzi-jev.git
cd open-bonzi-jev

./scripts/build_llama_fork.sh                            # ~2 min
python3 scripts/download_model.py Ternary-Bonsai-2-27B   # 5.95 GB

./bonzi/chat.sh --check          # verify runtime and weights match
./openjev/score.sh -q "Is the sky blue?"
```

Want small and fast instead? `Bonsai-8B` is 1.16 GB, needs no fork, and runs
10× the throughput at 64.5%:

```bash
./scripts/get_llama_cpp.sh
python3 scripts/download_model.py Bonsai-8B
./openjev/score.sh -q "Is the sky blue?" --model bonzi/models/Bonsai-8B
```

### Bonsai 2 needs PrismML's llama.cpp fork

Bonsai 2's ternary weights carry a folded-in **Hadamard rotation**, and the
runtime must apply the matching transform to activations. Stock llama.cpp has
no such transform and does not implement the `PTQ1_0` / `PQ2_0` tensor types at
all, so it refuses the file:

```
gguf_init_from_reader: tensor 'token_embd.weight' has invalid ggml type 142. should be in [0, 43)
```

**Good news: every incompatibility we could produce fails loudly, at load, in
well under a second.** We tested the full matrix, and nothing silently produces
garbage. `chat.py --check` confirms a pairing by *actually loading it*, which
is the only authoritative test:

```console
$ ./bonzi/chat.sh --check
model        Ternary-Bonsai-2-27B-PTQ1_0.gguf (5.95 GB)
quantization PTQ1_0  (ggml tensor type 143)
needs fork   yes
llama-server .../llama.cpp-prism/build/bin/llama-server
trial load   PTQ1_0 tensors, gguf v3, loaded successfully
verdict      OK
```

Bonsai 1's `Q1_0` is merged upstream and runs on stock release binaries. See
[bonzi/README.md](bonzi/README.md) for the full compatibility matrix.

---

## Use it

```bash
./openjev/score.sh -q "Is the sky blue?"
./openjev/score.sh -q "Which team?" --options billing,engineering,product \
                   --state '{"subject":"500 errors on every API call"}'
./openjev/score.sh --input openjev/examples/wanli256.jsonl
```

Keep the model resident, because 27B weights are not free to page in:

```bash
./openjev/api.sh          # localhost:8000, no auth
./openjev/demo.sh         # in another terminal
```

`POST /decide`, `POST /chat`, `GET /health`. `demo.py` triages support tickets
and drafts replies only for those judged both angry and urgent. It is a plain
`if angry and urgent:`, where the conditions happen to be semantic.

---

## How the scoring works

1. Build a chat prompt: a system line saying the model is a decision function
   that replies with a letter, then the state, the question, and the options
   lettered `A.`, `B.`, …
2. Apply the chat template with **thinking disabled**, so the assistant turn
   begins exactly where the answer letter goes.
3. One forward pass. Take the next-token scores.
4. Look up each option letter's score (`A`…`Z` are single tokens in these
   vocabularies) and softmax over **just those**.

**Thinking mode is load-bearing.** Bonsai 2 reasons by default at `xhigh`
effort. With `enable_thinking: false` its template emits an already-closed
empty block, `<think>\n\n</think>\n\n`, so the next token is the answer. Leave
it on and the next token is the first word of a monologue, and every
probability is noise. The scorer always disables it.

For GGUF models the prompt is rendered and tokenized **by llama-server**
(`/apply-template`, `/tokenize`, `--jinja`), never by a HuggingFace tokenizer,
so one scorer drives any GGUF whatever its vocabulary. Bonsai 1 8B has 151k
tokens, Bonsai 2 27B has 248k, and `A` is a different id in each.

### Backends

| Backend | For | Notes |
|---|---|---|
| `llama.cpp` | any `.gguf` | default; CPU, Metal, CUDA, Vulkan |
| `mlx` | PrismML's MLX pack | native Apple Silicon, no server process. See [docs/MLX.md](docs/MLX.md) |
| `torch` | HuggingFace checkpoints | `logits_to_keep=1`, BF16, auto MPS/CUDA/CPU |

---

## Layout

```
openjev/    score.py  api.py  demo.py  ggufinfo.py  mlx_backend.py  examples/
bonzi/      chat.py                                 weights + runtimes
scripts/    build_llama_fork.sh  get_llama_cpp.sh  download_model.py
            benchmark.py  make_charts.py  stop_servers.sh
docs/       BUILD_NOTES.md  MLX.md  charts/
results/    benchmark.json + per-run JSONL
```

- [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md): measurements, the gotcha table, the corporate-proxy saga
- [bonzi/README.md](bonzi/README.md): the runtime/quantization compatibility matrix
- [openjev/README.md](openjev/README.md): the scorer in detail
- [CREDITS.md](CREDITS.md): who made what

## Reproducing the numbers

```bash
python3 scripts/download_model.py --list
python3 scripts/benchmark.py            # writes results/benchmark.json
python3 scripts/make_charts.py          # regenerates docs/charts/*.svg
```

Method: one fresh llama-server per (model, eval); a warmup pass that is **not**
measured, because the first questions pay for shader compilation, paging in
weights and filling the prompt cache; the same prompt and eval file for every
model; label-balanced eval sets so chance is `1/n_options`.

## Licence

MIT for the code here. Bonsai models are Apache 2.0 from PrismML and are **not
redistributed**. `download_model.py` fetches them from source. SemIf is MIT.
llama.cpp is MIT.
