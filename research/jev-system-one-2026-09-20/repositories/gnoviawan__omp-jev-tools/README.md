# omp-jev-tools

Native [omp](https://github.com/can1357/oh-my-pi) extension: TypeSafe ([Jev](https://typesafe.ai)) judgment tools.
Small units of AI intelligence — typed answers and calibrated probabilities — usable as programming primitives inside OMP.

## Tools

| Tool | What it does | Pattern from TypeSafe docs |
|---|---|---|
| `jev_judge` | One request, a map of typed questions (noul/choice/score). Independent questions run in parallel in a single call. | [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md) — 10× cheaper, 10× faster than separate calls |
| `jev_route` | Pick one handler from a defined set + ACT/CONFIRM/ESCALATE gate from confidence. | [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing.md) |
| `jev_rerank` | Rank candidate texts against a query in one call; keep top-k. Massive token savings before feeding context. | [Re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md) |
| `jev_verify` | Check a claim against its evidence: supports/contradicts/insufficient + verbatim check + misleading score. | [Citation check](https://docs.typesafe.ai/cookbooks/citation_check.md) |
| `jev_models` | List TypeSafe models on the key. | — |

Plus `/jev` slash command for quick yes/no judgments: `/jev is this urgent? <text>`.

## Install

Requires an omp plugin-ready setup and a TypeSafe API key.

### Via omp plugin install (npm)

```bash
omp plugin install omp-jev-tools
```

### Via link (dev)

```bash
git clone https://github.com/gnoviawan/omp-jev-tools
cd omp-jev-tools
omp plugin link .
```

### Manual (user extension)

```bash
cp -r . ~/.omp/agent/extensions/omp-jev-tools
```

## Setup

```bash
# add to ~/.omp/agent/.env
TYPESAFE_API_KEY=apikey_...
# optional
TYPESAFE_MODEL=jev-latest
```

Key stays in the omp env layer; it is never stored inside the plugin.

## Use

Ask OMP naturally:

- "Rerank these grep results with jev_rerank and keep the top 3"
- "Route this support ticket with jev_route"
- "Verify this quote with jev_verify against the source doc"
- `/jev is this urgent? Help, my payouts have been failing for 3 days`

## License

MIT
