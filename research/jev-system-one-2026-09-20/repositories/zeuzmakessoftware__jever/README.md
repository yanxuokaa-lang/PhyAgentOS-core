<h1 align="center">Jever</h1>

<p align="center">A desktop home for <a href="https://openrouter.ai/~typesafe/jev-latest">TypeSafe Jev</a>.</p>

<p align="center">
  <a href="#get-started">Get started</a> ·
  <a href="#using-jever">Using Jever</a> ·
  <a href="docs/development.md">Development</a>
</p>

![Jever on macOS, showing a fruit choice with its confidence and question controls in the message bar](docs/images/jever.png)

Jev picks between options, scores against a rubric, and answers yes/no questions. Jever gives you a place to try those decisions: write a question, add some context, and see the answer alongside its confidence.

Conversations stay on your machine. Bring your own OpenRouter key.

## Get started

You'll need **Node.js 22.12+**, **pnpm 9.9+**, and an [OpenRouter API key](https://openrouter.ai/keys) with credits and access to Jev.

```sh
git clone https://github.com/zeuzmakessoftware/jever.git
cd jever
pnpm install
pnpm dev
```

Open **Settings → Connection**, paste your key, and save. Jever uses your operating system's secure storage to encrypt the key.

Tested on macOS with Apple Silicon. Windows and Linux packaging haven't been verified yet.

## Using Jever

Click **Questions** in the message bar to set up what you want Jev to decide. Start with a preset or write your own.

| Question type | What you give it                    | What comes back             |
| ------------- | ----------------------------------- | --------------------------- |
| **Choice**    | A question and possible answers     | A selected option           |
| **Score**     | A question and ordered score levels | A score against your rubric |
| **Noul**      | A yes/no condition                  | A boolean verdict           |

Paste context into the message bar or attach text files, then send. Open **Details** under an answer to inspect probabilities, usage, and the response JSON. A result below your review threshold stays visible with a review flag.

You can ask several questions in one request, save question sets as presets, and edit their JSON when you need more control. Background context and optional conversation history carry information between turns.

The sidebar keeps your conversations searchable. You can pin, rename, export, or delete them, and back up the whole workspace from Settings. Light and dark themes, accent colors, and text size live there too.

**Shortcuts:** `⌘/Ctrl+N` starts a chat, `⌘/Ctrl+K` searches, and `⌘/Ctrl+,` opens Settings. `Shift+Enter` adds a line.

## Where your data goes

Your key is encrypted locally and excluded from workspace exports. Conversations and backups are stored as **unencrypted JSON**.

When you run a decision, Jever sends the input, attachments, background context, and any enabled history to OpenRouter. Requests use `~typesafe/jev-latest` with model fallbacks disabled. The optional private routing setting asks for providers that decline data collection; this can reduce availability.

See [development notes](docs/development.md) for storage paths, transport details, and security boundaries.

## Working on it

Built with Electron, React, TypeScript, and Tailwind CSS.

```sh
pnpm typecheck
pnpm test
pnpm build
pnpm start
```

`pnpm dev:web` runs a browser preview at `http://127.0.0.1:5173`. It has a separate local workspace; live requests and API keys are only available in the desktop app.

For a local app bundle, run `pnpm package`. For a distributable on your current platform, run `pnpm dist`. Public macOS distribution needs signing and notarization configured separately.

The [development notes](docs/development.md) cover tests and source layout. The original visual concepts are in [design](design/README.md).

---

Jever is an independent project for [TypeSafe Jev](https://docs.typesafe.ai/introduction). It isn't affiliated with TypeSafe or OpenRouter.
