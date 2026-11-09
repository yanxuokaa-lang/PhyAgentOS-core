# jev-tree

**Recursive Jev choice over a taxonomy.** TypeSafe’s Jev can only list **255 options in one choice question**. Real catalogs are bigger. `jev-tree` walks a JSON shape and calls Jev once per level (or per partition) so you can select among thousands of leaves.

Same stack as [jevlogs](https://github.com/reachjalil/jevlogs): `typesafe-ai/jev` through Vercel AI Gateway, `ai@7.0.105`, Node.js 22+, MIT.

<p>
  <a href="https://www.npmjs.com/package/jev-tree"><img src="https://img.shields.io/npm/v/jev-tree?style=flat-square&color=2448ff" alt="npm version" /></a>
  <a href="https://github.com/reachjalil/jev-tree/actions/workflows/ci.yml"><img src="https://github.com/reachjalil/jev-tree/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI" /></a>
  <a href="https://github.com/reachjalil/jev-tree/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2448ff?style=flat-square" alt="MIT" /></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-%E2%89%A522-11131b?style=flat-square" alt="Node 22+" /></a>
</p>

[Guide](docs/guide.md) · [API](docs/api.md) · [Explainer](https://reachjalil.github.io/jev-tree/) · [20s intro](https://reachjalil.github.io/jev-tree/jev-tree-intro.mp4) · [Dataset](https://huggingface.co/datasets/reachjalil/jev-tree-choice-cap)

There is no marketing site. This repo is the product. The explainer is a 20-second film plus a click-through essay, not a dashboard.

## Why

A flat `choice` with 1,000 SKUs, incident types, or workflow ids does not fit. Truncating to 255 **drops the tail** (in our bake-off, all of Cape Town). Splitting the catalog into a **tree** — and auto-bucketing oversized sibling lists — makes each call a short, precise question.

Default **32 options per call**. Raise `maxFanout` up to 255.

## Install

```sh
npm install jev-tree
```

Live calls need `AI_GATEWAY_API_KEY` (Vercel AI Gateway). Not an OpenAI key.

`0.1.0` is the first real release (`latest`). Ignore any `placeholder` tag. How we publish: [docs/release.md](docs/release.md).

## Shape

```ts
type TreeNode = {
  id: string;
  label: string;
  description?: string;
  children?: TreeNode[];  // branch
  value?: unknown;        // returned when this leaf is selected
};
```

A node with no `children` (or an empty array) is a leaf. Pass one root, a forest (`TreeNode[]`), or `{ "shape": ... }` in a JSON file. Ids must be unique. `__root` is reserved.

Your ids need not be legal Jev choice keys. The library sends `o0`, `o1`, … and maps back.

## Use

```ts
import { createJevTree } from 'jev-tree';

const tree = createJevTree({ maxFanout: 32 });
const result = await tree.select({
  state: 'Replica lag 47m on primary still accepting writes',
  question: 'Which incident type is this?',
  shape: {
    id: 'incidents',
    label: 'incidents',
    children: [
      { id: 'payments', label: 'payments', children: [/* … */] },
      { id: 'data', label: 'data', children: [
        { id: 'replica_lag', label: 'multi-minute replica lag', value: { queue: 'sev1' } },
      ]},
    ],
  },
});

result.ids;         // ['incidents', 'data', 'replica_lag']
result.value;       // { queue: 'sev1' }
result.reason;      // 'model' | 'unavailable'
```

A **flat list of 300+ leaves** is fine. Siblings above `maxFanout` are partitioned into labeled buckets (`first … last`), Jev picks a bucket, then the walk continues. You never send more than `maxFanout` criteria in one `experimental_evaluate` call.

Timeouts and provider failures return `reason: 'unavailable'` and **do not invent a leaf**.

## CLI

```sh
npx jev-tree                         # offline demo, no key
npx jev-tree --live --shape taxonomy.json --state "the record"
npx jev-tree --count --shape taxonomy.json
```

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `maxFanout` | `32` | Options per Jev call; integer 2–255 |
| `timeoutMs` | `8000` | Per-call abort; timeouts do not retry |
| `maxDepth` | `16` | Stop and mark unavailable |
| `maxCalls` | `64` | Stop and mark unavailable |
| `instructions` | (built-in) | Prepended to every choice |
| `evaluator` | Gateway Jev | Inject a fake chooser in tests |
| `validate` | `true` | `parseShape` before walking |

## Evidence

320-leaf multi-region incident catalog, 180 labeled tickets, live Jev on Vercel AI Gateway with ZDR. Truncating to 255 gets **0% of the tail**. The authored tree recovers it.

- Dataset: [reachjalil/jev-tree-choice-cap](https://huggingface.co/datasets/reachjalil/jev-tree-choice-cap)
- Write-up: [`docs/article/jev-tree-choice-cap.md`](docs/article/jev-tree-choice-cap.md)
- Click the wall: [jev-tree explained](https://reachjalil.github.io/jev-tree/)

Synthetic. Seed `20260917`. Not production tickets. Confirm spend on the Gateway dashboard.

## What this is not

Not a host for Jev. Not a substitute for a well-authored taxonomy — explicit branches beat a 10,000-item flat list. Auto-partition is the fallback when a node has too many children.

Independent project. Not affiliated with TypeSafe or Vercel. The hosted model is TypeSafe’s Jev via AI Gateway.

## License

MIT
