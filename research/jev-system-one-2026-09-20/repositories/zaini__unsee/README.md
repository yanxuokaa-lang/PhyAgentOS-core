# Unsee

![Unsee's icon](icons/icon128.png)

A Chrome extension (Manifest V3, TypeScript) that hides whatever you'd rather not see.
Describe it in your own words: "ads and sponsored content", "anything about the royal
family", "crypto hype", "war". As you browse, each piece of a page is checked against
every rule. Matches disappear, and so do their photo, caption and summary.

> **This is a demo.** Unsee shows what [TypeSafe](https://docs.typesafe.ai)'s Jev model
> can do when it's used as a building block inside ordinary code. It's not a finished
> content-safety product. It will miss things and occasionally hide something it
> shouldn't; every hidden item can be shown again from the popup.

It started as [typesafe-adblock](https://github.com/realZachi/typesafe-adblock), an ad
blocker built on Jev, and grew from there. Ads are now just one built-in rule.

## The idea

A parent should be able to write guidelines for their child's browsing the way they'd
say them out loud: "hide graphic violence, unless it's serious news reporting", or
"hide war and battles, except the American Revolution for school". Keyword blocklists
can't express that, and a general chatbot is too slow and expensive to check every
headline on every page.

Unsee splits the problem in two. Code finds the pieces of a page (headlines, cards,
teaser links, paragraphs, ads) and decides what to hide. Jev answers one narrow yes/no
question per piece and rule, all in parallel, with a probability for each answer:
"does this match the rule?", "does it fall under the exception?", "is this photo part
of the same story?".

![Unsee flagging royal stories on the Daily Mail home page](docs/screenshot-royals.png)

_Highlight mode on a saved Daily Mail home page with the rule "anything about the royal
family". Royal stories are outlined with the rule and Jev's certainty; the stories
beside them (Burnham, the UFO files, the retired teacher) are untouched. In the default
hide mode they would simply be gone._

The semantic calls are made by [TypeSafe AI](https://docs.typesafe.ai)'s System One model
**Jev**, called through the [Vercel AI SDK](https://ai-sdk.dev)'s experimental
`evaluate()` against the [AI Gateway](https://vercel.com/docs/ai-gateway). Everything
else — finding regions, thresholds, vetoes, what actually gets hidden — is plain code.

**BYOK: bring your own key.** There is no backend. You paste your own Vercel AI Gateway
API key into the popup; it is stored in `chrome.storage.sync` and sent only to
`https://ai-gateway.vercel.sh`, which routes calls to TypeSafe's `jev` model. You pay for
your own usage. Jev bills input tokens only, and a page costs a small fraction of a cent.

## How it works

```
page ──► find regions ──► describe ──► Jev: one question per (region × rule) ──► code decides ──► hide
 (code)      (code)        (code)            + "is this site navigation?"         (policy.ts)        │
                                                                                                      ▼
                                   hide those too ◄── code decides ◄── Jev: "same item?" per ── smart regions:
                                                                        neighbor + parent        look around it
```

1. **Find regions (code, `src/content/candidates.ts`).** Two independent sources:
   - _Ad-shaped elements_ (only while the ads rule is on): iframes, `ins`, `ad`/`sponsored`
     tokens in id/class, `data-ad-*` attributes, links to ad networks, and short labels
     such as "Sponsored", "Anzeige", "Werbung". Tight wrappers are collapsed.
   - _Pieces of content_ (only while a topic rule is on): every headline (`h1`–`h6`)
     and every teaser link (a link that holds most of its block's text, as in news
     "puff" lists), climbed up to the card that holds it; `article`s and `figure`s;
     and paragraphs (`p`, `blockquote`, `dd` of 60+ characters) that aren't inside a
     card already.

   Anything big enough to be the page itself is skipped: half the viewport, 2000+
   characters, or containing `main`/`h1`.

2. **Describe (code, `src/content/describe.ts`).** Each region becomes a small JSON object:
   headline, visible text, label, image alt text, descriptive image file names, link
   hosts, iframe host, shape in words ("wide horizontal banner"), known ad network.
   Jev only ever sees these summaries, never the page itself.
3. **Judge (Jev, `src/lib/jev.ts` + `src/lib/questions.ts`).** Speculative fan-out: for
   every region, **one yes/no question per rule**, plus one "is this the site's own
   navigation or interface?" question. A rule with an exception ("war, unless it's the
   American Revolution") gets a second, separate question: "does this fall under the
   exception?". Each question carries the rule's text and true/false criteria with
   examples. All of them go in a single `evaluate()` call per
   six regions, and Jev answers them in parallel. The ads rule has its own hand-tuned
   criteria.
4. **Decide (code, `src/lib/policy.ts`).** A region is hidden when any rule scores ≥ the
   threshold (default 0.70) and that rule's exception, if it has one, does not. Topic rules are vetoed when the region is probably site
   navigation, so a menu link labelled "Royals" stays put. The ads rule has no veto,
   because ads do live in headers. Every rule that fired, with its probability, is kept
   as the **reason**.
5. **Smart regions (code + Jev, `src/content/neighborhood.ts`).** For each hidden region,
   code collects up to three siblings on each side and its parent. It climbs only
   through tight wrappers and never offers page landmarks. A second `evaluate()` call
   then asks, for each neighbor, "is this part of the same item?" and "does this match
   the rule on its own?", and asks of the parent "is this whole thing one item?". Code
   hides the neighbors that qualify, and the parent only if it is a single item, never
   a list. It can grow at most twice. That's how the photo and summary under a hidden
   headline go with it.
6. **Hide (code, `src/content/effects.ts`).** Nothing is deleted. Regions are hidden
   with an attribute and a stylesheet, so the popup can show any of them again, and
   switching to _Outline + show why_ re-renders in place with a tag on each region
   (`the royal family · 94%`; `↳` marks regions hidden because they belong with
   another).

A `MutationObserver` plus a scroll handler catch content that loads later. Batches are
debounced (600 ms, but never postponed past 2 s on busy pages). Answers that arrive after
the rules have changed are dropped.

## Install

1. `npm install && npm run build` bundles the TypeScript into `dist/` (`npm run watch`
   rebuilds on save).
2. Open `chrome://extensions` and enable **Developer mode**.
3. **Load unpacked** → pick the `dist/` folder.
4. Click the icon, open **Settings**, paste your Vercel AI Gateway API key, hit **Test**.
5. Add rules under **What should disappear?** and browse.

## Popup

| Section                | What it does                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------- |
| On / off               | Pause everywhere                                                                                   |
| What should disappear? | Your rules, in plain language, each with an optional "…unless" exception. Ads is built in (max 12) |
| On this page           | Everything hidden here, with the rule and probability behind it, and a **Show** / **Hide** toggle  |
| Certainty              | Probability a rule must reach before something is hidden (30–95 %)                                 |
| When something matches | **Hide it**, or **Outline + show why** (red outline and a tag with the reason)                     |
| Smart regions          | Also hide the photo, caption and summary that belong to a hidden item                              |
| Pop animation / Toast  | Cosmetic                                                                                           |
| Rescan                 | Forget what was already judged on this page and look again                                         |

Changing the rules applies immediately. Items that no rule stands behind any more come
back, and the page is judged again against the new list.

## What leaves your browser

Per batch, one `evaluate()` call per six regions to `ai-gateway.vercel.sh` (which
forwards it to `typesafe-ai/jev`). Each call contains the page hostname and title, your
active rules' text, and for each region the fields listed under step 2 (up to 280
characters of visible text, link hostnames, image alt texts and file names, attribute
names). Smart regions sends one more call per hidden region, with the same kind of
summaries for its neighbors. Nothing else leaves your browser, and nothing is stored on
any server of this project, because there isn't one.

## Testing without installing

Requires Node 22+ and a build first, since the harness loads the bundled content script:

```bash
npm install
npm run build
npm run serve     # static server on :8787

# heuristic stand-in for Jev (tests discovery, hiding and smart-region plumbing):
open "http://localhost:8787/test/harness.html?fixture=topics-fixture.html&rules=the%20royal%20family&mode=highlight&relay=0"

# real Jev: copy .env.example → .env.local, fill in AI_GATEWAY_API_KEY, then
npm run relay     # terminal 2; drop relay=0 from the URL above
```

`test/topics-fixture.html` is an English news front page. It has a lead story whose
photo and standfirst are siblings of the headline rather than wrapped with it (the smart
regions case), a card grid, a "Royals" menu link that must survive, and a bare
"ADVERTISEMENT" label next to an ad slot. `test/fixture.html` is the original German page
with eight ads; it exercises the German labels.

```bash
# score Jev against labelled regions × rules, plus one smart-regions case
npm run live-check
```

### Evals

`npm run eval` scores the real content script against labelled page snapshots. Each case
in `test/evals/cases.ts` is a page (two Wikipedia articles and the Daily Mail home page
saved under `test/evals/pages/`, plus the two fixtures; inline scripts are stripped when
served, so runs are repeatable), a set of rules (optionally with exceptions), and probes: regions
that should end up hidden and regions that must stay. The runner opens each page in
headless Chromium, injects `dist/src/content.js` behind a fake `chrome` API, answers its
Jev calls from Node, waits for the page to settle, and reports per case:

- probes correct, precision and recall;
- every mistake, with the probabilities Jev gave that exact region, or "never judged"
  when discovery didn't find it (so a failure points at discovery, the model, or policy);
- everything else that got hidden, for a quick over-blocking review.

```bash
npm run eval                               # real Jev (AI_GATEWAY_API_KEY in .env.local)
npm run eval -- --heuristic                # keyword stand-in: tests plumbing, not judgment
npm run eval -- --case us-war --dump       # one case, list every region that was judged
```

To add a case, save a page (`curl -L <url> -o test/evals/pages/<name>.html`), add an
entry with a `baseHref` so its styles load, and label a handful of regions a careful
parent would agree on. Leave out anything ambiguous. Results are written to
`test/evals/results/`. Real-Jev runs are committed; heuristic runs are git-ignored. Add
`--highlight --screenshot docs` to save a screenshot of each case.

The latest real-Jev run got every probe right: 106 of 106 across 12 cases. It judged
about 3,100 regions and used 2.9M input tokens, around $0.12. An excerpt:

```
▶ us-war-except-revolution — Rule with an exception: war is hidden, except the American Revolution
  … 6/6 correct · precision 100% · recall 100% · 357 regions judged, 63 hidden · 15.6s
▶ dm-royals — Royal stories among ~360 headlines, cards and puff links
  … 12/12 correct · precision 100% · recall 100% · 610 regions judged, 42 hidden · 17.7s
▶ dm-violent-crime — A parent's rule: violent crime stories go, everything else stays
  … 9/9 correct · precision 100% · recall 100% · 595 regions judged, 56 hidden · 15.4s

Overall: 106/106 probes correct · precision 100% · recall 100% · 0 false hides · 0 misses
```

Probes cover only the clear-cut regions, so the unlabelled hides still need a human
look. See [`test/evals/RESULTS.md`](test/evals/RESULTS.md) for the full table and notes
on where it over-blocks.

`.env.local` is only for these Node scripts. The extension itself never reads it.

## Limits

- Jev reads text. An image with no alt text and a hash for a file name is invisible to
  it, unless it sits right next to something that was hidden (smart regions).
- A region's content inside a cross-origin iframe is never seen; the iframe is judged
  as a whole.
- Candidates that hold the page's `h1` or `main` are never hidden, so an article page
  about a blocked topic keeps its structure; its matching paragraphs, figures and
  sections are hidden individually. Tables, comments and image-only posts are not
  covered yet.
- Every batch is an API call. Tune the certainty and the rules on the sites you visit.

## Contributing

Keep the split intact: discovery, thresholds and DOM changes in code; only narrow
semantic judgments go to the model. Good first targets: better card detection on
specific sites, paragraph-level hiding inside articles, and per-rule certainty.

## License

MIT, see `LICENSE`.
