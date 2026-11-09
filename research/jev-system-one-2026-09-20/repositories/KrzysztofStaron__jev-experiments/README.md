# jev-experiments

TypeSafe Jev experiments via Vercel AI Gateway.

1. **Pixel image** (`src/exp-image`) — Score gray / B&W per pixel → PNG under `out/`
2. **Memory filter** (`src/exp-memory`) — Base LLM vs Base+Jev relevance filter → table + `evals/memory-bench.jsonl`

## Setup

```bash
pnpm install
```

Live runs need `AI_GATEWAY_API_KEY` (PowerShell: load from `~/.vercel-ai-gateway.env` only — never commit it):

```powershell
Get-Content $env:USERPROFILE\.vercel-ai-gateway.env | ForEach-Object {
  if ($_ -match '^AI_GATEWAY_API_KEY=(.+)$') { $env:AI_GATEWAY_API_KEY = $Matches[1] }
}
```

## Experiment 1 — Pixel

```bash
pnpm exp:image --mock --prompt "white circle on black" --size 16
pnpm test:dry
# live:
pnpm exp:image --prompt "white circle on black" --size 16
```

Verify: PNG + JSON under `out/`.

## Experiment 2 — Memory

```bash
pnpm exp:memory --mock
# live:
pnpm exp:memory
```

Verify: Base vs Base+Jev comparison table printed; row appended to `evals/memory-bench.jsonl`.

## Notes

- Mock mode: `--mock` and/or `JEV_MOCK=1` (set `$env:JEV_MOCK=1` in PowerShell).
- Two Jev helpers currently coexist: `src/jev.ts` (pixel) and `src/lib/jev.ts` (memory). Safe to merge as-is; unify later if desired.
- Do not expand into graph-llm.