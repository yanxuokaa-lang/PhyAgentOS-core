# pi-jev

A single-file [pi](https://github.com/earendil-works/pi-mono) extension that exposes TypeSafe Jev as `jev_evaluate`. It evaluates supplied evidence against a batch of Choice, Score and Noul questions and returns the original typed judgments and probabilities.

The agent decides when to call it. It works with existing skills without changing their workflows or adding automatic routing hooks.

## Install

Requires pi 0.85.1 or later and its supported Node.js runtime. The extension uses Node built-ins and the packages provided by pi; the development dependencies are only needed to run this repository's checks.

Install the package:

```sh
pi install git:github.com/angribot/pi-jev
```

Or link the single extension file directly:

```sh
mkdir -p ~/.pi/agent/extensions
ln -s ~/repo/pi-jev/pi-jev.ts ~/.pi/agent/extensions/pi-jev.ts
```

Set `TYPESAFE_API_KEY` in the environment that starts pi. Then run `/reload` in pi. A missing key produces an error when the tool is called, rather than preventing pi from starting.

Requests use the `jev-latest` alias, so they follow TypeSafe's newest stable release. Each result includes the response's `model`, which reports the versioned ID that actually answered; pin that ID instead if you have tuned thresholds to a specific version.

## Tool input

Provide `state`, `stateFiles`, or both, plus a nonempty `questions` map:

```json
{
  "state": {
    "claim": "The SDK retries rate-limited requests automatically."
  },
  "stateFiles": [
    {
      "name": "sdk",
      "path": "./research/sdk.md",
      "startLine": 10,
      "endLine": 35
    }
  ],
  "questions": {
    "support": {
      "type": "choice",
      "instructions": "Does files.sdk.text support the complete claim in input.claim?",
      "criteria": {
        "supports": "The source supports the complete claim.",
        "contradicts": "The source contradicts the claim.",
        "insufficient": "The source does not establish the complete claim."
      }
    },
    "mentions_rate_limits": {
      "type": "noul",
      "instructions": "Does files.sdk.text discuss rate limits?"
    }
  }
}
```

Inline `state` can be a string, object or array. The extension assembles the API's shared state as:

```text
input                  Inline state, omitted when not supplied
files.<name>.path       Absolute source path
files.<name>.startLine  First selected line
files.<name>.endLine    Last selected line
files.<name>.text       Selected source text
```

File names must be unique and match `[A-Za-z][A-Za-z0-9_-]*`. Paths resolve from pi's working directory; a leading `@` is accepted. Ranges are 1-indexed and inclusive, defaulting to the entire file. Empty files, invalid ranges, missing files and binary or invalid UTF-8 content fail explicitly. Excerpts preserve interior line endings and omit the selected range's final newline; whole-file reads preserve the decoded text.

The selected text and source paths are sent to TypeSafe. Only explicitly supplied materials are included; the extension does not collect the conversation or scan the repository.

### Questions

| Type     | Criteria                                                                                        | Result                                           |
| -------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `choice` | Object with 1–255 named options; descriptions may be text, structured objects/arrays, or `null` | `choice`, `probabilities`, `confidence`          |
| `score`  | Ordered array of 2–10 descriptive levels, starting at level 0                                   | `score`, `legend`, `probabilities`, `confidence` |
| `noul`   | Optional object describing `true` and/or `false`                                                | `noul`, the probability of yes                   |

Instructions support text or structured objects/arrays. Criteria descriptions also accept `null`, following the API contract; concrete descriptions generally make better rubrics. Each question must contain its complete meaning: question IDs are only response identifiers. Questions see the same state independently, so one question cannot use another question's answer in the same call.

## Results and failures

Model-visible content is JSON containing `model`, `answers`, `usage` and `elapsedMs`. The tool also keeps the response in pi's result details for rendering. The collapsed TUI shows the number of judgments, model, elapsed time and input tokens.

- Choice/Score confidence describes distribution concentration, not correctness. Noul has no separate confidence field. The tool preserves raw outputs and leaves thresholds and actions to the caller.
- Output above pi's 50 KB / 2000-line display limit is saved as complete JSON in a private temporary directory. The tool returns a valid JSON summary with `outputPath`; use `read` to inspect it. Files remain available for resumed sessions until the operating system removes them.
- The whole operation has a 30-second deadline and respects cancellation. Connection failures, HTTP 408/429 and 5xx responses receive at most two retries, honoring `Retry-After` within the deadline. Authentication and validation failures are returned immediately.
- Invalid or incomplete API responses fail explicitly. Service failures never become negative judgments. Error bodies are omitted so they cannot echo credentials or source material into diagnostics.
- Local limits are 8 MB per source file and 192 KB per serialized API request. These are byte limits, not token estimates. TypeSafe additionally enforces its model's token limits. Reduce evidence ranges or split questions when limits are reached; input is never silently truncated.

## Prompt guidance

The tool's description and `promptGuidelines` follow the [official TypeSafe skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md): supply relevant evidence, ask narrow questions, batch independent judgments, choose the primitive according to the answer's meaning, and interpret uncertainty in the task's context.

`writing-for-agents` was used to organize and shorten those instructions: invocation guidance stays near the tool, parameter-specific rules stay in the schema, and detailed operational reference stays here. TypeSafe's current documentation remains authoritative for API behavior:

- [HTTP API](https://docs.typesafe.ai/api.md)
- [State](https://docs.typesafe.ai/concepts/state.md)
- [Primitives](https://docs.typesafe.ai/primitives.md) and [structured criteria](https://docs.typesafe.ai/primitives/advanced.md)
- [Confidence](https://docs.typesafe.ai/confidence.md)
- [Models and limits](https://docs.typesafe.ai/models.md)

## Development

```sh
npm ci
npm run typecheck
npm run lint
npm run format:check
npm test
```

Tests load the real extension through pi's extension loader, validate tool arguments through pi-ai, and exercise the registered tool with temporary source files and a fake HTTP boundary. They require no API key or live TypeSafe requests. They verify integration behavior, not Jev's judgment accuracy on real tasks.

The deployable extension remains entirely in `pi-jev.ts`; tests and documentation are separate repository artifacts.
