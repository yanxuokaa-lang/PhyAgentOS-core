# Focus — Jev-powered distraction blocker

Stay productive. **Focus** uses TypeSafe's **Jev System One classification model**
([docs](https://docs.typesafe.ai/concepts/system-one)) through
**OpenRouter's Decisions API** to decide whether a domain is distracting, and blocks it.

## How it works

1. On each top-frame navigation (`webNavigation.onBeforeNavigate` + `tabs.onUpdated`
   fallback for SPAs), the background service worker extracts the domain.
2. Allowlist / blocklist overrides win first. Fresh cached verdicts (7 days) win second.
3. Otherwise it calls Jev via OpenRouter:

```http
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
```

```json
{
  "model": "typesafe/jev-1.13",
  "state": "Domain: youtube.com\nFull URL: https://www.youtube.com/\nPage title: YouTube\nUser goal: stay productive…",
  "questions": {
    "site_category": {
      "type": "choice",
      "instructions": "Is visiting this website productive for focused work, or is it distracting?",
      "criteria": {
        "productive": "Work, study, documentation, coding, email, calendar, maps, …",
        "distracting": "Social media feeds, short-video doomscrolling, entertainment, gaming, gambling, …"
      }
    }
  }
}
```

4. If `answers.site_category.choice === "distracting"` and
   `P(distracting) >= threshold` (default 0.6), the tab is redirected to
   `blocked.html`, which shows the probability, confidence, and model.
5. Without an API key (or if the API fails), a small offline heuristic list
   keeps the extension useful until you configure a key.

This mirrors the TypeSafe `POST /v1/systemone` shape (`{ state, model, questions }`
with a `Choice` classification primitive); OpenRouter just serves it at
`/api/alpha/decisions` with OpenRouter auth.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | MV3 manifest (Chrome + Firefox), permissions, options page |
| `background.js` | Navigation interception, Jev classification, caching, blocking |
| `popup.html` / `popup.js` | Toolbar popup: current-site verdict, enable toggle, allow/block, re-check |
| `options.html` / `options.js` | **Extension dialog: OpenRouter API key**, model, threshold, lists, cache |
| `blocked.html` / `blocked.js` | Block interstitial with allow-once / always-allow |
| `styles.css` | Shared dark theme |
| `icons/` | Extension icons |

## Install (Chrome / Edge / Brave)

1. Open `chrome://extensions`, enable **Developer mode**.
2. **Load unpacked** → select this `Focus` folder.
3. Click the 🎯 toolbar icon → **Settings & API key**.
4. Paste your OpenRouter key (from `openrouter.ai → Keys`) → **Save settings** → **Test API key**.
5. Browse. Distracting domains redirect to the Focus blocked page.

## Install (Firefox)

1. Open `about:debugging#/runtime/this-firefox` → **Load Temporary Add-on** → pick `manifest.json`.
2. Open Add-ons → Focus → **Preferences** to set the API key.

## Configure

- **Model:** `typesafe/jev-1.13` (pinned, default) or `~typesafe/jev-latest` (auto-update).
- **Threshold:** minimum `P(distracting)` to block. Lower = stricter.
- **Allowlist / blocklist:** one domain per line, `www.` stripped, subdomains match.
- **Cache:** per-domain verdicts cached 7 days; "allow once" caches 1 hour.

## Privacy

- The API key is stored in `chrome.storage.sync` and sent only to `https://openrouter.ai`.
- Each new domain sends `{ domain, full URL, page title }` as Jev `state`. No page content is sent.
