# TypeSafe Cookie Consent

A Chrome extension that reads every cookie banner and popup the way a person would, decides which button declines without agreeing, and clicks it. "Reject all" over "Accept all". "No thanks, I don't want to save money" over "Claim discount". When the reject button is hidden behind "Cookies Settings", it opens the settings and rejects there.

There are no filter lists and no vendor rules. The only semantic call is made by [Jev](https://typesafe.ai), TypeSafe's System One decision model: it is shown the overlay's text and its button labels and answers four typed questions in about 400 ms for about $0.00003. Everything else is plain code.

Made by [@mtropolis_chris](https://x.com/mtropolis_chris). MIT.

> **Disclaimer.** This is a fun, experimental project. It costs API tokens (a heavy browsing day is a cent or two), it can misjudge, and it does not replace Consent-O-Matic, "I still don't care about cookies" or uBlock's annoyance lists. It never touches dialogs about your own actions (confirmations, unsaved changes, checkout, age gates): that is a hard rule, not a preference. It is not a privacy tool. It is a demonstration that a decision model can replace a rule list, and it happens to be useful.

## Bring your own key

The extension has no backend. You paste a TypeSafe API key into the popup; it is stored in `chrome.storage.local` and only ever sent to `https://api.typesafe.ai`. The key never enters a page: only the extension's service worker talks to the API. Get a key at [typesafe.ai](https://typesafe.ai).

## How it works

1. **Find candidates.** A content script (in every frame) watches the DOM for overlays: `dialog` / `role=dialog` / `aria-modal` elements, fixed or sticky elements that cover a meaningful part of the viewport or span it as a bar, and boxes sitting on a dimming backdrop. Ordinary page content (anything containing `main`, `article`, an `h1`, or with no readable text) is never a candidate. See [`src/detect.ts`](src/detect.ts).
2. **Describe compactly.** Each candidate becomes a small state object: its visible text (at most 600 characters), up to eight button labels keyed `B0…Bn`, its position in words ("fixed bottom bar", "centered over a dark backdrop"), and the page's hostname. Words, not pixels, because decision models are weak with numbers. See [`src/extract.ts`](src/extract.ts).
3. **Judge.** The service worker sends one request per candidate to Jev with four questions in parallel ([`src/jev.ts`](src/jev.ts)): what *kind* of overlay this is (consent banner, marketing popup, wall, user-action dialog, regular page UI); which button *declines*; which button opens the *settings* layer; and whether it is an *interruption* that is safe to dismiss (a yes/no probability).
4. **Act.** A pure rule table ([`src/decide.ts`](src/decide.ts)) turns the answers into one action. Interruption below 0.5, user-action dialogs and page UI are always ignored. Consent banners and marketing popups: click the decline button when Jev is confident (≥ 0.7); otherwise open the settings layer once and judge that; otherwise click a label that reads like "reject" or "only necessary"; otherwise a plain ×; and only when Jev is sure of the kind and nothing honest exists, remove the element. Walls (paywalls, login walls) are left alone unless you turn on "close walls with a plain ×". After acting, scrolling is restored and orphaned backdrops are removed.

The two-layer flow is the part rule lists can't do: on a OneTrust banner that only offers "Accept All Cookies" and "Cookies Settings", Jev answers *decline: none, settings: Cookies Settings*; the extension clicks Settings, the preference centre appears, Jev is asked again and answers *decline: Reject All*, and that gets clicked. About two seconds end to end.

## Install

1. `git clone https://github.com/chrisXchen/typesafe-cookie-consent && cd typesafe-cookie-consent && npm install && npm run build`
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, choose the `dist/` folder.
3. Click the extension's icon, paste your TypeSafe API key, press **Test**. It sends one trivial question and shows the latency.
4. Browse. The badge on the icon counts what was declined on the current tab; the popup's log shows every action with the three judgments behind it.

Works in Chrome, Edge and Brave (Manifest V3, Chrome 116+). Not Firefox yet.

## Popup options

| Option | Default | What it does |
|---|---|---|
| Mode: **Auto** | on | Judge and click. A small toast says what was clicked, how long Jev took and what it cost. |
| Mode: **Ask** | | Judge, outline the element and the button it would click, and wait for you to press the pill. |
| Mode: **Highlight** | | Judge, outline the element with the kind, probabilities and intended action, never act. Debug and demo. |
| Mode: **Off** | | Content script idle. |
| Pause on *site* | | Per-site off switch. Takes effect immediately. |
| Show readout | off | A monospace readout in the bottom-right corner: judged, declined, last latency, session cost. Made for filming. |
| Toasts | on | The pill after each action. |
| Animation | on | The mark → point → click → collapse sequence. Off means click immediately. `prefers-reduced-motion` is respected either way. |
| Marketing popups | on | Also handle newsletter, discount, notification and app-install nags. Off means consent banners only. |
| Close walls with a plain × | off | Paywalls, login walls and soft "sign up to keep reading" walls: click their × if there is one, never hide them. |

The log keeps the last 100 actions (site, kind and its probability, label clicked, decline probability, interruption probability, latency, tokens) and can be exported as JSON.

## What leaves your browser

For each overlay, exactly this, to `api.typesafe.ai` and nowhere else:

```json
{
  "element_text": "We value your privacy. We and our partners store and access information on your device …",
  "buttons": ["B0: Accept all", "B1: Manage preferences", "B2: Reject all"],
  "position": "fixed bottom bar",
  "site": "theguardian.com"
}
```

Not the URL, not the page, not what you typed, not the rest of the DOM. There is no server of ours and no telemetry. A runtime check in [`src/jev.ts`](src/jev.ts) refuses to send any object with other keys or with numbers in the position, and a unit test covers it. Judgments are cached for the browser session per site and banner, so the same banner on the next page of the same site costs nothing.

Chrome will warn that the extension "can read and change all your data on all websites". That is what a content script on every page means; the paragraph above is the whole story of what it does with it.

## Testing without installing

```bash
cp .env.example .env        # add TYPESAFE_API_KEY (used by scripts only)
npm test                    # rule table and extraction helpers, no network
npm run live-check          # judges every fixture against the real API and prints the table below
npm run e2e                 # Playwright loads dist/ as an extension and runs every fixture
npm run scout -- https://stackoverflow.com   # Highlight mode on a real site: screenshot + judgments
npm run demo                # opens a real Chrome window with the extension for a live tour
```

`fixtures/` holds one self-contained page per overlay pattern: OneTrust two-layer, Sourcepoint modal with a second layer, Cookiebot bar, a Didomi-style banner inside an iframe, a Klaviyo-style discount modal, a newsletter modal whose × sits outside the box, a notification nag, a soft wall, and four that must be left alone (hard paywall, unsaved-changes dialog, age gate, a control page with sticky nav, share bar and chat widget), plus German and French banners.

Live check, 2026-09-18 (`npm run live-check`; walls option on):

| Fixture | Buttons | kind | decline | settings | interruption | action | ms |
|---|---|---|---|---|---|---|---|
| onetrust-two-layer | Cookies Settings / Accept All Cookies | consent_banner 1.00 | none 0.74 | Cookies Settings 1.00 | 0.75 | open_settings "Cookies Settings" | 458 |
| sourcepoint-modal | Yes, I'm happy / Manage my choices / Do not sell or share… | consent_banner 1.00 | Do not sell… 0.57 | Manage my choices 1.00 | 0.64 | open_settings "Manage my choices" | 295 |
| cookiebot-bottom | Deny / Allow selection / Allow all | consent_banner 1.00 | Deny 1.00 | Allow selection 0.81 | 0.71 | click "Deny" | 349 |
| didomi-frame | Disagree and close / Learn more / Agree and close | consent_banner 1.00 | Disagree and close 1.00 | Learn more 0.85 | 0.75 | click "Disagree and close" | 156 |
| discount-modal | CLAIM DISCOUNT / No thanks, I don't want to save money / × | marketing_popup 1.00 | No thanks… 0.97 | none 0.93 | 0.91 | click "No thanks, I don't want to save money" | 219 |
| newsletter-modal | Subscribe / × | marketing_popup 1.00 | × 0.99 | none 0.95 | 0.92 | click "×" | 194 |
| notification-nag | Later / Allow | marketing_popup 1.00 | Later 0.98 | none 0.77 | 0.89 | click "Later" | 222 |
| soft-wall | Sign up with email / × | wall 0.99 | × 0.99 | none 0.97 | 0.80 | click "×" | 283 |
| hard-paywall | Subscribe / Already a subscriber? Log in | wall 0.90 | none 0.91 | none 0.98 | 0.81 | ignore | 326 |
| unsaved-changes | Stay / Leave | user_action_dialog 1.00 | Leave 0.58 | none 1.00 | **0.10** | ignore | 315 |
| age-gate | I am 21+ / I am under 21 | wall 1.00 | I am under 21 0.77 | none 1.00 | **0.11** | ignore | 169 |
| control | – | no candidates | | | | ignore | |
| cookie-de | Einstellungen / Alle ablehnen / Alle akzeptieren | consent_banner 1.00 | Alle ablehnen 1.00 | Einstellungen 1.00 | 0.73 | click "Alle ablehnen" | 199 |
| cookie-fr | Paramétrer / Tout refuser / Tout accepter | consent_banner 1.00 | Tout refuser 1.00 | Paramétrer 1.00 | 0.77 | click "Tout refuser" | 164 |

Each request is 850–960 input tokens. The end-to-end run (`npm run e2e`) passes all fourteen fixtures, the two-layer OneTrust flow in under 2.5 s from banner to page usable, and zero actions on the four must-ignore pages.

On real sites from the US the same day: Stack Overflow's OneTrust banner → "Necessary cookies only" (decline 0.90); Gymshark's → "Accept only essential cookies" (0.92); ad slots on nypost.com and theguardian.com, a breaking-news ticker on express.co.uk and a shipping bar on allbirds.com → ignored as page UI; CNN's agree-only notice → ignored (nothing honest to click, and removal needs certainty).

## Limits

- **Cross-origin iframes.** Sourcepoint, Didomi and some OneTrust setups render the banner in an iframe. The content script runs in every frame and judges the frame's own DOM, and reports the top page's hostname, but it cannot see into a frame from outside.
- **Jev reads literally.** It judges the words on the element. A banner with no words (an image) or with buttons that are `div`s without any text gets nothing.
- **Programmatic clicks.** The click is dispatched from a content script (`isTrusted` is false). Most consent managers accept it; where a site ignores it, the element is removed after 800 ms and the log says so.
- **Region.** Many consent banners only appear from the EU/UK. Marketing popups appear everywhere.
- **Hard walls** are never removed. Google's and Yahoo's full-page consent forms are out of scope.
- **Cost.** One to two requests per page that has an overlay, none when the session cache hits. About $0.00003 per request.
- **Language.** Tuned in English; German and French fixtures pass. Other languages are untested.

## Contributing

Add a fixture that reproduces the pattern under `fixtures/`, make `npm run live-check` and `npm run e2e` pass, and open a PR. Never change the question wording in `src/jev.ts` without re-running `live-check` and updating the table above. The video pipeline in `tools/` (frame-by-frame offline render, see [`tools/RECORDING.md`](tools/RECORDING.md)) is not needed to use or test the extension.

## License

MIT. Judged by [Jev](https://typesafe.ai) (TypeSafe). Fonts: JetBrains Mono, Anton (OFL).
