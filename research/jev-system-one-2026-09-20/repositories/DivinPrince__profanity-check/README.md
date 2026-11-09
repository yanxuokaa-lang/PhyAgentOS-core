# Profanity check

Vite + React demo. Type a sentence, click **Profanity check**, and the app asks TypeSafe Jev whether that sentence contains profanity.

The browser never sees the API key. `POST /api/check` runs in a Vite server plugin (`server/plugin.ts`), which calls TypeSafe and returns a verdict plus a 0–1 score.

## Run it

```sh
cp .env.example .env
```

Put a TypeSafe key in `.env`:

```
TYPESAFE_API_KEY=apikey_...
```

Do not name it `VITE_TYPESAFE_API_KEY`. Vite exposes `VITE_*` variables to the browser. This app loads `TYPESAFE_API_KEY` in `vite.config.ts` and only uses it on the server.

Get a key from the [TypeSafe dashboard](https://console.typesafe.ai). Docs: [https://docs.typesafe.ai/](https://docs.typesafe.ai/).

```sh
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## API

```http
POST /api/check
Content-Type: application/json

{ "text": "this is definitely not a swear word" }
```

200:

```json
{ "verdict": "clean", "score": 0.03 }
```

`score` is a TypeSafe noul: probability the text contains profanity, from `0` (no) to `1` (yes). Higher is worse.

Verdicts are decided in `server/evaluate.ts`, not by the model:

| verdict  | rule                         |
| -------- | ---------------------------- |
| `clean`  | `score < 0.2`                |
| `review` | `0.2 ≤ score < 0.7`          |
| `flagged`| `score ≥ 0.7`                |

Error responses look like `{ "error": "..." }`:

| status | when                                      |
| ------ | ----------------------------------------- |
| 400    | missing/empty `text`, or body is not JSON |
| 405    | method is not POST                        |
| 500    | `TYPESAFE_API_KEY` is missing             |
| 502    | TypeSafe request failed                   |

`vite preview` serves the same `/api/check` plugin.

## Layout

```
src/App.tsx          UI: input, red button, dashed result box
src/api.ts           fetch('/api/check')
src/types.ts         CheckResult { verdict, score }
server/plugin.ts     Vite middleware for POST /api/check
server/evaluate.ts   TypeSafe systemOne call + score thresholds
vite.config.ts       loads TYPESAFE_API_KEY, registers the plugin
.env                 local key (gitignored)
.env.example         empty key template
```

## Scripts

```sh
npm run dev       # http://localhost:5173
npm run build     # typecheck + production bundle
npm run preview   # serve dist, including /api/check
npm run lint      # oxlint
```
