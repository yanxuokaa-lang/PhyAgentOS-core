# jev-canvas

Say "make a yellow circle here" while pointing your finger at the screen, and the circle appears
under your fingertip on a [tldraw](https://tldraw.dev) canvas. Speech comes from the browser's Web
Speech API, the fingertip from MediaPipe hand tracking on the webcam, and every decision (is this a
command, which action, which shape, which colour, which existing shape, where) from
[Jev](https://typesafe.ai), TypeSafe's decision-only model, reached through OpenRouter's Decisions
API.

![Speaking Ukrainian commands at the canvas while a tracked finger points at it](docs/demo.gif)

## What you can say

Commands work in English and in Ukrainian. The language button switches the recogniser between
`en-US` and `uk-UA`; it understands one language at a time.

| Action | English | Ukrainian |
| --- | --- | --- |
| create | "make a yellow circle here", "draw a big red star", "add a sticky note that says buy milk in the top right" | "намалюй синій трикутник тут", "додай зелений квадрат" |
| move | "move this over there", "put it in the corner" | "пересунь це сюди" |
| delete | "delete that", "remove the star", "get rid of it" | "видали це" |
| recolor | "make it red", "turn this blue" | "зроби його червоним" |
| resize | "make it bigger", "make the star much smaller", "shrink that" | "збільш синій квадрат" |
| duplicate | "duplicate this", "copy it", "another one like that" | "скопіюй це" |
| clear | "clear the canvas", "start over", "delete everything" | "очисти все" |
| undo / redo | "undo", "go back", "redo", "bring it back" | "скасуй", "поверни" |

Anything that is not addressed to the canvas is ignored. "So anyway, what do you want for lunch"
scores `is_command` around 2% and nothing happens.

- **Shapes**: rectangle, ellipse, triangle, diamond, hexagon, star, heart, cloud, arrow, plain text,
  sticky note.
- **Colours**: the 13 tldraw colours (black, grey, red, light red, orange, yellow, green, light
  green, blue, light blue, violet, light violet, white).
- **Places**: where the finger points ("here", "there", "тут", "сюди"), the centre, and eight
  regions (top left, top, top right, left, right, bottom left, bottom, bottom right). With no place
  named, a new shape goes to a free spot near the centre.
- **Sizes**: a five-step rubric from tiny to huge, mapped in code to a scale factor between 0.5 and
  2. "Nothing said" is the middle step and leaves the size alone.
- **Text**: "that says …", "з написом …" and similar leads make code extract candidate spans; Jev
  picks one and it is copied to the canvas verbatim.

Two commands in one breath work: "make a blue square there make it orange". Pinching on a shape and
moving your hand drags it directly, with no model call.

## Run it

Requirements:

- Chrome or Edge. Safari and Firefox have no Web Speech API, so the microphone button is disabled
  there. The rest of the app still works with the mouse and the typed command box.
- A webcam, for the pointing finger. Without one the mouse pointer stands in for the finger.
- Node 22.12 or newer (`package.json` `engines`; tldraw 5 and Vite 8 need it, and the dev script
  uses `--env-file-if-exists`).
- An OpenRouter API key with access to the alpha Decisions API:
  <https://openrouter.ai/settings/keys>.

```bash
git clone https://github.com/gaborishka/jev-canvas.git
cd jev-canvas
cp .env.example .env     # then paste your key after OPENROUTER_API_KEY=
npm install
npm run dev
```

Open <http://127.0.0.1:5183>. `npm run dev` first runs `scripts/copy-wasm.js`, which copies the
MediaPipe wasm runtime out of `node_modules` into `public/mediapipe` so nothing is fetched from a
CDN at run time.

On the first run:

1. **Start mic**, and allow the microphone when Chrome asks. The button then shows a level bar, and
   the status line names the input device Chrome is really using.
2. **speak: English / Українська** switches the recognition language. Switch it before you talk.
3. **Start camera**, and allow the camera. The hand model is downloaded from Google's MediaPipe
   bucket on the first start, so it takes a few seconds. A dot then follows your index fingertip.
4. **Calibrate** (optional). Point at each of four dots and hold still. The mapping is saved in
   `localStorage`. Without it, the middle 60% of the camera frame is stretched over the canvas.

With no camera or microphone, hover the mouse where you mean, press `/`, type a command and press
Enter. Typed commands take exactly the same path as a finished spoken sentence.

## How it works

```
 mic (Web Speech API) ─┐
 webcam → fingertip ───┼─▶ state as text ─▶ ONE Jev request ─▶ policy ─▶ editor.createShape(…)
 canvas → "s1 yellow ──┘    + 8–9 questions    (typed answers)   (thresholds in code)
           circle 120x120 at (756,177)"
```

Every transcript update, partial or final, produces one request to Jev. The request carries the
state as text (transcript, where the finger is and what it is over, the shapes on the page with
short ids, the visible area, the selection, the last changed shape) and this set of typed questions,
built in `shared/questions.js`:

| Question | Type | What it answers |
| --- | --- | --- |
| `is_command` | noul | Is the speaker addressing the canvas at all? |
| `complete` | noul | Is the instruction finished, so it can be carried out now? |
| `action` | choice | create, move, delete, recolor, resize, duplicate, clear, undo, redo, none |
| `shape` | choice | one of the 11 shape kinds, or none |
| `color` | choice | one of the 13 colours, or none |
| `target` | choice | which existing shape the instruction is about, or none |
| `where` | choice | point, center, one of eight regions, or none |
| `size` | score | a 0 to 4 rubric from tiny to huge, 2 meaning nothing was said |
| `text_span` | choice | which extracted span is the text to write (only when the transcript has candidate spans) |

Jev returns probabilities. It never generates text and never calls a tool. Everything else is plain
code:

- **Thresholds and fallbacks** live in `shared/policy.js`: `is_command ≥ 0.5` or the transcript is
  ignored, `action ≥ 0.55`, `complete ≥ 0.6`. A command that needs a place waits for a 900 ms pause
  unless the place is already clear (`where ≥ 0.6`), so "make a circle" does not fire before
  "… here". Text is never cut short. When `target` is below its threshold, code falls back to the
  shape under a spoken "this", then to the only shape on the page, then to the selection.
- **Pointing words are captured at the moment they are spoken**, not when the answer comes back.
  `src/controller.js` keeps a 3 s trail of finger positions and reads it back `SPEECH_LAG_MS`
  (300 ms) earlier, because a word reaches the transcript after it was said. That is what makes
  "move this there" work: "this" and "there" each remember their own position.
- **Back-to-back commands** are handled by a consumed prefix. Without a pause the recogniser keeps
  one result growing, so after a command is executed the controller remembers the text it acted on
  and treats what follows as the next sentence once it is two words long. One action per sentence.
- **At most 2 requests are in flight.** Partial transcripts are debounced 200 ms, an older request
  is aborted when a third is needed, and an answer that arrives after a newer one has been applied
  is dropped.
- **429s are retried twice**, 400 ms and 800 ms apart, in `server/decide.js`.

The key is only ever in the dev-server process. The browser posts its context to `/api/decide`, and
the server builds the questions itself, so the endpoint cannot be used as a generic proxy for the
key. It accepts only `application/json` POSTs, which forces a CORS preflight that the server never
answers, and it binds to 127.0.0.1.

## Numbers

Measured on the author's machine:

- 18 of 18 probe commands decided correctly (`scripts/probe.js`, 10 English and 8 Ukrainian).
- 300 to 550 ms per decision.
- About 1,900 input tokens per request, roughly $0.00008. A spoken sentence costs 2 to 4 requests.

To reproduce, with a key in `.env`:

```bash
node --env-file=.env scripts/probe.js   # 18 real Jev calls, about $0.0015
npm test                                # 18 unit tests, no network
```

`probe.js` prints the raw answers and the policy verdict for each command, so you can see where a
threshold would have to move.

## Two things learned about Jev

**The question text has to say which language it is reading.** Short Ukrainian imperatives such as
"видали це" and "скасуй" scored `is_command` around 12%, low enough to be thrown away as
background speech. Adding one sentence to the question instructions ("The speaker may use English
or Ukrainian") and two Ukrainian examples to the criteria took the same commands to about 87%. The
model was not missing the meaning; it was reading them as speech that was not addressed to the app.

**A visible finger pulls `where` towards `point` even when no pointing word was spoken.** The state
says where the finger is, and that is enough to raise the answer on its own. Code does not accept
it at face value: `placeFor` in `shared/policy.js` honours `where = point` only when the transcript
really contained a pointing word, which `shared/spans.js` knows by regex, for certain and for free.

## Troubleshooting

- **Speech stays empty and the status says the session was closed at once.** Chrome allows one Web
  Speech recognition session per browser. Close any other tab that uses speech recognition,
  including another copy of this app, and press Start mic again.
- **Nothing is transcribed.** The mic button's level bar and the input device name in the status
  line show whether Chrome is listening to the microphone you think it is. The status also reports
  the stage the recogniser reached, so "no sound yet" and "heard speech, recognised no words" (the
  wrong language) can be told apart.
- **Ukrainian is not recognised.** The recogniser handles one language at a time. Use the language
  button before speaking.
- **Privacy.** Web Speech sends audio to Google for recognition. The webcam video never leaves the
  browser; MediaPipe runs locally.
- **The tldraw badge.** tldraw 5 shows a "Get a license" watermark on localhost and needs a licence
  key to be hosted in production, which is why there is no hosted demo of this app.
- **HTTP 429 from OpenRouter.** The Decisions API is alpha and rate-limits bursts. The server
  retries twice; if you speak a long sentence with many partial results you may still see one.
- **"OPENROUTER_API_KEY is not set".** `.env` is missing, or the key line is empty. The dev script
  reads `../.env` and then `.env`, both optional.

## Project layout

```
index.html            Vite entry
vite.config.js        React plugin, plus /api/decide mounted on the dev server
.env.example          the one variable this project needs
shared/questions.js   every question and the state Jev is asked about — read this first
shared/policy.js      typed answers → act, wait or ignore; all thresholds and fallbacks
shared/spans.js       pointing words and candidate text spans (EN + UK), plain regex
server/decide.js      POST /api/decide — the only place that sees the API key
src/main.jsx          React root
src/App.jsx           layout, buttons, the INPUTS → JEV → CANVAS panel
src/controller.js     debounce, in-flight requests, pointing capture, one action per sentence
src/canvas.js         canvas → text, and action → tldraw editor calls
src/hand.js           MediaPipe hand landmarker, smoothing, calibration
src/hand-math.js      gesture and calibration arithmetic, kept apart so it can be unit-tested
src/voice.js          Web Speech wrapper and the microphone level meter
src/styles.css        all styling
scripts/copy-wasm.js  copies the MediaPipe wasm runtime into public/ before dev
scripts/probe.js      18 spoken commands against the real API, no browser
test/                 unit tests for policy, spans and hand math
docs/                 the demo GIF and a poster frame
```

## Credits

The idea comes from a demo Jack Cheng posted on X: voice plus finger on a tldraw canvas, with an
INPUTS → JEV → CANVAS panel showing the decision. The code here was written from scratch.

Built with [tldraw](https://tldraw.dev), [MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker),
the Web Speech API, [TypeSafe's Jev](https://typesafe.ai) and the
[OpenRouter Decisions API](https://openrouter.ai/docs).

## License

MIT, see [LICENSE](LICENSE).
