# opencode-toolrouter

An [opencode](https://opencode.ai) plugin that sends the model only the MCP tools each request needs.

opencode sends every MCP tool schema to the model on every step. With a few large MCP servers, that is tens of thousands of tokens before the model reads your request. Some models cannot fit it at all. This plugin asks [TypeSafe's Jev](https://typesafe.ai) which tools a request needs, in one call of about 1 second. It then hides the other MCP tools for that request. Built-in tools (`read`, `edit`, `bash`, ...) are never touched.

You bring your own TypeSafe API key. It works with any model provider opencode supports.

## Measured

Real opencode 1.18.31 against 18 mock MCP servers (296 real tool schemas) and a mock model that records
every request, over 72 labeled prompts (`bench/opencode_e2e.py`):

| | Tools sent to the model | Tool schemas per model call | Needed tool loaded | Median wall time |
|---|---|---|---|---|
| opencode alone | 306 | ~90,200 tokens | 70/70 | 1.8 s |
| with this plugin | 17.7 | **~7,300 tokens (-92%)** | 69/70 | 3.5 s |

Every model call in a request carries the tool schemas, so the saving repeats on every step.
Routing added about 1 s per user message, plus opencode's own startup. No run failed, and none fell back
to loading everything. The one miss was "Is WEB-1234 going to breach its SLA?", where the router picked
other Jira tools but not `jira_get_issue_sla`; `find_tools` exists for that case.

The mock model answers immediately instead of using tools, so these numbers measure what reaches the
model, not task success. Task quality with a real model is not measured yet.

See [docs/cost-report.md](docs/cost-report.md) for what this saves in money, including how prompt caching changes it.

## Install

```bash
git clone <this repo> && cd opencode-toolrouter
npm install && npm run build
export TYPESAFE_API_KEY=...   # https://console.typesafe.ai/settings/keys
```

Add the plugin to your `opencode.json`, with an absolute path to the build:

```json
{
  "plugin": [
    ["/absolute/path/to/opencode-toolrouter/dist/index.js", { "alwaysLoad": ["github"] }]
  ]
}
```

## How it works

1. **Startup.** The plugin reads the `mcp` section of your config, connects to each enabled server, and lists its tools. It caches the list in `~/.cache/opencode-toolrouter/`, so later starts do not reconnect. OAuth servers are skipped, and their tools are never hidden.
2. **Each new user message** (the `chat.message` hook). The plugin sends your request and a little recent conversation to Jev. One request asks, per server: is it needed, which tool comes first, and which tool does the main action.
3. **Hide.** For every MCP tool Jev did not pick, the plugin sets `message.tools[name] = false`. opencode drops those tools from every model call made for that message. Tools you set to `true` yourself stay visible.
4. **Fallback.** If the model needs a hidden tool, it calls `find_tools` to search for it, then `use_tool` to run it. `use_tool` asks permission under the tool's own name, so your approval rules still apply.

If routing fails or takes too long, nothing is hidden. The request runs as if the plugin were not there.

## Options

| Option | Default | Meaning |
|---|---|---|
| `apiKey` | `TYPESAFE_API_KEY` | TypeSafe API key |
| `alwaysLoad` | `[]` | Server names or tool ids that are never hidden |
| `minTools` | `30` | Do not route when your MCP servers have fewer tools than this |
| `maxTools` | `10` | Most MCP tools kept per request |
| `perServer` | `2` | Top tools kept per chosen server, for each of "first" and "main action" |
| `usesThreshold` | `0.5` | Keep a server when Jev's "is it needed" score reaches this |
| `noneThreshold` | `0.9` | Hide all MCP tools when Jev is this sure none are needed |
| `fallback` | `true` | Add `find_tools` and `use_tool` |
| `timeoutMs` | `8000` | Stop waiting for routing after this long, and hide nothing |
| `contextChars` | `1500` | Characters of recent conversation sent with the request |
| `refreshCatalog` | `false` | List tools from every server again, ignoring the cache |

## Limits

- **Tools change per user message.** Providers with prompt caching write a new cache once per user message. Steps within that message still reuse the cache.
- **`use_tool` runs a second copy of the MCP server.** Stateful servers, such as a browser session, do not share state with opencode's own copy. Put such servers in `alwaysLoad`.
- **Routing adds about 1 second** per user message.
- **Remote servers that need OAuth** are not routed.

## Development

```bash
npm test                      # unit tests; spawns small mock MCP servers (needs python3)
npm run build
python3 bench/opencode_e2e.py # real opencode + 18 mock MCP servers + a mock model (needs TYPESAFE_API_KEY)
```

`bench/` holds 296 real tool schemas from 18 common MCP servers, mock servers that serve them, 72 labeled prompts, and a mock OpenAI-compatible model that records the tools opencode sends.
