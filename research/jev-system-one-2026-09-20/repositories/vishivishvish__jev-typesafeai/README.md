# jev-typesafeai

A minimal client for TypeSafe AI's Jev model (`POST /v1/systemone`), used from
Claude Code.

## Background

This repo originally targeted the Claude Code compaction hooks
(`PreCompact`/`PostCompact`) to replace the default lossy summary with
verbatim, selective deletion scored by Jev. That turned out not to be
possible: those hooks are purely observational — they receive
`session_id`/`transcript_path`/`reason` and can only emit a cosmetic
`systemMessage`/`terminalSequence`; they cannot influence, block, or
rewrite what gets compacted, and the transcript file is explicitly
documented as not safe to write to.

The reusable pieces from that attempt — a correct Jev API client and a
couple of token-budget helpers — are kept in `src/`. The next direction is
using Jev as a classifier inside hooks that actually support decision
control, such as `PreToolUse` (risk-gate a tool call) or `UserPromptSubmit`
(classify/route a prompt, inject context).

## Layout

```
src/client.ts   Jev API client: askNoulBatch(apiKey, model, state, questions)
src/state.ts    estimateTokens, abridge — generic token/text-budget helpers
tests/          vitest unit tests
```

## Setup

```bash
npm install
cp .env.example .env   # fill in TYPESAFE_API_KEY
```

## Development

```bash
npm run typecheck
npm test
```

## Pending - 9 use cases for Jev (System 1 Model):

From a Tweet

- Re-ranking: Score and reorder retrieved results by relevance.
- Tool pruning: Drop unused tools during context compaction.
- Model routing: Route tasks to small, medium, or large LLMs.
- Query routing: Decide between SQL, Vector DB, or Graph DB.
- Cache admission: Filter which responses are worth caching.
- Cache TTL prediction: Estimate how long cached results stay valid.
- RAG retrieval control: Gate irrelevant retrieved documents.
- Human escalation: Know when to hand off from AI to a human.
- Action selection: Score and pick the best next agent action.
