# Jev Academy

Public zero-to-hero walkthrough for TypeSafe **System One** (Jev), maintained for Brandon Theriot.

Not affiliated with or endorsed by TypeSafe. Content cites [docs.typesafe.ai](https://docs.typesafe.ai/llms.txt).

## Local run

```bash
cd site   # if monorepo layout
npm install
npm run dev
```

Open http://localhost:3000.

## Environment

Labs are **copy-paste only**. This site never stores or displays API keys.

On your machine (and in product repos), set:

```bash
export TYPESAFE_API_KEY=...   # from https://console.typesafe.ai/settings/keys
```

Verify without printing the secret:

```bash
echo "length=${#TYPESAFE_API_KEY}"
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  https://api.typesafe.ai/v1/models
```

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Next.js dev server |
| `npm run build` | Production build |
| `npm start` | Serve production build |

## Deploy on Vercel (free)

1. Import `Btheriot83/jev-academy` (or this fork) in Vercel.
2. Root directory: `site` if the Next app lives in `/site`, otherwise repo root.
3. Framework preset: Next.js. Build: `npm run build`. Output: default.
4. **No env vars required** for the public UI (lessons, labs snippets, gallery).
5. Deploy.

Optional later: server-side lab runners would need `TYPESAFE_API_KEY` as a **server** env var — never `NEXT_PUBLIC_*`.

## Routes

| Path | Purpose |
|------|---------|
| `/` | Pitch + 0→7 checklist + next action |
| `/lessons` | 12-step curriculum |
| `/lessons/[slug]` | Lesson body + citations |
| `/labs` | curl + JS labs |
| `/use-cases` | Gallery (X-cited first, then docs) |
| `/ship` | Ship-into-repo checklist |

Progress toggles use `localStorage` only.
