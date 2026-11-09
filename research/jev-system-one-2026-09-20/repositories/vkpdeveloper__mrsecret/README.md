# Mr. Secret

A Chrome MV3 extension that blurs secrets and PII on any web page — useful when screen sharing, streaming, or recording demos.

## How it works

Two detection layers run in the page:

1. **Regex layer** (deterministic, instant): API keys (`sk-…`, `AKIA…`, `ghp_…`, `xoxb-…`, `AIza…`, `glpat-…`, Stripe, HF, private-key blocks), JWTs, emails, IBANs, Luhn-valid card numbers, phone numbers, and generic high-entropy tokens (Shannon entropy > 3.5).
2. **AI layer**: short "value-like" text snippets that regex can't judge (names, org/workspace names, account IDs, balances) are sent to the [TypeSafe AI](https://typesafe.ai) **Jev** classifier, which returns a probability that each snippet is private. Anything ≥ your threshold gets blurred.

Blurring wraps the exact matching substring in a blurred `<span>` — the rest of the page stays readable. Hover a blurred region to reveal it (toggleable). A MutationObserver keeps scanning as the page changes, and `<input>` values containing keys are blurred too.

### Privacy

- Only short text snippets (2–200 chars, < 12 words) plus a ~160-char context window are sent to TypeSafe — never whole pages.
- All API calls go through the extension's service worker; the page never sees your key.
- Your API key is stored in `chrome.storage.local` only. Classification verdicts are cached persistently in `chrome.storage.local` (never leaves the browser), so repeat visits cost zero tokens. Decisive verdicts are reused across contexts; borderline ones are keyed to their exact context.

## Install

```bash
npm install
npm run build
```

Then open `chrome://extensions`, enable Developer mode, **Load unpacked** → `.output/chrome-mv3`.

Open the popup, paste your TypeSafe API key, and you're set. Try `demo/index.html` (serve it over HTTP, e.g. `python3 -m http.server`) for a test page.

## Settings

- Master enable/disable, per-site disable, rescan
- AI classifier on/off + API key
- Sensitivity threshold (0.4–0.95), with optional per-site overrides
- Hover-to-reveal

## Dev

```bash
npm run dev       # WXT dev server with HMR
npm run build     # production build → .output/chrome-mv3
npm run compile   # typecheck
npm test          # vitest (detectors + candidates)
node scripts/gen-icons.mjs   # regenerate icons
```
