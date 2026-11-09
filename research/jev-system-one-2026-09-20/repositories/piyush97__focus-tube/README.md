<p align="center">
  <img src="extension/icons/icon.svg" width="96" height="96" alt="FocusTube icon">
</p>

# FocusTube

**A distraction-free YouTube learning feed, powered by Jev from [TypeSafe AI](https://typesafe.ai).**

FocusTube is a Chrome and Firefox extension that transforms YouTube into a focused hub for coding, software engineering, technical interview preparation, academic study, and professional upskilling. It uses **Jev**, TypeSafe's fast System One model, to make typed relevance judgments for visible videos.

All YouTube Shorts are hidden. Entertainment and uncertain recommendations stay concealed; only videos whose Jev probability meets your chosen threshold are revealed.

## Why Jev?

Traditional keyword filters cannot reliably distinguish a substantive programming tutorial from tech entertainment or vague career content. FocusTube sends structured video metadata to TypeSafe and asks Jev one narrow `Noul` question per video: is this directly useful for focused learning or career upskilling?

Jev returns a typed probability rather than generated prose. FocusTube uses that probability directly in code:

```text
YouTube metadata → Cloudflare Worker → TypeSafe Jev → Noul probability → reveal or hide
```

- Model: `jev-latest`
- Primitive: TypeSafe `Noul`
- Default reveal threshold: `0.82`
- Maximum batch: 20 videos
- Cache duration: 7 days in the browser

## Features

- Filters YouTube home, search, and watch-page recommendations
- Hides Shorts and Shorts shelves without sending them to TypeSafe
- Prevents recommendation cards from flashing before classification
- Strict-by-default handling of uncertain results
- Adjustable probability threshold and instant pause control
- Local seven-day decision cache
- Chrome and Firefox Manifest V3 support
- Cloudflare Worker keeps the TypeSafe API key out of extension code
- Sends no cookies, account identity, watch history, comments, or transcripts

## Architecture

```text
┌─────────────────────────┐
│ Browser extension       │
│ title + channel + page  │
└────────────┬────────────┘
             │ authenticated batch
             ▼
┌─────────────────────────┐
│ Cloudflare Worker       │
│ validates + builds      │
│ typed Noul questions    │
└────────────┬────────────┘
             │ Jev evaluation
             ▼
┌─────────────────────────┐
│ TypeSafe System One     │
│ probability of “yes”    │
└────────────┬────────────┘
             │
             ▼
      Reveal or hide card
```

## Try locally

### 1. Configure the Worker

```bash
cd worker
cp .dev.vars.example .dev.vars
```

Edit `.dev.vars`:

```dotenv
TYPESAFE_API_KEY="your-typesafe-api-key"
FOCUSTUBE_TOKEN="a-long-random-token"
```

Then start Wrangler:

```bash
npm install
npm run dev
```

The Worker will be available at `http://127.0.0.1:8787`.

### 2. Load the extension

**Chrome**

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked** and choose `extension/`.

**Firefox**

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on**.
3. Choose `extension/manifest.json`.

Open FocusTube settings and enter:

- Worker URL: `http://127.0.0.1:8787`
- Extension token: the same `FOCUSTUBE_TOKEN` from `.dev.vars`

Refresh YouTube after saving.

## Deploy the Worker

```bash
cd worker
npm install
npx wrangler secret put TYPESAFE_API_KEY
npx wrangler secret put FOCUSTUBE_TOKEN
npm run deploy
```

Enter the deployed `https://…workers.dev` URL and token in FocusTube settings. Use a long random `FOCUSTUBE_TOKEN`; it prevents strangers from spending your TypeSafe quota. The TypeSafe API key remains in Cloudflare, while the extension token is kept in browser-local storage rather than sync storage.

## Classification policy

The Worker asks Jev whether each video is directly useful for:

- Programming and coding
- Software engineering, architecture, tooling, security, data, cloud, or AI engineering
- Coding interviews, system design interviews, and technical career preparation
- Academic study, tutorials, courses, lectures, and substantive explainers
- Professional skills with concrete instructional value

It asks Jev to reject entertainment, reactions, gaming, celebrity content, general tech news, product-launch hype, desk setups, unboxings, creator vlogs, vague motivation, and unclear educational value.

YouTube Shorts are detected locally and hidden before classification.

## Privacy and security

Only the video title, channel name, and surface (`home`, `search`, or `watch recommendations`) are sent to your Worker and then to TypeSafe. FocusTube never sends YouTube cookies, account details, history, comments, or transcripts.

Secrets are excluded from Git. Never commit `worker/.dev.vars`.

## Development

The extension has no build step. Reload the unpacked extension after editing it.

```bash
cd worker
npm run check
```

Extension artwork lives in `extension/icons/`. `icon.svg` is the source; browser-ready PNG sizes are included.

## Built with

- [TypeSafe AI](https://typesafe.ai) and the **Jev System One model**
- [Cloudflare Workers](https://workers.cloudflare.com)
- Browser Manifest V3 APIs

## License

MIT
