# Vibe Check for X (powered by Jev)

A Chrome extension that runs your draft post through [TypeSafe's Jev](https://docs.typesafe.ai) before you hit **Post**. It renders a scorecard under the composer with virality, funniness, informativeness, clarity, insult level, ragebait, cringe, "sounds AI-written", regret risk, typo detection, and the most likely crowd reaction, plus an overall "Send it / Fine, mid / Probably don't / Sleep on it" verdict.

Works in the `/compose/post` modal, the inline composer on Home, reply composers, quote posts, and multi-post threads. The tweet you're replying to is sent along as `reply_to` and a quoted tweet as `quoting` (text, author, and described photos), so insult level, virality and likely reaction are judged against that context. Plain retweets have no compose step, so there's nothing to check.

**Images and video:** Jev is text-only. If you add an OpenAI API key, every attached image (and the first frame of each video/GIF) is described by an OpenAI vision model and the description is passed to Jev as `media`. Photos on the tweet you're replying to are described too. Two extra rubrics ("Media helps", "Media risk") are asked only when media is present. Descriptions are cached per attachment, so you pay for each image once, not on every keystroke.

## Install

1. Open `chrome://extensions`, turn on **Developer mode** (top right).
2. Click **Load unpacked** and select this `vibecheck` folder.
3. The settings page opens automatically. Paste your TypeSafe API key, click **Test key**, then **Save**.
   Optionally paste an OpenAI API key, set the vision model (defaults to `gpt-4o-mini`; any OpenAI chat model that accepts images works), and click **Test key + model**.
4. Go to https://x.com/compose/post and start typing.

## Usage

- Auto-analyze fires ~1.2 s after you stop typing (configurable, or disable it).
- **Check** button or `⌘⇧V` / `Ctrl+Shift+V` forces a run.
- Hover any metric to see the rubric and the level Jev landed on.
- Expand "What Jev was told about N attached items" to read the exact media descriptions Jev received.
- `⚙` opens settings. `▾` collapses the panel (remembered).

## Customizing rubrics

Settings → **Rubrics (JSON)**. Each entry:

```json
{
  "id": "spicy",
  "label": "Spiciness",
  "type": "score",
  "polarity": "neutral",
  "weight": 0,
  "instructions": "How spicy a take is `draft`?",
  "criteria": ["Lukewarm", "Mild", "Medium", "Hot", "Nuclear"]
}
```

- `type`: `score` (ordered levels low→high, 2–10), `noul` (yes/no probability, optional `criteria: {true, false}`), `choice` (`criteria: {option: description}`).
- `"requires": "media"` makes a rubric conditional on attached media.
- `polarity` + `weight` feed the verdict: `good` metrics push it up, `bad` push it down, `neutral` / weight 0 are display-only. Any `bad` metric at ≥75% forces "Sleep on it".
- All questions go to Jev in **one request** and are evaluated in parallel against the same state, so adding rubrics costs tokens but not latency.

## How it works

- `content.js` finds X's Draft.js composer (`data-testid="tweetTextarea_*"`), reads the text, and inserts the panel after the composer toolbar. A MutationObserver keeps it attached through X's re-renders.
- Attached media lives in X's `data-testid="attachments"` block as `blob:` URLs. The content script fetches each blob, downscales it to 1024px JPEG on a canvas (or grabs a video frame), and hands it to the background worker as a data URL. Reply-context photos are public `pbs.twimg.com` URLs and are passed through directly.
- `background.js` (service worker) holds both API keys. It POSTs media to `https://api.openai.com/v1/chat/completions` for a neutral description (subjects, verbatim text, meme format, sensitive content), then POSTs the draft + descriptions to `https://api.typesafe.ai/v1/systemone` with `model: "jev-latest"`. Both calls retry on 429/5xx with backoff.
- `rubrics.js` is the default question set. Scores are normalized to 0–1 in the content script and combined into the verdict in code, per TypeSafe's composite-scoring pattern.

## Cost

Each Jev analysis is roughly 1.5k–2.5k input tokens (rubrics dominate), i.e. a fraction of a cent at Jev's published price. Output tokens are free. Each image description is one vision call to OpenAI, cached per attachment.

## Caveats

- X changes its DOM without notice. If the panel disappears, the selectors at the top of `content.js` are the place to look.
- Both keys live in `chrome.storage.sync` and never touch the x.com page context, but these are still client-side keys; use keys you can rotate.
- Video/GIF support describes a single frame only, so motion-dependent jokes will be under-read.
