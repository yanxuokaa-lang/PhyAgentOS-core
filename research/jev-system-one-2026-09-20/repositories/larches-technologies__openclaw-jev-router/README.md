# OpenClaw Jev Router

An OpenClaw-native TypeScript plugin that uses the [TypeSafe Jev](https://docs.typesafe.ai/) System One API for:

- per-turn tool-family recommendations through `before_prompt_build`;
- optional narrowing of the host-approved tool surface with `toolsAllow`;
- reusable `jev_classify`, `jev_score`, `jev_filter`, and `jev_rank` agent tools.

The router is **dry-run by default**, **fails open**, and skips external routing when a prompt looks credential-bearing.

## Status

This is an initial usable release. The plugin targets OpenClaw Plugin API `>=2026.9.4` and Node.js `>=24.16`.

## How routing works

1. OpenClaw calls the plugin's `before_prompt_build` hook with the current prompt.
2. Local privacy checks reject prompts that match conservative credential patterns or exceed `maxPromptChars`.
3. The plugin sends the remaining prompt and configured tool-family descriptions to TypeSafe's documented endpoint:
   `POST https://api.typesafe.ai/v1/systemone`.
4. Jev returns a Choice answer with a selected family and confidence.
5. The plugin applies a route only when confidence meets `confidenceThreshold` and `dryRun` is `false`.
6. The hook returns `toolsAllow`, which can only narrow the tool surface OpenClaw already approved.

Timeouts, missing credentials, API errors, unknown families, and low confidence leave the existing tool surface unchanged.

> `toolsAllow` is turn-scoped routing, not a security enforcement boundary. OpenClaw runtimes differ; restrictive values are not supported by the Codex app-server harness. Operator tool policy remains authoritative.

## Installation

```bash
npm install
npm run check
```

For local OpenClaw development, build and link/install the package using the applicable OpenClaw plugin workflow. Non-bundled conversation hooks require explicit permission:

```json5
{
  plugins: {
    entries: {
      "openclaw-jev-router": {
        enabled: true,
        hooks: {
          allowConversationAccess: true,
          allowPromptInjection: true,
        },
        config: {
          dryRun: true,
        },
      },
    },
  },
}
```

See [`config.example.json5`](./config.example.json5) for a fuller example.

## Authentication

Set the API key in the Gateway process environment or through your existing secret-management path:

```bash
export TYPESAFE_API_KEY="..."
```

The key is read at runtime, used only in the `Authorization: Bearer` request header to the fixed official endpoint `https://api.typesafe.ai/v1/systemone`, and is never included in tool output or logs. Do not put it in plugin config or commit it to the repository.

## Configuration

| Field | Default | Description |
| --- | ---: | --- |
| `enabled` | `true` | Enables automatic prompt routing. Tools remain registered according to OpenClaw policy. |
| `dryRun` | `true` | Logs the recommended family without returning `toolsAllow`. |
| `confidenceThreshold` | `0.75` | Minimum Choice confidence required to apply a route. |
| `timeoutMs` | `2500` | TypeSafe request timeout and hook budget basis. |
| `model` | `jev-latest` | TypeSafe model alias. |
| `maxPromptChars` | `12000` | Prompts above this length are not sent externally. |
| `alwaysAllow` | `[]` | Canonical tool names included in every applied family. |
| `toolFamilies` | built-in families | Map of family descriptions and canonical OpenClaw tool names. |

At least two valid custom families are required; otherwise the built-in family map is used.

## Optional Jev tools

The tools are marked optional and need explicit OpenClaw tool-policy opt-in, for example:

```json5
{
  tools: { allow: ["openclaw-jev-router"] }
}
```

All four tools transmit caller-provided non-sensitive state to TypeSafe:

- `jev_classify`: wraps a Jev Choice question.
- `jev_score`: wraps a Jev Score question with 2-10 ordered levels.
- `jev_filter`: asks one independent Noul question per item in a single request, then applies a local threshold.
- `jev_rank`: asks one independent Noul question per item in a single request, then sorts locally by the returned values.

The official API does not expose separate classify/filter/rank endpoints; these are small application-level wrappers around `/v1/systemone` primitives.

## Security and privacy

### Data sent externally

Automatic routing sends only the current prompt, not session history. Jev tools send the state, question, criteria, items, and optional context supplied to that tool.

### Local skip checks

The router and tools refuse input matching conservative patterns for:

- private-key blocks;
- Bearer or Basic authorization headers;
- credential assignments such as `api_key=...`, `password: ...`, or `client_secret=...`;
- AWS access keys, GitHub tokens, Slack tokens, and JSON Web Tokens.

These checks reduce accidental disclosure; they cannot detect every secret. Keep dry-run enabled during evaluation, avoid sending sensitive prompts, and enforce data-handling requirements outside this plugin.

### Failure behavior

- Missing `TYPESAFE_API_KEY`: fail open for routing; tools return an error.
- Timeout or network/API error: fail open for routing; tools return an error.
- Confidence below threshold: fail open.
- Credential-like prompt: skip routing before any network request.
- Dry run: no tool restriction is returned.

The plugin does not retry requests in this version, avoiding extra latency and duplicate external processing in the prompt hook.

## Development

```bash
npm ci
npm run build
npm test
npm run plugin:validate
npm run pack:check
```

`plugin:validate` loads the mixed hook/tool plugin through an isolated temporary OpenClaw state, checks runtime inspection, and requires a clean `plugins doctor` result. OpenClaw's `plugins build`/`plugins validate --entry` authoring commands are for tool-only or feature-authoring metadata entries and reject a normal mixed `definePluginEntry` module, so they are not used as the mixed-plugin validation gate.

Tests mock `fetch`; they do not require or use a real TypeSafe API key.

## References

- [TypeSafe HTTP API](https://docs.typesafe.ai/api)
- [TypeSafe JavaScript SDK docs](https://docs.typesafe.ai/sdk/javascript)
- [OpenClaw building plugins](https://docs.openclaw.ai/plugins/building-plugins)
- [OpenClaw prompt and session hooks](https://docs.openclaw.ai/plugins/hooks/prompt-and-session)

## License

MIT
