<p align="center"><img src="https://raw.githubusercontent.com/robipop22/Jev-is-odd/main/assets/hero.png" alt="Jev is odd. One number. One decision. Seven dots: three pairs and one odd dot." width="100%"></p>

# jev-is-odd

A deliberately overengineered way to ask whether a number is odd. Send an integer to **Jev**, the decision model from [TypeSafe AI](https://typesafe.ai). Get a boolean back.

Inspired by [is-odd-ai](https://github.com/rhettlunn/is-odd-ai). Written in TypeScript, with ESM and CommonJS builds, typed answers, and a receipt for the tokens and time it took.

This is a playful AI experiment. Jev can get arithmetic wrong. For reliable, free parity checks, use `n % 2 !== 0`. This package always asks Jev and returns its decision; it never substitutes local arithmetic.

## Install

Requires **Node.js 20.19+** and a [Typesafe API key](https://typesafe.ai).

```sh
npm install jev-is-odd
```

## Ask Jev

Set `TYPESAFE_API_KEY` in your server environment. For local development, copy `.env.example` to `.env`, add the key, and run your example with `node --env-file=.env example.mjs`. The library itself does not load `.env` files.

```ts
import isOdd from 'jev-is-odd';

console.log(await isOdd(7)); // Jev's boolean decision
```

CommonJS works too:

```js
const { isOdd } = require('jev-is-odd');

isOdd(7).then(console.log);
```

Accepts safe integer numbers, `bigint`, and decimal integer strings:

```ts
await isOdd(-7);
await isOdd(0);
await isOdd(9007199254740993n);
await isOdd('900719925474099312345');
```

Decimals, `NaN`, infinities, unsafe JS numbers, whitespace, exponent/hex strings, and non-numeric strings are rejected **before making a request**. Leading signs and zeroes in integer strings are normalized. Passing a large integer precisely does not guarantee Jev classifies it correctly.

## Tokens, speed, and confidence

```ts
import { checkOdd } from 'jev-is-odd';

const result = await checkOdd(7, { model: 'jev-1.13.0' });
console.log({
  odd: result.isOdd,
  model: result.model,
  milliseconds: result.durationMs,
  inputTokens: result.usage.inputTokens,
  outputTokens: result.usage.outputTokens,
  confidence: result.confidence,
  probabilities: result.probabilities,
});
```

`checkOdd()` returns `input`, `isOdd`, `parity`, `confidence`, `probabilities`, `model`, `usage` (input/output/total tokens), `durationMs`, `startedAt`, `completedAt`, and an optional `requestId`.

Timing is measured on the client and includes network, full response delivery, and parsing. It is not GPU inference time. Usage comes from the successful provider response. If you enable retries, timing includes retry waits but usage does not include failed attempts. Confidence is the provider's score, not a correctness guarantee.

<!-- benchmark:start -->
![Live Jev benchmark: 20 of 20 cases correct, median 294.3 milliseconds](https://raw.githubusercontent.com/robipop22/Jev-is-odd/main/assets/metrics.png)

Measured **2026-09-18T12:32:40.152Z → 2026-09-18T12:32:47.089Z**, using **jev-1.13.0**.

| Measurement | Result |
| --- | ---: |
| Correct answers | 20/20 fixed cases |
| Median / p95 round-trip | 294.3 / 364.8 ms |
| Mean round-trip | 345.3 ms |
| Input / output tokens, all successful requests | 6,928 / 640 |
| Estimated successful-call cost, whole run | $0.00029098 |
| Request failures / not attempted | 0 / 0 |

Sequential calls, network included, no retries, and the first request retained. Timing covers successful responses, including any wrong answers. This is a small fixed sample; correctness and speed are not guaranteed for other inputs or runs. [Every request and the full method](https://github.com/robipop22/Jev-is-odd/blob/main/benchmarks/README.md).
<!-- benchmark:end -->

TypeSafe lists Jev 1.13 at **$0.042 per million input tokens**, with free output tokens ([source](https://docs.typesafe.ai/models), checked September 18, 2026). Estimated cost is `inputTokens × 0.042 / 1_000_000`. The benchmark applies this price only when the provider reports `jev-1.13.0`; this is an estimate, not an invoice.

## Options

Both functions accept the same optional second argument:

| Option | Default | Purpose |
| --- | --- | --- |
| `apiKey` | `TYPESAFE_API_KEY` | Explicit server-side credential |
| `model` | `jev-latest` | Model or alias; pin a version for reproducibility |
| `timeoutMs` | `10000` | Timeout for the full response, per attempt |
| `maxRetries` | `0` | Optional retries after the initial request |
| `signal` | — | `AbortSignal` for cancellation |
| `fetch` | global `fetch` | Custom transport for testing |

Every valid invocation makes an API call. There is no cache, local answer, or batch API. Errors reject the promise: input errors are `TypeError`/`RangeError`, invalid responses are `JevResponseError`, and network/auth/rate-limit errors retain the official SDK error types. An API failure is never returned as `false`.

Use this package on the server. A Typesafe key must not be bundled into browser code. Only `TYPESAFE_API_KEY` is inherited from the SDK environment; endpoint, logging, model, timeout, and retry defaults are explicitly configured by this package.

## Run the benchmark

```sh
cp .env.example .env
# Add your key to .env in an editor.
npm run benchmark
```

Runs 20 fixed integer cases sequentially, with no retries, cache, or discarded warmup requests. It verifies Jev's answers against `BigInt` arithmetic **in the benchmark only**, saves timestamped JSON and Markdown reports, updates this README, and generates `assets/metrics.svg` and `assets/metrics.png`. A wrong answer or failed/unattempted request makes the command exit nonzero **after saving the evidence**. To regenerate the report and images from the saved data without making API calls, run `npm run benchmark:render`.

Reports include per-request UTC timestamps, probabilities, confidence, token usage, duration, correctness, model, and provider request ID where available. Latency statistics cover successful requests, including incorrect answers. Failed requests have unknown token usage and are listed separately. This small sample is not proof of general accuracy or sustained throughput.

## Develop and release

```sh
npm ci
npm run check        # types, mocked transport tests, ESM/CJS builds
npm run test:package # install a real tarball and test both module/type formats
```

Tests do not use credentials or make inference requests. The tarball consumer check downloads the published TypeSafe SDK from npm. GitHub Actions runs these checks on Node 20, 22, and 24 when the repository is pushed. For repository metadata, hosted README images, and publication steps, see [RELEASING.md](https://github.com/robipop22/Jev-is-odd/blob/main/RELEASING.md).

## Artwork and credit

The [banner](https://raw.githubusercontent.com/robipop22/Jev-is-odd/main/assets/hero.png), [icon](https://raw.githubusercontent.com/robipop22/Jev-is-odd/main/assets/icon.png), and editable SVG sources are original artwork; see [asset notes](https://github.com/robipop22/Jev-is-odd/blob/main/assets/README.md). The seven-dot mark is three pairs plus one odd dot.

Built with the official [`@typesafe-ai/sdk`](https://github.com/typesafe-ai/typesafe-sdk-js). An independent experiment, not an official TypeSafe package. Inspired by the idea behind `is-odd-ai`; no source code was copied.

MIT © 2026 Robert Pop.
