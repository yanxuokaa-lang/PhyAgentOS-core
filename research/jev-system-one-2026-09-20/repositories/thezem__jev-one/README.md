# Jev One

**Give Jev a language. Connect its choices to a world. Watch what happens.**

Jev One is a JavaScript library for building stateful applications around
TypeSafe AI's **Jev**, a model that answers by pointing to choices you supply.

A choice can mean a word, a place, an object, a tool, another vocabulary, or a
request to stop. Your code gives that choice its effect. The runtime carries
the observation into the next decision, until an objective is verified or a
limit is reached.

```text
                  Your goal + the observed world
                               │
                               ▼
                    What can Jev choose here?
                     words · numbers · actions
                               │
                               ▼
                          Jev points
                               │
                               ▼
                   Code validates and applies it
                               │
                               ▼
                     Observe what really changed
                               │
                   ┌───────────┴───────────┐
                   │                       │
               Choose again         Verify / stop / wait
```

The route comes from Jev's choices. The available actions, permissions, and
definition of success come from the application.

**Experimental · TypeScript source · ESM JavaScript · Real Jev via Vercel AI Gateway**

## Start here

| You want to… | Start with… |
| --- | --- |
| Understand the idea | [A word can change the world](#a-word-can-change-the-world) |
| Make your first Jev call | [Run it locally](#run-it-locally) |
| See an actual loop | [Run the courier](#run-the-courier) |
| Recommend items and remember feedback | [Recommendations that remember](#recommendations-that-remember) |
| Integrate it into an application | [The four building blocks](#the-four-building-blocks) |
| Give a coding agent the right context | [Agent integration guide](docs/AGENT-GUIDE.md) |
| Stream decisions or verify completion | [Runtime lifecycle](docs/OBSERVABLE-RUNTIME.md) |
| Understand the internals | [Architecture](docs/ARCHITECTURE.md) |

## A word can change the world

Imagine a courier in a small world. It can move, carry one object, plant seeds,
repair a beacon, and deliver a notebook. Give it a goal: **“Take care of this place.”**

- At home, `PICK UP` can put seeds in its hands.
- `MOVE` opens a numbered list of connected places.
- At the greenhouse, carrying seeds makes `PLANT` available.
- Planting changes the world, empties its hands, and changes its next choices.
- Closing a bridge changes the routes it can see.
- Removing its hands vocabulary removes the actions that need hands.
- Teaching it `NURTURE` can give it another meaning bound to the planting capability.

These are the mechanics demonstrated by the companion React lab. This repository
contains the reusable library and terminal examples; the lab UI is a separate
application. The courier below runs entirely from this repository.

The same structure can drive an application with files, interface elements,
messages, or game objects. You supply the environment and implement its effects.
Adding a word expands the language; adding a capability expands what the program
can actually do.

## Run it locally

Use Node.js 22 or newer and npm. This workflow builds from source and does not
assume a published npm release.

```bash
git clone https://github.com/thezem/jev-one.git
cd jev-one
npm ci
npm run build
```

Set `AI_GATEWAY_API_KEY` in the environment of your **Node process**. In PowerShell:

```powershell
$env:AI_GATEWAY_API_KEY = "your-vercel-ai-gateway-key"
```

Or in a POSIX shell:

```bash
export AI_GATEWAY_API_KEY="your-vercel-ai-gateway-key"
```

Keep credentials on the server. Do not put them in browser code, source files,
logs, or Git. The examples read the environment; they do not automatically load
a `.env` file. Each live example uses your Gateway account. There is no offline
or heuristic fallback.

```bash
node examples/quick-start.js
```

This asks Jev to route a message into `BUG`, `REQUEST`, or `NEEDS CONTEXT`, then
prints the selected word, meaning, and selection weight.

### Use it from another local project

Build this checkout first, then install its local path from your consuming project:

```bash
npm install /absolute/path/to/jev-one
```

In an ESM `.mjs` file, or a project with `"type": "module"`:

```js
import { JevOne, PointKernel } from 'jev-one';
import { VercelJevProvider } from 'jev-one/gateway';

const apiKey = process.env.AI_GATEWAY_API_KEY;
if (!apiKey) throw new Error('Set AI_GATEWAY_API_KEY.');

const jev = new JevOne(
  new PointKernel(new VercelJevProvider({ apiKey })),
);
```

The snippets below assume this `jev` instance. For a browser UI, call your own
server endpoint and stream its decisions back to the page.

## Run the courier

```bash
node examples/observable-world.js
```

This gives Jev a four-place map, a notebook at the archive, and a goal: bring
the notebook home. Jev selects each action, then uses numbers to select adjacent
places. Legal actions are rebuilt from actual state on every turn.

Give it extra direction:

```bash
node examples/observable-world.js "Travel through the garden on the outward journey."
```

An illustrative run looks like this; actual choices can differ:

```text
MOVE      home → garden
MOVE      garden → archive
PICK UP   notebook is now carried
MOVE      archive → workshop
MOVE      workshop → home
DELIVER   notebook is now on the home desk

done: true
reason: verified
```

The program checks the delivered state. A `STOP` before delivery returns
`done: false`. All effects happen in memory. The complete, executable
[observable-world.js](examples/observable-world.js) shows the loop, numbered
board, handlers, observations, and success predicate together.

## The four building blocks

### 1. A vocabulary gives Jev meanings to choose

```js
const answer = await jev.vocabulary.answer({
  context: 'After I press Save, the app closes and my draft disappears.',
  question: 'Where should this message go?',
  vocabulary: [
    { id: 'bug', label: 'BUG', meaning: 'Existing behavior is broken.',
      payload: { type: 'meaning' } },
    { id: 'request', label: 'REQUEST', meaning: 'A new capability is wanted.',
      payload: { type: 'meaning' } },
    { id: 'unknown', label: 'NEEDS CONTEXT', meaning: 'There is not enough information.',
      payload: { type: 'meaning' } },
  ],
});

console.log(answer.entry.label);
console.log(answer.decision.probability);
```

A vocabulary needs at least two entries with distinct IDs. Write meanings that
distinguish the alternatives. Include uncertainty when a forced choice would
be misleading. For reuse, register an object with `id`, `label`, `description`,
and `entries` through `jev.vocabularies.register(...)`, then pass its ID to
`vocabulary.answer`.

### 2. A word can open another vocabulary

| Payload | What happens |
| --- | --- |
| `{ type: 'meaning' }` | Return the selected meaning. |
| `{ type: 'vocabulary', target: 'tools' }` | In `navigate`, open the registered `tools` vocabulary and choose again. |
| `{ type: 'capability', target: 'world.plant' }` | In the runtime, validate and call the registered handler. |
| `{ type: 'control', action: 'stop' }` | Request termination. Other controls are `continue`, `wait`, `ask`, and `unknown`. |

`vocabulary.answer` selects in one vocabulary. `vocabulary.navigate` follows
vocabulary references until it reaches a leaf. Register every referenced
vocabulary first; references are IDs, not filesystem paths.

```js
// After registering a root and the vocabularies it references:
const result = await jev.vocabulary.navigate({
  root: 'world',
  context: 'The courier is holding seeds beside an empty planter.',
  question: 'Which available meaning or action fits now?',
  maxDepth: 6,
});

console.log(result.path);
console.log(result.entry);
```

`loadVocabularyDirectory` from `jev-one/node` loads JSON vocabulary files. See
the [exact loading example](docs/AGENT-GUIDE.md#load-a-directory-of-vocabularies).
Large choice sets use Jev shortlist batches; hierarchical vocabularies can
expose a smaller, meaningful choice at each level. Navigation rejects cycles
and excessive depth.

### 3. Numbers point to whatever is visible now

```js
const answer = await jev.numbers.choose({
  context: 'The courier carries a notebook that belongs at home.',
  question: 'Which connected place should it enter?',
  items: [
    { label: 'Home', description: 'The notebook delivery desk.', value: 'home' },
    { label: 'Garden', description: 'A path toward the archive.', value: 'garden' },
    { label: 'Stay', description: 'Do not move yet.', value: null },
  ],
});

console.log(answer.number);     // one-based position on this board
console.log(answer.index);      // zero-based position
console.log(answer.item.value); // the value bound to the selected item
```

The board accepts **2–25 items**. Bindings are local to that call. Re-observe
before acting if the environment can change. For larger lists, use explicit
pages or hierarchical selection; silently slicing to 25 can hide the correct
answer. An empty or single-item list needs an explicit application policy.

### 4. The runtime connects choices to consequences

A capability is your function, registered with a stable ID, description, and
declared effects. Its handler returns updated `state` and an `observation`.
The runtime adds that observation to the next decision's context.

The courier example demonstrates the complete wiring. A runtime call looks like:

```js
// With the courier vocabulary and capabilities already registered:
const run = await jev.runtime.run({
  goal: 'Bring the notebook home.',
  context: 'The notebook starts at the archive.',
  root: 'courier',
  state: { location: 'home', carrying: false, delivered: false },
  policy: {
    maxTurns: 16,
    maxDepth: 6,
    maxRepeatedState: 2,
    allowedEffects: ['none'],
  },
  verifyCompletion: state => state.delivered,
  onDecision: answer => console.log('Selected:', answer.entry.label),
  onTurn: turn => console.log('Observed:', turn.observation),
});
```

For a changing world, `root` may be a function `(state, turn) => vocabularyId`.
Use it to derive legal actions from current state. If Jev should choose the
route, avoid selecting the next vocabulary just because it is turn two or three.

## Know what “finished” means

Supply **`verifyCompletion`** whenever `done` should mean an objective was achieved.

| Result reason | Interpretation |
| --- | --- |
| `verified` | Your predicate confirmed the current state. |
| `jev_stop` | Jev requested a stop. With a verifier, this does not imply success. |
| `semantic_answer` | A meaning was returned; it does not automatically satisfy a verifier. |
| `wait`, `ask`, `unknown` | Control returned for the application to handle. |
| `no_progress` | Consecutive unchanged states or repeated `continue` reached the limit. |
| `max_turns` | The turn budget was exhausted. |
| `aborted` | The signal cancelled the run at a runtime boundary. |
| `capability_done` | Without a verifier, a handler reported completion. |

Without `verifyCompletion`, the existing API also treats a returned meaning,
a handler's `done: true`, or Jev's `STOP` as completion. Check the reason and
the application's facts before calling that success.

`onDecision` runs before the capability; `onTurn` runs after its result. Both
receive clones and may be asynchronous. A nested call made inside your handler
has its own result and trace; expose it explicitly to stream that choice too.

Cancellation does not undo effects or interrupt an in-flight model call.
`maxTurns` counts runtime turns, **not** every underlying Jev call. Applications
with nested calls or repeated one-turn runs must enforce overall call, time,
and session budgets. See [the lifecycle guide](docs/OBSERVABLE-RUNTIME.md).

## Boundaries that matter

- **Jev selects supplied choices.** It does not generate handler implementations.
- **Effect policy checks declarations.** It is not a JavaScript sandbox. Handlers
  must enforce real permissions, argument validation, and recovery.
- **Words do not grant authority.** New labels do not create new permissions.
  `requiresApproval` is an entry-level gate; the caller owns any approval workflow.
- **Use JSON-compatible, cloneable state.** A new timestamp or counter every turn
  can conceal a semantic no-op from state comparison.
- **Supply the relevant facts.** Describe carried objects, destinations, changes,
  and open paths. Jev cannot use options or facts your application omitted.
- **Weights are not proof.** Selection weights do not establish correctness.
  `jev.kernel.ledger.verify()` checks the local hash chain, not world truth or
  provenance against a malicious rewriter.
- **Errors propagate.** Invalid choices, unknown references, forbidden effects,
  provider failures, and callback failures throw. Handle them at your application
  boundary; do not replace errors with fabricated success.

## Recommendations that remember

Record feedback, save the profile as JSON anywhere, and restore it next session:

```js
const profile = jev.profiles.create({ preferences: 'Thoughtful science fiction.' });
profile.record({ itemId: 'arrival', action: 'liked', item: { title: 'Arrival' } });
const saved = JSON.stringify(profile.export());
const restored = jev.profiles.restore(JSON.parse(saved));

const result = await jev.recommend({
  profile: restored,
  items: movies, // objects with stable string id and title or label
  context: 'Watching with my partner; we have 90 minutes.',
  eligible: movie => movie.minutes <= 90,
  minItems: 3,
  maxItems: 5,
});
console.log(result.items, result.minimumMet, result.reason);
```

For a database or remote catalog, replace `items` with
`source: async ({ cursor, limit }) => ({ items, nextCursor })`.
Jev can browse pages, revisit earlier candidates, and select multiple items.
`pageSize` defaults to 10; `maxPages` and `maxDecisions` bound the run. A minimum
prevents voluntary early finishing, but never overrides hard filters or budgets.

Your app owns storage and records actual feedback. The library does not infer a
like from a recommendation, train a model, or silently save personal data.
Read the [complete profile and pagination contract](docs/RECOMMENDATIONS.md), or run:

```bash
node examples/recommendations.js
```

## Other tools in the library

Use the vocabulary runtime for new stateful integrations. Focused modules remain
available independently:

| Surface | Use it for |
| --- | --- |
| `jev.oracle` | An expandable lexicon, starting with 100 semantic symbols. |
| `jev.cortex` | Choices, Boolean judgments, ordered scores, and cumulative sequences. |
| `jev.navigator` | Observation and traversal through an environment adapter. |
| `jev.commander` | Inert `family → operation → target` proposals; never execution. |
| `jev.voice` | Jev-selected speech acts and supplied facts rendered through templates. |
| `jev.orchestrator` | A loop over legal talk / choose / act / wait / stop postures. |
| `PointKernel` | Direct choices, per-call deadlines, diagnostics, and trace recording. |

These have their own result contracts; the semantic runtime's verifier is not
automatically applied to other loops. The library's Cortex module is separate
from any installed `jev-cortex` agent-tool audit workflow.

`ReadonlyFilesystemEnvironment` from `jev-one/node` observes real directory
entries, confines traversal to its root, skips symlinks, and caps depth at four.
It does not read file contents or execute shell commands. Names and paths can
become Jev context; choose an appropriate root. See
[the filesystem example](examples/navigate-g-drive.js), which uses a Windows path.

## CLI and development

After building, run the CLI directly from this checkout:

```bash
node bin/jev-one.js --help
node bin/jev-one.js oracle --context "The interface has too many steps." --question "What should guide the next change?"
node bin/jev-one.js will --goal "Find the missing file." --context "The directory has not been inspected."
node bin/jev-one.js capabilities
```

Currently all non-help CLI commands require `AI_GATEWAY_API_KEY`; capabilities
lists manifests without a model call. Installing the package also provides the
`jev-one` command shim.

```bash
npm run build     # emit ESM JavaScript and TypeScript declarations
npm test          # build and run mechanics/example tests; no API key required
npm run demo      # live posture/oracle/voice example; requires a key
npm pack --dry-run
```

Tests use private fixtures to verify mechanics, not live model quality. The
quick-start and courier commands exercise the real Gateway path. Source examples
and docs live in the repository; the package archive contains `dist`, `bin`, the
README, and license.

## For coding agents

For persistent personalization, see [recommendations and portable profiles](docs/RECOMMENDATIONS.md).

Read [docs/AGENT-GUIDE.md](docs/AGENT-GUIDE.md) before integrating. It gives the
exact API entry points, a build sequence, a vocabulary-file example, and
acceptance criteria. Start from
[examples/observable-world.js](examples/observable-world.js) for a working loop.

Preserve the central contract: **Jev chooses. The application defines what is
possible, applies the effects, and checks what actually happened.**

## Status and license

This is an experimental library. APIs may evolve as applications expose gaps.
The source and examples are released under the [MIT license](LICENSE).
