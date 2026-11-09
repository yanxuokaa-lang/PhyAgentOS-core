# jev-reflex

**Claude thinks, Jev reacts.** This is an MCP server that lets Claude hand a whole browser task to
[TypeSafe's Jev](https://docs.typesafe.ai/introduction). Jev makes each click/type/select decision in about 100 ms.
Claude stays in charge of planning the task and verifying the result.

```text
you ──▶ Claude ── browse(url, goal) ──▶ jev-reflex ──▶ Chrome (background tab)
          ▲                                 │
          │                                 │ loop until done:
          │                                 │   read page → Jev picks action (~100 ms) → execute
          │                                 ▼
          └──── status · steps with probabilities · final page text
```

---

## Why

Browser tools for LLM agents usually work one step at a time. The model looks at the page, picks a click, waits for
the result, and looks again. Every one of those steps is a full round trip to a frontier model: several seconds and
thousands of tokens per click. A 15-click form costs 15 of them.

Most of those steps don't require reasoning. "Which of these 40 elements is the *Where to?* field?" is a choice from
a list, not an open question. Psychologists call this kind of fast judgement **System 1**. Slow, deliberate
reasoning is **System 2**.

Jev is a *System One model*. It never generates free text. It gets a state and a fixed set of options, and it returns
one of those options with calibrated probabilities. That makes it fast, cheap, and unable to invent an element that
is not on the page.

jev-reflex splits the work between the two models:

| | Claude (System 2) | Jev (System 1) |
| --- | --- | --- |
| Role | decides *what* to do | decides *which element, now* |
| Calls per task | 1 `browse` call, plus verification | one per step |
| Output | plans, goals, judgement | a typed choice from the element table |
| Latency | seconds | ~100 ms (TypeSafe's figure) |

The browser loop comes from [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast). This project
exposes it as an MCP tool. It also adds what an orchestrating LLM needs: a result it can verify, loop detection, a
hard time limit, and a handoff when Jev gets stuck.

## How a run works

1. **Claude calls `browse`** with a URL, a goal that says when to stop, and the exact strings to type:
   `goal="Find one-way flights from Zurich to London on 20 September 2026 for one adult. Stop when flight options
   are visible."`, `values=["Zurich", "London", "20 September 2026"]`.
2. **jev-reflex opens a background tab** in your Chrome and reads the page in a single call. The result is a numbered
   table of every visible control:
   ```text
   [1] button    Change ticket type · Round trip
   [2] combobox  Where from?        · San Francisco
   [3] combobox  Where to?          · empty
   ```
3. **Jev picks an operation and a target** in one request: `CLICK [1]`, `TYPE_TEXT [3]`, `SELECT`, `SCROLL`, `WAIT`,
   `DONE` or `BLOCKED`. Every choice comes with a probability.
4. **Claude supplies the text and Jev decides where it goes.** For `TYPE_TEXT`, Jev picks which of the `values`
   belongs in the selected field ("London" goes in *Where to?*). That is one more ~100 ms choice, with no text model
   and no generated text. If no value fits, the run stops and Claude takes over. If you leave `values` out, a small
   text model you configure infers the value from the goal instead.
5. **The action is executed safely.** Before input, the target is rechecked against the live page: it must still
   exist, be visible, and not be covered by another element. If the page changed, the decision is discarded and the
   loop observes again.
6. **The loop repeats** until Jev says `DONE` or `BLOCKED`, the same page comes back a third time (`looping`), or
   `max_seconds` runs out.
7. **Claude gets the result back.** It contains the status, every step with its probability, and the final page
   text. If the run did not finish, it also contains the element table, so Claude can take over from where Jev
   stopped.

## Measured

| Task | Result | Time |
| --- | --- | --- |
| example.com → *"Click 'Learn more'. Stop when the IANA example-domains page is open."* | `done`, 1 step, probability 1.0 | **1.96 s** |
| Wikipedia search for *Gödel's incompleteness theorems*, with `values` and no text model | `done`, type + click | **3.39 s** |
| Google Flights, one-way ZRH→LON on 20 Sep 2026 for 1 adult, with `values` and no text model | `done`, 11 steps, 21 results | **13.0 s** |
| Google Flights ZRH→LON search (upstream demo, [their measurements](https://github.com/browser-use/jev-ultrafast/blob/main/docs/performance.md)) | done | 7.1 s |

The first three rows were measured through this MCP server, end to end, on Windows 11 with a real Chrome. The last row is
jev-ultrafast's own published figure. A handful of runs is not a benchmark. Run your own tasks before relying on it.

## When to use it

**Good fit:** tasks inside one site with a clear finish line, for example searches, filters, form filling,
navigating to a known page, or reaching a results view. Also any flow where Claude would otherwise spend a dozen
tool calls on clicks.

**Poor fit:** open-ended research across many sites, tasks where reading and judging the content is the actual work
(Claude should do that part), and anything that involves iframes, shadow DOM, canvas, file uploads or pop-up
windows, which the upstream loop does not support.

## Install

### Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Google Chrome with remote debugging enabled. Open `chrome://inspect/#remote-debugging` and turn it on, or run
  `uvx browser-harness --doctor` and follow its prompts
- A **TypeSafe API key**. Jev is in early access
- *Optional:* an OpenAI-compatible text model key. You only need it if you want field values inferred from the
  goal instead of passed in `values`

### Claude Code

```bash
claude mcp add jev --scope user -e TYPESAFE_API_KEY=your-typesafe-key \
  -- uvx --from git+https://github.com/MSalvalaggio/jev-reflex jev-reflex
```

That is all you need: Claude passes `values`, so no text model is involved. To enable the text-model fallback, also
add `-e TEXT_MODEL_API_KEY=… -e TEXT_MODEL_BASE_URL=https://openrouter.ai/api/v1 -e TEXT_MODEL=inception/mercury-2.5
-e TEXT_MODEL_REASONING=none`.

Start a new session, then ask something like *"use jev to find one-way flights from Zurich to London on 20
September"*.

### Claude Desktop and other MCP clients

```json
{
  "mcpServers": {
    "jev": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/MSalvalaggio/jev-reflex", "jev-reflex"],
      "env": { "TYPESAFE_API_KEY": "your-typesafe-key" }
    }
  }
}
```

### Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | — | Required |
| `TYPESAFE_MODEL` | `jev-latest` | |
| `TEXT_MODEL_API_KEY` | — | Optional fallback, used only when a goal types text and `values` is omitted |
| `TEXT_MODEL_BASE_URL` | `https://api.deepseek.com/v1` | Any OpenAI-compatible `/chat/completions` endpoint |
| `TEXT_MODEL` | `deepseek-chat` | |
| `TEXT_MODEL_REASONING` | — | Set to `none` to disable reasoning on OpenRouter models |

## How Claude decides to use it

Claude chooses tools on its own. The server gives it two signals:

- **Server instructions.** Claude Code adds these to the system prompt. They tell Claude to use `browse` before
  step-by-step browser tools for any interaction with a website, list the cases where it should not (reading a
  known URL, debugging a local dev server, visual checks, logins, payments), and describe what to do with each
  status, including falling back to another browser tool from the returned `url`.
- **The tool description**, which is what Claude sees when it searches for a tool to load.

If you have other browser tools installed and want to make the preference explicit, drop a rule into
`~/.claude/rules/jev.md`:

```markdown
Use the jev MCP tool `browse` for any task that needs interacting with a live website (searching on a site,
forms, filters, dates, dropdowns, reaching a page through menus). Prefer it over step-by-step browser tools; if it
is deferred, load it with ToolSearch (`select:mcp__jev__browse`). Always give `goal` a stop condition and pass
every string to type in `values`. Never let it submit orders, payments, messages or deletions without asking.
```

## Tool reference

### `browse(url, goal, values=None, max_seconds=60)`

```json
{
  "status": "done",
  "elapsed_ms": 1956,
  "url": "https://www.iana.org/help/example-domains",
  "title": "Example Domains",
  "page_text": "first 4000 characters of visible text",
  "steps": [
    { "action": "Learn more", "kind": "click", "text": null,
      "probability": 1.0, "confidence": 0.96, "page_changed": true }
  ]
}
```

| Status | Meaning | What Claude should do |
| --- | --- | --- |
| `done` | Jev reports the goal is met | Check `page_text`. `done` is Jev's own claim, not proof |
| `blocked` | Jev found no way forward, or the page stopped changing | Read `elements` and decide, or rephrase the goal |
| `looping` | The same page was reached a third time | Usually means a missing stop condition. Add one |
| `timeout` | `max_seconds` ran out | Split the goal into smaller ones |
| `error` | Model or provider failure, step budget reached, or no entry in `values` fits a field. The failed step was not executed | Read `error`, and add the missing value if that was the cause |

Every status except `done` includes `elements`, the indexed controls of the final page.

### Writing good goals

- **Pass every string to type in `values`**, exactly as it should appear. Jev only decides which one goes in
  which field, so nothing can be typed that you didn't supply.
- **State a stop condition.** Without *"stop when …"*, Jev keeps browsing until the run hits `looping`.
- **Keep one goal per site.** For multi-site work, let Claude chain several `browse` calls.

## Safety

- **It runs in your real Chrome profile**, including your logged-in sessions. Only give it goals you would click
  through yourself. Turn remote debugging off when you are done: while it is on, any local program can control
  Chrome.
- **Model output never becomes code.** Every action targets an element that was observed on the page and rechecked
  just before input. Nothing the models return is used as a selector, a coordinate or JavaScript.
- **Runs are bounded:** by `max_seconds`, by the 60-action budget of jev-ultrafast, and by loop detection.
- **Jev can click any control on the page, including submit and buy buttons.** Nothing restricts it to "safe"
  actions. Keep goals explicit about where to stop, and don't delegate anything you wouldn't want done unattended.

## Development

```bash
uv sync
uv run pytest                      # offline, no API calls
uv run ruff check . && uv run ruff format --check .
uv run python scripts/smoke.py     # live: a few paid Jev calls; needs TYPESAFE_API_KEY and Chrome
```

The whole server is [one file](src/jev_reflex/__init__.py) of about 90 lines. The browser loop lives upstream and
is pinned to a specific commit.

## Credits

- [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) (MIT): the browser loop, DOM snapshot and
  safe executor
- [TypeSafe](https://typesafe.ai): the Jev model
- [Browser Harness](https://github.com/browser-use/browser-harness): the Chrome connection

This is an independent project. It is not affiliated with Browser Use, TypeSafe or Anthropic.

## License

MIT
