# A hundred faces

Show it to a hundred people before you post it. A wall of one hundred faces
that react while you type. Each face is an authored profile of one specific
person (name, age, job, where they live, temperament, what they care about,
how they read), and each pause in typing (600 ms) sends the message to
TypeSafe AI's Jev with four questions per person: which of seven reactions they
have (a Choice, answered with a probability distribution over the options), and
whether they understand it, trust it, and would share it (three Nouls; a Noul
is a yes/no question answered with a probability). The reactions are Jev's
estimates of how each written person would take the message. The face is drawn
from the whole reaction distribution, not just the winner, so a face that is
60% confused and 40% annoyed looks like that. Hover a face (tap it on a phone)
for the person and their numbers. The aggregates above the grid are computed
in code from the per-face answers: the reaction mix is the mean distribution,
and the understands, trusts, and would-share counts are the people whose
probability is above 50%.

## Deploy shape

Vercel serves the static site Vite builds into `dist/` and runs one function,
`api/react.ts`, for judging. The function and the local development server
share one Web-standard handler, `react(request)` in `server/react.ts`, which
does the validation, the limits, the judging, and the headers. `vercel.json`
names the build command and output directory and sets `supportsCancellation`
on the function, which is expected to abort the request's signal when the
browser drops the request, so the handler stops its Jev calls. Verified so
far: the browser aborts on clear, and the local Node adapter turns a dropped
connection into that abort; that Vercel does the same has not been observed.

Judging is `GET /api/react?m=<message>`, the message URL-encoded and capped at
2,000 code points and 13,000 bytes as the `m=` query it makes (413 beyond either; Vercel's
CDN refuses a URL over 14 KB before the function runs, and the browser refuses
the same messages with the same reason before sending). A wall is answered with
`Cache-Control: public, s-maxage=86400, stale-while-revalidate=604800`, so
Vercel's CDN serves an identical message, and every shared link, without a Jev
call; errors are `no-store`. The six presets never call Jev at all: `npm run
build` first runs `scripts/build-presets.ts`, which writes
`public/presets/<id>.json` from `recordings/jev-presets.json` in the wire
shape, removes any preset file there it did not just write, and the page loads
a preset from there. The recording is the source; nothing is hand-copied. It
carries a hash of the personas, the questions, the batch size, and the preset
messages it was answered against, and the builder refuses a recording whose
hash no longer matches the code, or whose message for a preset is not the
code's, so a change to any of them means `npm run record` before the build
passes again.

To deploy a preview: `vercel` in the project directory (linked to
`hundred-faces`; `vercel link` if not). `TYPESAFE_API_KEY` is set on the
project for the preview and production environments (`vercel env ls`). Preview
deployments sit behind Vercel's deployment protection; production does not.

## Capacity and cost

One wall update is 10 Jev calls (batches of `BATCH_SIZE`, 10 personas each)
and about 74k input tokens, roughly $0.003. Under the documented key limit of
1,200 requests a minute that is 120 updates a minute across every visitor;
presets and shared links are free (static file, CDN). The Jev client used in
production does not retry a 429, so a busy key is reported at once instead of
amplified.

Abuse controls: a Vercel firewall rule on the project (not in this repo) rate
limits `/api/react` to 60 requests per minute per IP, fixed window, answered
429; the handler answers 403 to a browser request whose `Sec-Fetch-Site` is
neither `same-origin` nor `none`; the message limits are 2,000 code points and
13,000 bytes as the `m=` query; the browser judges on pause with one request in flight and the newest text queued
behind it. On a 429 (from Jev or from the firewall) the browser waits 2 s and
retries once, then shows "The wall is busy right now. Try again in a few
seconds."

Your text goes to Jev and comes back as numbers; it lives in the link and nowhere else.
The link is the page URL with `m=`, made when a message is judged and handed on by the share row; the API request carries the same query.
The handler logs each request's status and duration and nothing else. The
message rides in the URL, so Vercel's request logs see it (kept one hour on
Hobby) and the CDN keys its cache on it (a day, plus a week stale); TypeSafe
receives it as the request state. Vercel Web Analytics gets the page URL with `m` removed by the `beforeSend` hook in `src/client/main.ts` (Vercel's documented way to redact a query parameter); observed on a preview deployment: the page-view request's body carried the bare page URL while the address bar carried `?m=`, and typing a further message sent no view.

## The share loop

The page URL carries the message (`/?m=<encoded>`); opening such a link fills
the box and judges through the same cached GET, and judging keeps the URL
current with `history.replaceState`. Once a wall is shown: "Post on X" opens an
X post with the top reaction, the understands and trusts counts, and the link;
"Save the wall as an image" draws the hundred faces with a header onto a
1200×1200 canvas, from the same geometry the SVG wall uses, and downloads
`hundred-faces.png`; "Copy link" copies the URL. `public/og.png` is the card
image for links to the page.

## Run it locally

Needs Node 24 and `TYPESAFE_API_KEY` in the environment (the local server
reads it; the browser never sees it). The API server listens on loopback only,
on port 8787; `PORT` overrides it for both the server and Vite's proxy.

```sh
npm install
npm run dev        # builds the presets, then the API server and Vite together; open http://localhost:5173/
```

## Check it

```sh
npm run check      # typecheck + tests + build
npm test           # tests only; offline, against recordings/jev-presets.json
npm run record     # re-record the presets from the real API (after changing personas, questions, batch size, or presets)
npm run measure    # batching measurement against the real API; see log/ for the numbers
npm run probe      # movement between each preset pair, spread, self-consistency, and sanity probes against the real API
```

Tests use Node's built-in runner and run with no network. `test/react.test.ts`
is the contract test: the handler with a recording-backed fake client on one
side, the browser's `fetchWall` on the other, one recording between them, over
the same Node adapter the local server uses. The recording's hash (personas,
questions, batch size, preset messages) is checked by the loader, so the suite
cannot pass on stale answers. `test/presets.test.ts` checks the built presets
against what the handler would answer.

## Layout

```
index.html               the page
api/react.ts             the Vercel function: the real Jev client behind the handler
server/                  react.ts (the handler), node.ts (Node http adapter), jev.ts (the client), main.ts (local server)
src/client/              browser code: main.ts (update loop, share loop, card), faces.ts (SVG wall), image.ts (canvas image), card.ts (the person card), bars.ts, api.ts
src/shared/              pure modules used by both sides
  personas.ts            the hundred people
  reactions.ts           the seven reactions, their contrastive descriptions, face parameters, and distribution helpers
  questions.ts           the three nouls, the Jev request for a batch, and reading the answers back
  wall.ts                one wall update: batches, parallel calls, BATCH_SIZE
  face.ts                blend a distribution into face parameters and geometry
  aggregate.ts           wall-level numbers
  share.ts               the share text
  presets.ts             the preset messages
  types.ts               the /api/react wire contract and the message limits
public/                  og.png; presets/ is generated by the build
recordings/              jev-presets.json (Jev's answers for the six presets, the source for the suite and the page) and schema.ts (its shape, loader, request hash, recorded wall)
scripts/                 dev.ts, build-presets.ts, record-fixture.ts, measure-batching.ts, probe.ts, stats.ts
test/                    tests; helpers/fixture-client.ts (a Jev client that answers from the recording)
vercel.json              build command, output directory, function cancellation
```

## How a wall update works

1. The browser waits for a 600 ms pause in typing, then requests
   `/api/react?m=<message>`, one request in flight; text typed while it is out
   waits and goes out when it settles. Whatever lands with a newer sequence
   than the wall shows becomes the wall, success or failure; an older response
   is ignored. Clearing the box takes effect at once and aborts the request in
   flight; the local server cancels its Jev calls on that abort, and on Vercel
   `supportsCancellation` is expected to do the same. A preset is loaded from
   its recording instead.
2. The server splits the hundred personas into batches of `BATCH_SIZE`, builds
   one Jev request per batch with state `{ message, personas: [...] }` and four
   questions per persona addressed by path (`personas[3]`), and fires the
   batches in parallel. Why ten per call is measured and explained in `log/`.
3. Answers come back as probabilities, about half a second after the request
   left; the browser blends the seven reaction probabilities into mouth, brow,
   eye, and tint parameters and tweens each face there over 180 ms.

## Not in v1

Per-face explanations, editing personas in the page, saving sessions, any
generative model.
