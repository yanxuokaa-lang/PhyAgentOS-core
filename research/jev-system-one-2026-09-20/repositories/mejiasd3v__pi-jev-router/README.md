<p align="center">
  <img src="https://raw.githubusercontent.com/mejiasd3v/pi-jev-router/main/assets/logo.png" alt="Jev Router logo" width="144" height="144">
</p>
<h1 align="center">Jev Router</h1>
<p align="center">Choose once. Stay pinned.</p>
<p align="center">
  <a href="https://www.npmjs.com/package/pi-jev-router"><img src="https://img.shields.io/npm/v/pi-jev-router?style=flat-square&amp;color=67e8b4&amp;logo=npm&amp;logoColor=white" alt="npm version"></a>
  <a href="https://github.com/mejiasd3v/pi-jev-router/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/mejiasd3v/pi-jev-router/test.yml?branch=main&amp;style=flat-square&amp;label=tests&amp;logo=github" alt="Tests"></a>
  <a href="https://github.com/mejiasd3v/pi-jev-router/blob/main/LICENSE"><img src="https://img.shields.io/github/license/mejiasd3v/pi-jev-router?style=flat-square&amp;color=8b9cff" alt="MIT license"></a>
  <a href="https://pi.dev"><img src="https://img.shields.io/badge/Pi-0.85.1%2B-f8b86d?style=flat-square" alt="Pi 0.85.1 or later"></a>
</p>

Let [TypeSafe's Jev](https://vercel.com/ai-gateway/models/jev) choose a model and reasoning effort for [Pi](https://pi.dev), then keep both fixed for the session. Generation uses your existing Pi providers and credentials.

## Get started

Requires Pi **0.85.1+**, Node.js **22.19+**, and a **Vercel AI Gateway key**.

```sh
pi install npm:pi-jev-router
```

Git also works: `pi install git:github.com/mejiasd3v/pi-jev-router`. Keep only one installation.

1. Use `/login` for your generation provider and `/login vercel-ai-gateway` for Jev. `AI_GATEWAY_API_KEY` also works.
2. Run `/reload`, then `/model auto/jev`.
3. Start with your actual task. `/jev` shows the pin, selected effort, and fork suggestions.

## Configure

Merge `jevRouter` into **global** `~/.pi/agent/settings.json`, then `/reload`:

```json
{
  "jevRouter": {
    "options": {
      "openai-codex/gpt-5.6-luna": {
        "description": "Small fixes, tests, and routine implementation.",
        "thinking": "auto"
      },
      "openai-codex/gpt-6-astra": {
        "description": "Architecture, difficult debugging, and complex reasoning.",
        "thinking": "auto"
      }
    },
    "fallback": "openai-codex/gpt-6-astra",
    "timeoutMs": 5000,
    "monitor": true,
    "skills": false
  }
}
```

Only listed, authenticated models are eligible; `fallback` must be listed too. Routes replace the default list; they aren't merged. `PI_CODING_AGENT_DIR` is respected; project settings cannot override routing.

Without configuration, defaults are Luna/`max`, Astra/`xhigh`, Astra fallback, a five-second timeout, and monitoring on. The example above enables automatic effort.

### Thinking

| `thinking` | Behavior |
| --- | --- |
| `"auto"` | Jev chooses the lowest effort it judges sufficient. |
| `"high"` | Force a level, clamped to the model's capabilities. |
| `{"low": "Small changes", "high": "Hard problems"}` | Customize the allowed choices and their descriptions. |
| Omitted | Inherit Pi's thinking level when the pin is created. |

Levels: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Automatic choices are filtered to supported levels. Model and effort are chosen together, not in separate evaluations.

### Automatic skill loading (opt-in)

Set `"skills": true` inside your existing global `jevRouter` configuration, then `/reload`. It defaults to `false` and works with both `auto/jev` and concrete models, independently of `monitor`.

Before generation for each new user turn, including steering messages, Jev checks Pi's discovered skill names and descriptions against recent user/assistant text. It loads up to **three** matches with a returned probability of at least **0.8**. These probabilities are heuristic relevance signals, not guarantees.

- Uses Pi's catalog, including its trust and discovery settings. Skills marked `disable-model-invocation` are never auto-loaded.
- Injects full skill instructions with their source path and reference directory. It does not execute scripts or eagerly load linked references.
- Skips skills already included as `<skill>` blocks or successfully loaded through a complete `read` call in the current context. Path aliases are canonicalized. Arbitrary shell commands or unmarked pasted instructions cannot reliably be recognized as skill loads.
- Saves selections and instructions on the active session branch. Tool continuations and `/reload` reuse them without another evaluation or file read. Skills removed by compaction or branch navigation can be selected again when needed.
- Makes at most one additional evaluation per user turn, bounded by `timeoutMs` with no retries and the same **28,000-byte** request budget. Older history is dropped first; oversized tasks/catalogs skip selection rather than using a partial task. Full injected instructions are limited to **50,000 bytes** per turn; unreadable or oversized skills are skipped with a warning.

`/jev` shows whether this feature is enabled. Failures leave ordinary skill loading available. Turning it off stops selection and reinjection; it does not erase instructions the model already read or remove saved session records.

### Long prompts

The latest task takes priority; older history is dropped before splitting it. Requests have a **28,000-byte serialized UTF-8 budget**, including route descriptions. This is a conservative proxy for Jev's [roughly 32K-token request budget](https://docs.typesafe.ai/primitives#ask-speculative-questions), not an exact token count.

Tasks that don't fit are split into at most **eight overlapping chunks**, evaluated **two at a time**, then combined in one final evaluation. The final evaluation is instructed to weigh requirements, not vote counts. This is still a heuristic: relationships across sections may be missed.

Tasks over **192,000 UTF-8 bytes**, excessive chunk plans, or incomplete evaluations use fallback (or retain the existing pin during monitoring). The coding model always receives the original input; its context limits still apply.

## Session behavior

- **Pin once.** Model and effort survive tool calls, compaction, `/reload`, and `/resume`. `/new`, `/fork`, and `/clone` choose afresh. Configuration changes don't rewrite existing pins.
- **Suggest, never switch.** Monitoring checks new user text and may suggest a fork with another model, once per alternative per session. Use `/fork`, then `/model` and `/thinking` in the fork to follow it. No automatic forks or model switches.
- **Control overhead.** Evaluation timeouts retry up to three attempts of `timeoutMs` each (1 to 60,000 ms). The entire operation shares a ceiling of **3 × `timeoutMs`**, including chunks and combination: 15 seconds by default. Set `"monitor": false` to disable advisory checks; tool continuations don't trigger them.
- **Fail explicitly.** Initial routing failures use the fallback, with its fixed/inherited effort or highest supported automatic choice. If an existing pin becomes unavailable or cannot accept the input, the router errors instead of switching.

Context limits follow the pinned backend. The status and `/jev` show its effort; Pi's thinking picker does not track automatic choices. Selecting a concrete model bypasses model routing, but not opt-in skill selection. Deferred/background generation is unsupported by `auto/jev`.

## Privacy and cost

Routing and monitoring consider up to **eight recent user/assistant text messages**, limited to **192,000 UTF-8 bytes of source text**. Evaluations send selected text, route/effort descriptions, and chunk assessments to Vercel/TypeSafe. Overlaps, excerpts, and retries can send the same text more than once. System prompts, reasoning blocks, tool-result blocks, images, and provider credentials are excluded. **Conversation text is not redacted and may contain secrets.**

Opt-in skill selection additionally sends eligible skill names and descriptions to Vercel/TypeSafe. Skill file contents are read locally and stored in the session; automatically injected skill messages are excluded from subsequent Jev evaluations. Manually pasted or expanded skill instructions in user messages remain conversation text.

Gateway evaluations are billed separately. Chunking uses at most nine evaluations before timeout retries, or 27 attempts total. `/jev` estimates sum returned usage; failed, cancelled, or timed-out calls may still be billed. Skill-selection evaluations are additional and are not included in `/jev` routing estimates. Evaluation costs are not in Pi's footer totals. Pinning favors cache reuse but guarantees neither cache hits nor savings.

<details>
<summary>Migrating from file-based configuration</summary>

Move the old `routes.json` contents under `jevRouter` and unset `JEV_ROUTES_FILE`; neither is read anymore. Sessions created before pinning was introduced select a pin on their next main request.

</details>

## Development

```sh
nub install --frozen-lockfile --ignore-scripts
nub run test
```

Tests mock network responses; no API keys or paid requests are needed.

## Publishing

`.github/workflows/publish.yml` publishes stable GitHub releases to npm using [trusted publishing](https://docs.npmjs.com/trusted-publishers/). It checks that the release tag matches `package.json`, installs from the frozen lockfile, and runs tests before publishing. Prereleases are skipped. The publish step uses npm's native OIDC flow; installs and tests use Nub.

### One-time npm setup

In [pi-jev-router package settings](https://www.npmjs.com/package/pi-jev-router/access), add a **GitHub Actions** trusted publisher:

| Field | Value |
| --- | --- |
| Organization or user | `mejiasd3v` |
| Repository | `pi-jev-router` |
| Workflow filename | `publish.yml` |
| Environment name | Leave blank |
| Allowed actions | Allow direct `npm publish`, not just staged publishing |

No npm token or GitHub secret is needed. Keep account 2FA enabled. This connection must be saved on npm before the first automated release; committing the workflow alone does not authorize npm publishing.

### Release a version

1. Bump `package.json`, commit, and push to `main`.
2. Create and push the matching `vX.Y.Z` tag.
3. Publish its GitHub release, for example `gh release create vX.Y.Z --verify-tag --generate-notes`.
4. Wait for **Publish to npm** to succeed and verify the new npm version.

Publishing a GitHub release triggers npm publication; pushing a tag alone does not. Release tags must include the publish workflow. A failed run can be rerun after fixing the npm connection; an already-published npm version cannot be overwritten.

[MIT](LICENSE).
