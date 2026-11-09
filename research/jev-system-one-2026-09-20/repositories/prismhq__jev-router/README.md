# jev-router

Open-source LLM router. Clients send one model id; **Jev** (TypeSafe's System One
model) picks which model serves each request.

Transport is [LiteLLM](https://github.com/BerriAI/litellm), so the router can
route across [OpenRouter](https://openrouter.ai) or any provider LiteLLM
supports. You bring your own keys.

- **Works with no third-party decision model**: without a TypeSafe key, a
  cheapest-eligible baseline runs by default.
- **Optional Jev**: set `TYPESAFE_API_KEY` and Jev makes the routing call.
- **OpenAI-compatible**: point any client at the proxy and use
  `model: "jev-router"`.
- **Capability-aware**: image and output-length requirements filter the
  candidates before any decision is made.

## Quickstart

```bash
pip install "litellm[proxy]" pyyaml

export OPENROUTER_API_KEY=sk-or-...
# optional — enables Jev routing instead of the baseline
export TYPESAFE_API_KEY=...

litellm --config config.yaml --port 4000
```

Then call it like any OpenAI endpoint:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-jev-router" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jev-router",
    "messages": [{"role": "user", "content": "refactor the auth module"}]
  }'
```

The response `model` field reports the model that served the request.

## How it works

1. The pre-call hook in `jev_router/hook.py` sees requests for `jev-router`.
2. It builds a minimized summary of the request (recent messages' roles and
   truncated text, plus image/tool signals).
3. `eligible()` filters the candidates in `router.yaml` to models that can serve
   the request (vision, output length, tools).
4. The decider picks one: `JevDecider` if `TYPESAFE_API_KEY` is set, else
   `RulesDecider` (cheapest eligible).
5. Any failure falls back to `fallback` in `router.yaml`.

## Configuration

Two files:

- **`config.yaml`** — the LiteLLM proxy: `model_list` (the pool), plus the hook
  registration. Edit the OpenRouter slugs to match the models you want.
- **`router.yaml`** — the routing policy: candidates with descriptions Jev reads,
  capability flags, prices, the fallback, and Jev settings. Candidate `name`s
  must match `model_list` entries.

## Privacy

Routing sends a minimized summary of the request to TypeSafe, a third party, when
`TYPESAFE_API_KEY` is set. Don't enable Jev for workloads that can't share context
with another provider. Without a TypeSafe key, routing stays local.

## Status

Experimental. APIs and config will change.

## License

MIT
