# jevd

An inference server for [openjev](https://huggingface.co/AlexWortega/openjev), a small
NLI cross-encoder: premise and hypothesis in, probabilities over `contradiction` /
`entailment` / `neutral` out.

One primitive, no task-specific training, and cheap enough to sit in a hot path. It is
a good enough decision engine that you can rank, route, gate and grade with it instead
of prompting a chat model and hoping.

```sh
openjev serve
```

First run says what it is about to download and how big it is *before* it downloads
anything. The server reports *downloading* and *loading* as different states, so a
supervisor cannot kill a slow model load.

| crate | what |
| --- | --- |
| `openjev-core` | model acquisition, device selection, inference. `predict` / `rerank` / `grade` |
| `openjev-cli` | the `openjev` binary and the HTTP API |

## Speaks System One

`POST /v1/systemone` serves [TypeSafe's System One
shape](https://typesafe.ai/blog/introducing-system-one-models-and-jev): one unstructured
`state`, a map of typed questions, typed answers, no free-form text. Tools already written
against that API — TypeSafe's own clients, the `jev-model-router` and
`fast-jev-compaction` Claude Code mods — work against a local server **by changing a base
URL**, with no code change and nothing leaving the machine.

```sh
curl -s http://127.0.0.1:21131/v1/systemone \
  -H "Authorization: Bearer $OPENJEV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openjev",
    "state": "My card was charged twice. Please help ASAP.",
    "questions": {
      "urgent": {
        "type": "noul",
        "instructions": "Does this message convey urgency?",
        "criteria": { "true": "Explicitly time-sensitive", "false": "No urgency expressed" }
      },
      "team": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
          "billing": "Payments and refunds",
          "technical": "Bugs and integrations",
          "sales": "Pricing and new accounts"
        }
      }
    }
  }'
```

```json
{
  "model": "openjev",
  "answers": {
    "team": {
      "type": "choice",
      "choice": "billing",
      "probabilities": { "billing": 0.97, "sales": 0.02, "technical": 0.01 },
      "confidence": 0.97
    },
    "urgent": { "type": "noul", "noul": 0.98 }
  },
  "usage": { "input_tokens": 376, "output_tokens": 0, "cost": 0 },
  "id": "gen-dec-1789877520-GOYwpkAlDDl56SCVRKYj",
  "provider": "openjev"
}
```

On loopback with no token configured, the `Authorization` header is optional and a bearer
is accepted if you send one — the same auth as every other route, not a second path.

| type | ask with | answered with |
| --- | --- | --- |
| `noul` | `instructions`, optional `criteria.{true,false}` | `noul` — a probability in [0,1] |
| `choice` | `criteria`: key -> description, two or more | `choice`, `probabilities`, `confidence` |
| `score` | `criteria`: an ordered array of rubric levels, lowest first | `score` in [0, levels-1], `legend`, `probabilities`, `confidence` |
| `boolean` | the Vercel AI Gateway's name for `noul` | `probability` |

Each question becomes one entailment check per criterion, against the `state` as premise;
`choice` normalises those over its keys, `score` takes their expected index, and `noul`
contests `true` against `false` when both are described. `docs/adr/0018` says why, and
what an irrelevant or self-contradictory question does.

**Three deliberate differences from TypeSafe, all in the direction of not lying:**

* `provider` is `"openjev"`, never `"TypeSafe"`. A field that says who answered must say
  who answered; a client branching on it would otherwise be branching on a forgery.
* `usage.output_tokens` is always `0` — a cross-encoder emits no tokens — and `cost` is
  always `0`, because this runs on your machine. `input_tokens` is real, counted by the
  encoder that ran.
* Errors use this server's one envelope, `{"error":{"code":...}}`, with `code` as the
  contract. A choice with one option, empty criteria, an unknown type, too many questions
  or an over-long state are each their own code and a clean 4xx — never a confident
  answer. `/v1/info` lists the limits.

See `docs/adr/0017` for what was verified against the published spec versus assumed.

## Engine

llama.cpp as the trunk only — hidden states out — with the three-label head applied in
Rust from a small safetensors. Keeping the classifier out of GGUF means every backend's
contract is one method, `forward(batch) -> last hidden state`, and everything else is a
free function that backends cannot disagree about.

CPU, Metal, CUDA, Vulkan and ROCm are cargo features over one codebase. The device is
detected, with an explicit override and a logged demotion chain; a device whose backend
was not compiled in fails loudly naming the missing feature rather than quietly falling
back.

**A model is config, not code.** An embedded registry plus `~/.config/openjev/models.toml`
carries the repo, revision, template, label map, tokenizer and head shape, so a different
checkpoint — or later a different architecture — is an edit, not a release.

## Verified

100% label agreement (35/35) against reference `transformers` outputs at every
quantisation level, with token ids matching exactly. Q8_0 is both the most accurate quant
and the fastest, so there is no accuracy/speed trade to make.

See `STATUS.md` for the numbers, `docs/design/` for the decisions and what each is
organised against, and `docs/adr/` for how they changed.

## Using it

The HTTP API is the whole interface. Nothing in the engine knows about any particular
client.

A Herdr plugin was built on it — a three-way dispatcher that answers decision-shaped
tasks locally, routes the rest to an agent at the right model tier, and passes anything
uncertain straight through. It lives outside this repo; the engine deliberately carries
no knowledge of it.

MIT.
