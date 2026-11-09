# PagePilot

An agent in the browser that pays for thinking once.

An agent looks at a page and authors a small deterministic spec (which blocks
to read, which rows to extract). A pure executor replays that spec on every
later page of the same site for 0 tokens. The model is only in the loop when
something new shows up.

Status: alpha. Works on our fixtures and the live sites listed below; the
installed-extension click-through has not been exercised yet.

## What is here

- `extensions/pagevoice` — read any article aloud. In-page reader panel,
  paragraph highlight, click to seek, cached audio.
- `extensions/pagelens` — turn a page into rows (CSV / JSON / Markdown).
- `extensions/shared` — the spec formats, the executors, and the authors.
- `pagepilot/` — zero-dependency Node server: site-key-authenticated proxies
  (OpenAI-compatible LLM + TTS, TypeSafe Jev), trace recording, spec registry,
  dashboard. Real API keys never reach the browser.
- `experiments/jev-reader-author` — live-site evals, run through
  [ego lite](https://github.com/citrolabs/ego-lite).

## System One in front of System Two

Reading specs are authored by [Jev](https://docs.typesafe.ai/introduction)
(TypeSafe's System One model: typed yes/no answers with probabilities, no text
generation) before any LLM runs:

1. Code groups the page's text blocks by a selector that generalizes
   (`div.entry p`, `ol.references li`).
2. Jev answers one question per group, all groups in parallel: would a
   listener want to hear this?
3. Code builds the spec (default-deny), runs it, and checks the result:
   coverage of what was voted in, leakage of what was not, how much text sat
   in Jev's uncertain band, word count.
4. Only when a check fails does the LLM agent take over.

Measured 2026-09-18 (`experiments/jev-reader-author/*.json`):

| Page | Author | Cost |
|---|---|---|
| Wikipedia article | Jev | 4.0k tokens, 1.6 s |
| simonwillison.net post | Jev | 3.4k tokens, 0.4 s |
| MDN guide | Jev | 3.2k tokens, 0.3 s |
| docs.typesafe.ai | escalated: 64% of text uncertain | 2.3k tokens |
| paulgraham.com essay | escalated: no block tags | 0.5k tokens |
| Hacker News thread, front page | escalated: not an article | under 1k |

Jev input is $0.042 per million tokens, so an authored spec costs about
$0.0002. Each spec was then replayed on other articles of the same site
(Kahneman and Jevons paradox on Wikipedia, another post, another MDN guide):
clean article text, 0 tokens.

Known limit: a group is read or skipped as a whole, so Wikipedia's "External
links" list rides along with body lists.

## Run it

Needs Node >= 22. Keys go in a repo-root `.env`:

```
OPENAI_API_KEY=...      # LLM agent fallback + text to speech
TYPESAFE_API_KEY=...    # Jev
```

```sh
node pagepilot/server.mjs                 # http://localhost:7788, dashboard at /
cd extensions && npm install
npm run build                             # pagelens + pagevoice -> */.output/chrome-mv3
npm run build:harness                     # test harness for the fixtures
```

Load `extensions/pagevoice/.output/chrome-mv3` unpacked in Chrome, open an
article, click the extension, press read.

Details: [extensions/README.md](extensions/README.md),
[pagepilot/README.md](pagepilot/README.md).

## Fixtures

`pagepilot/public/article.html` is a mirrored Wikipedia article (CC BY-SA 4.0)
and `hn.html` a mirrored Hacker News front page, kept so runs are repeatable.

## License

MIT. Fixtures under `pagepilot/public/` keep their original licenses.
