# Jev Browser

Jev Browser is a local browser automation UI that turns a URL and a plain-language goal into safe, bounded browser actions.

It observes the live page, asks TypeSafe Jev to choose the next operation and target, then executes through Browser Harness. A separate OpenAI-compatible text model is used only when a field needs text. The model never emits selectors or executable browser code.

## Why It Exists

Most browser agents blur three jobs: deciding what to do, generating text, and controlling the browser. Jev Browser keeps those jobs separate:

- Jev chooses from observed operations only: click, type, select, wait, done, or blocked.
- Browser Harness performs the actual Chrome DevTools Protocol actions.
- The text helper supplies field values only when the chosen action is `TYPE_TEXT`.
- The local UI shows screenshots, ranked targets, probabilities, confidence, and the full decision trail.

## Features

- Run browser tasks from a local web interface.
- Inspect every model decision before execution.
- Switch between manual step-by-step control and automatic execution.
- Overlay numbered targets on the live page screenshot.
- Export a JSON trace of executed actions.
- Optionally record screenshots for each observed state.
- Keep credentials local in `.env`.

## Install

Requires Python 3.12+ and `uv`.

```bash
uv sync
cp .env.example .env
```

Fill `.env`:

```env
TYPESAFE_API_KEY=...
TYPESAFE_MODEL=jev-latest

TEXT_MODEL_API_KEY=...
TEXT_MODEL_BASE_URL=http://localhost:6655/openai/v1
TEXT_MODEL=gpt-5.5
```

`TEXT_MODEL_BASE_URL` can point to any OpenAI-compatible chat-completions endpoint.

## Run

```bash
uv run jev
```

Open the printed local URL, enter any `http://` or `https://` page, describe the goal, then choose actions manually or run automatically.

## How It Works

1. The local server opens an isolated browser target.
2. The page is observed and converted into bounded action candidates.
3. Jev ranks the next operation and target from the current page state.
4. Browser Harness executes the selected action through Chrome DevTools Protocol.
5. The UI records the result, model probabilities, confidence, latency, and trace history.

## Safety Model

- The UI binds to `127.0.0.1` only.
- API calls require a per-session token.
- Page text is treated as untrusted data, not instructions.
- The model chooses from observed candidates instead of writing selectors.
- Secrets stay in `.env`, which is ignored by git.

## Checks

```bash
uv run ruff check .
uv run pytest
node --check jev_browser/static/app.js
uv build
```

## Repository Topics

`ai-agents`, `browser-automation`, `web-automation`, `typesafe-ai`, `jev`, `python`, `chromium`, `cdp`, `autonomous-agents`, `local-first`
