# jevmod

Moderation for communities and apps: every message gets a probability for **spam, scam, harassment, nsfw,
off-topic, self-harm, doxxing, sexual content involving minors**, and for **rules you write in plain English**.
You set the thresholds and the actions. Every decision is logged with its numbers.

It runs on [Jev](https://typesafe.ai), TypeSafe's System One model: you ask yes/no questions about a message and
get probabilities back, no text generation. About **$0.04 per 1,000 messages** with all categories on.

Site: **https://jevmod.dev** (community owners) and **https://jevmod.dev/developers/** (packages, API, MCP, benchmark, cost calculator)

![jevmod check and the HTTP API in a terminal](docs/jevmod.gif)

```
$ jevmod check "FREE NITRO for the first 100!! claim at discord-gifts.ru/nitro"
scam 0.99      'FREE NITRO for the first 100!! claim at discord-gifts.ru/nitro'  [scam 0.99, spam 0.98, harassment 0.02]
```

Flag-only by default: nothing is deleted until you turn that on. Fails open: if Jev is unreachable, messages are
left alone and the failure is logged. Self-harm is flag-only by design so a moderator can reach out.

| you are | you get | start |
|---|---|---|
| a community owner, not technical | a Discord bot you tune with commands (Telegram with fewer commands, Reddit by env vars) | [Run the bot](#run-the-bot) |
| a developer | a CLI, a Python package, an npm package, or one HTTP call | [Developer](#developer) |
| a coding agent, or someone using one | an MCP server and a Claude Code skill that wires jevmod into a codebase | [Agents](#agents) |

On the [benchmark](BENCHMARK.md) (2,531 messages from OpenAI's moderation eval, Jigsaw and YouTube spam) jevmod
had the best AUROC in every category it was compared on in OpenAI's human-labelled set: harassment 0.93 and
sexual 0.98 against Llama Guard 3 8B, ShieldGemma 2B and toxic-bert; self-harm 0.99 and minors 0.98 against Llama
Guard, the only other system with those labels. Calibration was measured too; caveats are in the same file.

## The key, once

Every surface needs a TypeSafe API key (free tier at [console.typesafe.ai](https://console.typesafe.ai)).

```bash
pip install "jevmod[keys]"
jevmod init          # asks for the key without echo, verifies it with one call, stores it in the OS keyring
```

Resolution order everywhere (CLI, API, bots, MCP, `Moderator`): `TYPESAFE_API_KEY` in the environment, then the
keyring, then a `.env` in the current directory. In a container or a headless server `jevmod init --env-file`
writes `.env` with mode 600. `jevmod init --forget` removes the keyring entry (`pip uninstall` does not). Keys never
go into git; `.env` is ignored.

## Run the bot

### Discord

1. [Developer Portal](https://discord.com/developers/applications) → New Application → Bot → **Reset Token** →
   enable **Message Content Intent** (the only privileged intent used).
2. OAuth2 → URL Generator → scopes `bot` + `applications.commands`; permissions: Read Messages, Send Messages,
   Manage Messages, Moderate Members, Manage Channels, Embed Links. Open the URL, add it to your server.
3. `pip install "jevmod[discord]"`, set `DISCORD_TOKEN`, run `jevmod discord`.

The bot creates a private `#jevmod-log` channel and starts flagging there.

| command (server managers only) | what |
|---|---|
| `/mod status` | settings and this month's usage |
| `/mod set <category> <action> [threshold]` | any category → `off`, `flag`, `delete`, `timeout` |
| `/mod rule <name> <text> [action] [threshold]` | a rule in your words: "No politics. News about the game is fine." (max 5) |
| `/mod trust <role>` | messages from that role are never judged |
| `/mod topic <text>` | what this channel is for, in a sentence. Off-topic is judged against it, so it does nothing on its own: turn the category on with `/mod set offtopic flag`. |
| `/mod log`, `/mod recent` | choose the log channel; last decisions with probabilities |
| `/mod forget`, `/mod forget_user @member` | delete everything stored about the server, or one member |

React ❌ on a log entry to mark a false positive (that category's threshold goes up a notch), ✅ to confirm a
correct call (down a notch, floor 0.5).

### Telegram and Reddit

Telegram: [@BotFather](https://t.me/BotFather) → `/newbot`, make the bot a group admin, `pip install
"jevmod[telegram]"`, set `TELEGRAM_TOKEN`, run `jevmod telegram`. Admin commands: `/mod_status`, `/mod_set`,
`/mod_rule`, `/mod_topic`, `/mod_log`.

Reddit: for your own subreddit with your own "script" app credentials, non-commercial (Reddit's API terms).
`pip install "jevmod[reddit]"`, fill the `REDDIT_*` variables from `.env.example`, run `jevmod reddit`. Reports by
default; removal and bans are opt-in.

### What the bots send where

Only the **message text** and the **channel topic** go to TypeSafe. Author names and ids never do. Locally,
jevmod keeps a decision log (category, probabilities, action, first 300 characters); rows older than 30 days are
purged on every batch.
`/mod forget` deletes everything; leaving the server does the same. Members whose message is removed get a direct
message saying an automated system did it and how to appeal.

## Developer

### CLI

```bash
pip install jevmod
jevmod check "some text"                                   # exit 0 clean, 1 something triggered, 2 error
cat comments.txt | jevmod check --json --rule "No politics. Game news is fine." -
```

One message per line on stdin, one Jev request per 50. `--topic` turns on the off-topic check, `--threshold` sets
one for every category, `--json` prints one object per line with every probability. `examples/cli/` has a file
screener and a pre-commit hook.

### Python

```python
from jevmod import Moderator, Policy

d = Moderator().check("FREE NITRO for the first 100!! claim at discord-gifts.ru/nitro", channel_topic="gaming")
d.action, d.category, d.probability  # ('flag', 'scam', 0.99)
d.scores  # {'spam': 0.98, 'scam': 0.99, 'harassment': 0.02, 'nsfw': 0.01, ...}

p = Policy()
p.set_category("scam", "delete", 0.7)
p.set_rule("no_politics", "No political discussion. Game news is fine.", action="flag", threshold=0.8)
Moderator(policy=p).check_many(["...", "..."], channel_topic="support")  # one request for the batch
```

### npm

```ts
import { Moderator, Policy } from "jevmod";
const d = await new Moderator().check("FREE NITRO ...", { channelTopic: "gaming" });
d.action, d.category, d.scores            // same shape as Python and the HTTP API
```

Node 20+. Same questions (`jevmod/categories.json` is copied byte for byte and CI fails if it drifts), same
policy, same decision. `JevmodClient` talks to a deployed HTTP API instead, so browsers and edge functions never
hold the TypeSafe key. Express middleware in `packages/jevmod-js/examples/`. Details in
[packages/jevmod-js/README.md](packages/jevmod-js/README.md).

### HTTP API

```bash
JEVMOD_ADMIN_TOKEN=... jevmod api                     # binds 127.0.0.1; JEVMOD_HOST=0.0.0.0 to expose (Docker does)
curl -X POST localhost:8080/v1/keys -H "Authorization: Bearer $JEVMOD_ADMIN_TOKEN" \
     -H "Content-Type: application/json" -d '{"tenant":"my-app"}'          # {"api_key":"jm_...", shown once}
curl -X POST localhost:8080/v1/moderate -H "Authorization: Bearer jm_..." -H "Content-Type: application/json" \
     -d '{"messages":[{"id":"a","text":"FREE NITRO for the first 100!! claim at discord-gifts.ru/nitro"}]}'
```

| endpoint | what |
|---|---|
| `POST /v1/moderate` | up to 50 messages → decisions; the `X-Request-Id` you send comes back as `request_id` and as a response header |
| `GET/PUT /v1/policy` | thresholds, actions, rules for this tenant |
| `GET /v1/decisions` | the audit log |
| `DELETE /v1/tenant` | forget this tenant |
| `POST /v1/keys` (admin) | mint a tenant key, stored hashed |
| `GET /v1/health`, `GET /metrics` | liveness, Prometheus counters |

OpenAPI at `/docs` on a running server (a static copy at [docs/openapi.json](docs/openapi.json)), a Postman collection at [postman/jevmod.postman_collection.json](postman/jevmod.postman_collection.json). Any chatbot, forum or comment system that can make an HTTP
call can use it; the bots are adapters over the same service.

### Examples, one folder per surface

| folder | what |
|---|---|
| [`examples/sdk/`](examples/sdk) | `Moderator` basics, a custom policy with a rule, batching 50 per request |
| [`examples/cli/`](examples/cli) | `screen_file.sh` exits 1 on hits; `pre-commit.sh` blocks flagged text files |
| [`examples/api/`](examples/api) | curl, a stdlib Python client, a Node client against a local `jevmod api` |
| [`examples/discord/`](examples/discord) | run the bot; `custom_adapter.py` puts any chat platform on `ModerationService` in 20 lines |
| [`examples/agent_harness/`](examples/agent_harness) | `@guarded` decorator, Claude Agent SDK `PreToolUse`/`PostToolUse` hooks, LangChain callback |
| [`examples/input_validation/`](examples/input_validation) | FastAPI dependency that answers 422, a pydantic `ModeratedText` field |
| [`packages/jevmod-js/examples/`](packages/jevmod-js/examples) | Express middleware and a plain Node script |

## Agents

**MCP server.** `pip install "jevmod[mcp]"` then `jevmod mcp` (stdio). Tools: `moderate(texts, channel_topic?,
rules?)` returns one decision per text; `categories()` describes each category and its default threshold.

```
claude mcp add jevmod -- jevmod mcp                                   # Claude Code
{"mcpServers": {"jevmod": {"command": "jevmod", "args": ["mcp"]}}}    # Cursor, Codex, others
```

**Claude Code plugin.** This repository is its own marketplace:

```
/plugin marketplace add ohernandezdev/jevmod
/plugin install jevmod@jevmod
```

`jevmod-integrate` adds moderation to an existing codebase (detects the stack, picks SDK/npm/HTTP/MCP, wires the
key, inserts the call where it belongs, adds a real test). `jevmod-moderate` screens text or datasets from the
terminal while working. [AGENTS.md](AGENTS.md) has every signature; [docs/llms.txt](docs/llms.txt) indexes the docs.

## Categories

| category | true when | default |
|---|---|---|
| `spam` | unsolicited promotion, invite farming, bare link drops, mass mentions | flag ≥ 0.85 |
| `scam` | fake giveaways, phishing domains, impersonated support, "DM me for a deal" | flag ≥ 0.75 |
| `harassment` | insults, slurs, threats, targeted abuse, in any language | flag ≥ 0.75 |
| `nsfw` | sexual or gore content for a general audience (below the threshold means SFW) | flag ≥ 0.80 |
| `offtopic` | unrelated to `channel_topic`; needs a topic to mean anything | off, 0.90 |
| `selfharm` | the author is in crisis or considering self-harm; alert moderators, never punish | flag ≥ 0.80 |
| `doxxing` | reveals or hunts private data about a real person | flag ≥ 0.80 |
| `minors` | sexualises a minor or shows grooming behaviour | flag ≥ 0.70 |
| `rule:<name>` | your rule in plain language, exceptions included, up to 5 | flag ≥ 0.80 |

Every check returns all enabled categories at once, in one request. The questions are in
[`jevmod/categories.json`](jevmod/categories.json): one yes/no question per category with explicit true/false
criteria, the pattern of TypeSafe's guardrails cookbook. Jev's probabilities move about ±0.03 between runs, so
anything within that band of a threshold will flip; the ❌/✅ feedback and `PUT /v1/policy` exist to move the line.

## How it works

![architecture](docs/diagrams/architecture.svg)

Message → pre-filter (trusted authors, under eight letters without a link, repeats of judged text never reach
Jev) → batch for 2 s per community → **one** Jev request for the batch → probabilities → policy → action → audit
log. Batched messages are sent as a dict keyed by position; as a list, probabilities leaked between neighbours,
which the 98-message adversarial [red team](tests/data/redteam.csv) caught and which now runs as a regression
suite in CI. More in [docs/diagrams/](docs/diagrams) and [PLAN.md](PLAN.md).

## Self-host

One image, one variable picks the role: `api`, `discord`, `telegram`, `reddit`. SQLite on a volume.

```bash
cp .env.example .env && docker compose up -d              # API on :8080
docker compose --profile discord up -d                    # add the Discord bot
```

A $4/month VM, Fly.io or Railway with a volume is enough. Failure policy: Jev unreachable → decisions come back
`reason="error_open"` and nothing is acted on. There is no quota by default; `JEVMOD_MONTHLY_QUOTA=5000` pauses
judging for a tenant after 5,000 judged messages in a month as a cost guard, tells the owner once, deletes nothing.

## Public demo

The landing page's live check talks to `jevmod demo`, a separate role that keeps the key on the server and stops
at a monthly budget (`JEVMOD_DEMO_BUDGET_USD`, default $0.50), with per-visitor limits and a CORS allow-list. It
logs what visitors try (text, scores, hashed IP) for the operator. `deploy/demo/` has a Caddy + Docker compose
for a small VPS with HTTPS in two commands.

## Development

```bash
git clone https://github.com/ohernandezdev/jevmod && cd jevmod
python -m venv .venv && .venv/bin/pip install -e ".[all,dev,examples]"      # Windows: .venv\Scripts\pip
ruff check . && mypy jevmod && pytest          # offline tests run without a key; the rest hit the real API
cd packages/jevmod-js && npm ci && npm test    # same for the npm package
```

Tests never mock Jev. `tests/test_redteam.py` is the adversarial regression set; `benchmark/` reproduces
[BENCHMARK.md](BENCHMARK.md).

## License

MIT, © Omar Hernandez. See [DISCLAIMER.md](DISCLAIMER.md): decisions are probabilistic, the operator owns the
thresholds, the actions and legal compliance; not affiliated with TypeSafe, Discord, Telegram or Reddit.
