# Jev Codex Bridge

[![Checks](https://github.com/ansidium/jev-codex-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/ansidium/jev-codex-bridge/actions/workflows/ci.yml)

[TypeSafe Jev](https://docs.typesafe.ai) selects a model and reasoning effort for
each new message in Codex Desktop or CLI. Codex keeps its existing login.
Windows setup includes a background service, daily updates and rollback.

## Quick start

Requires **Node.js 24+, npm, Git, Codex**, and a
[TypeSafe API key](https://console.typesafe.ai/settings/keys).

```powershell
npm install --global git+https://github.com/ansidium/jev-codex-bridge.git --ignore-scripts
```

Create `~/.jev-router.env` outside your repositories:

```dotenv
TYPESAFE_API_KEY=your-key
```

```powershell
jev-bridge install
jev-bridge status
```

Restart Codex Desktop. **Jev Router** appears in the model picker and becomes the
default for new tasks. In tasks connected to the bridge, choosing a concrete model
pauses routing; choosing Jev Router resumes it.

Existing tasks retain their original provider. To connect one, close Codex Desktop
and any CLI using that task, then run `jev-bridge attach THREAD_ID` and reopen Codex.
Use the UUID from the task's copied link. The installer backs up `config.toml`.

For the CLI:

```sh
jev-codex resume --last
jev-codex exec "fix the failing test"
```

On macOS or Linux, use
`jev-bridge install --no-service` and run `jev-bridge serve` under your own supervisor.

## Routing

```text
Codex Desktop / CLI
        |
        v
  local bridge ----> Jev: choose model + effort
        |
        v
  OpenAI, using your Codex login
```

- Uses the task history and tool results to choose among your account's supported
  model-and-effort pairs, with quality first and your reasoning selection as a ceiling.
- Keeps the chosen pair through tool calls, with a checked upgrade if repeated
  failures reveal a reasoning blocker.
- Keeps the current pair if Jev is unavailable; low confidence prevents a downgrade.

Run `$jev-explain` in Codex to inspect the latest decision.
See [selection policy and benchmark sources](docs/routing.md).

## Updates

Updates are tested and activated after current requests finish.

```powershell
jev-bridge update
jev-bridge rollback
```

Rollback pauses automatic updates; `jev-bridge auto-update on` re-enables them.
See [service controls, logs and removal](docs/operations.md).

## Data

TypeSafe receives task text, tool calls and results, and model metadata for routing.
OpenAI receives the Codex conversation. Routing context and decisions are also
saved locally. See [context modes and data handling](docs/configuration.md#routing-context).

## Development

```sh
npm ci --ignore-scripts
npm test
npm run check
```

Tests run without API keys. CI covers Windows, Linux and macOS.

Based on [Jev Router](https://github.com/gargpratyush/jev-router).
[MIT](LICENSE) · [Attribution](NOTICE)
