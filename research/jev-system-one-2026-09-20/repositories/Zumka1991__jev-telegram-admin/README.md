# Jev Telegram Guard

AI moderator for Telegram groups. The bot reads messages and uses the
**Jev** model (TypeSafe System One via OpenRouter) to detect abuse and take
action automatically — delete a message, mute or ban a member — according to
per-chat settings.

[Русская версия](README.ru.md)

📖 **New here? Follow the step-by-step [Setup Guide](docs/SETUP.md).**

## Features

- **Detection categories**: profanity, insults, fraud/phishing, bullying,
  trolling, spam (including mass "job offers" and recruiter scams), and flood.
- **AI decisions**: Jev is a structured-decision model, not a chat model. It
  returns calibrated probabilities plus a recommended punishment and mute
  duration — so even the *penalty* can be chosen by the model.
- **Smart spam heuristics**: identical text cross-posted across many chats and
  link/DM-heavy posts raise the spam score.
- **Complete message coverage**: text, media captions, and edited messages;
  stickers and media count toward flood detection, while a photo album counts
  as one event.
- **Complex senders**: messages from other bots, channels, and anonymous admins
  cannot bypass checks; when such a sender cannot be muted, the violating
  message is deleted instead.
- **Configurable per chat**: for every category choose `off`, `auto`, `warn`,
  `delete`, `mute` or `ban`; set thresholds, warning limits and mute duration.
- **Multi-language interface**: English, Russian, Spanish, Portuguese, Arabic.
- **Localized Telegram command menu** per user language.
- **SQLite storage**: settings, violations and per-user stats.
- **Runs offline fallback**: if no OpenRouter key is set, a lightweight
  rule-based engine keeps the bot useful.

## How it works

1. Each group message is sent to the **Jev Decisions API** instead of a chat
   completion. Jev answers typed questions about the message: yes/no
   probabilities (`noul`), a choice (`choice`) and an ordered score (`score`).
2. The bot asks for a probability per category, the spam type, the severity
   level and the **recommended punishment** (with mute duration).
3. Heuristics run on top: the same text broadcast to several chats and posts
   with many links/contacts increase the spam score.
4. The result is compared with the chat threshold and settings, then applied.
5. Everything is stored in SQLite: chat settings, violations, user stats.

A redelivered update does not cause a second punishment. When Telegram upgrades
a basic group to a supergroup, the bot moves its settings and statistics to the
new chat ID.

## Quick start (Docker)

```bash
cp .env.example .env
# set BOT_TOKEN and OPENROUTER_API_KEY
docker compose up -d --build
docker compose logs -f
```

## Quick start (local)

Requires **Python 3.10+** (3.12 recommended).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your keys
python -m app.main
```

## Configuration

1. Create a bot with [@BotFather](https://t.me/BotFather) and get the token.
2. Get an OpenRouter key: https://openrouter.ai/keys
3. Add the bot to a group and grant the rights:
   - **Delete messages**
   - **Restrict members**

> **Important:** Telegram enables *privacy mode* for new bots, so in regular
> groups they only receive commands and replies. Disable it with BotFather
> (`/setprivacy` → select the bot → **Disable**) or promote the bot to
> administrator. See [Troubleshooting](#troubleshooting).

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token | — |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `JEV_MODEL` | Jev model id | `~typesafe/jev-latest` |
| `JEV_ENDPOINT` | Decisions API endpoint | `https://openrouter.ai/api/alpha/decisions` |
| `DATABASE_URL` | database connection string | `sqlite+aiosqlite:///./data/jev.db` |
| `DEFAULT_THRESHOLD` | model confidence threshold | `0.55` |
| `DEFAULT_WARN_LIMIT` | warnings before a ban | `3` |
| `DEFAULT_MUTE_MINUTES` | default mute duration | `60` |
| `DEFAULT_LANGUAGE` | default interface language | `en` |
| `DEFAULT_SELF_DELETE_SECONDS` | auto-delete the bot's messages after N seconds (`0` = off) | `0` |
| `BACKLOG_ENABLED` | process messages missed while the bot was offline | `true` |
| `BACKLOG_MAX_AGE_HOURS` | ignore missed updates older than this | `24` |
| `BACKLOG_LIMIT` | maximum number of missed updates to process | `200` |

## Commands

| Command | Action |
|---|---|
| `/settings` | chat settings menu (inline buttons) |
| `/stats` | violation stats for the last 7 days |
| `/check <text>` | analyze a text without acting |
| `/warn` | warn a member (reply to their message) |
| `/unwarn` | remove a member's warnings (reply) |
| `/resetwarns` | reset warnings (reply) |
| `/help` | help |

## Chat settings

In `/settings`, each category can be set to one of:

- `off` — ignore;
- `auto` — **the bot decides** (delete / mute / ban) from the severity and
  Jev's own punishment recommendation;
- `warn` — warn (then ban once the warning limit is reached);
- `delete` — delete the message;
- `mute` — mute the member;
- `ban` — ban the member.

You can also configure the confidence threshold, warning limit, mute duration,
whether admins are ignored, notifications, and the interface language.

## Languages

The interface ships with five languages and can be switched per chat via
`/settings` → 🌐 **Language**:

| Code | Language |
|---|---|
| `en` | English |
| `ru` | Русский |
| `es` | Español |
| `pt` | Português |
| `ar` | العربية |

Translations live in `app/i18n/locales/<code>.py` as a flat `STRINGS` dict.
To add a language: copy `en.py`, translate the values, register the locale in
`app/i18n/__init__.py` (`LOCALES`, `LANGUAGE_ORDER`, `LANGUAGE_NAMES`,
`LANGUAGE_FLAGS`) and add the `language` column value. English is the fallback
for missing keys.

## Project structure

```
app/
  main.py                 entry point, polling, command menu
  config.py               environment settings (pydantic-settings)
  texts.py                localized rendering helpers
  i18n/
    __init__.py           translator and language registry
    locales/              en.py, ru.py, es.py, pt.py, ar.py
  db/
    models.py             SQLAlchemy models (settings, violations, stats)
    database.py           engine, table creation, additive migrations
    repository.py         CRUD operations
  services/
    jev.py                Jev Decisions API client and question set
    moderation.py         category/punishment selection (incl. "auto")
    actions.py            applying actions (delete/mute/ban/warn)
    fallback.py           rule-based engine used without Jev
    history.py            message context, flood, cross-chat spam
    telegram_utils.py     permission checks
  handlers/
    moderation.py         group message handling
    commands.py           slash commands
    settings_ui.py        inline settings menu
```

## Database

SQLite via `aiosqlite`. The default file is `./data/jev.db`; in Docker it is
mounted as `./data:/app/data`. To switch to PostgreSQL, set `DATABASE_URL` to
a `postgresql+asyncpg://…` value and add `asyncpg` to `requirements.txt`.

Additive SQLite migrations run on startup, so new columns are added to existing
databases automatically.

## Troubleshooting

**The bot does not react to messages.**

1. **Privacy mode.** In regular groups, a bot receives only commands, replies
   and mentions unless privacy mode is off. Disable it in BotFather
   (`/setprivacy` → bot → **Disable**) or make the bot an administrator. The
   bot logs every received message, so run `docker compose logs -f` and send a
   message: if nothing appears, privacy mode is the cause.
2. **Admins are ignored.** By default `Ignore admins` is on, so messages from
   administrators are skipped. Turn it off in `/settings` → ⚙️ Parameters, or
   test from a non-admin account.
3. **Missing rights.** The bot needs *Delete messages* and *Restrict members*.
   Check it in `/settings` → 🩺 Check bot rights.
4. **Moderation is off.** Verify that moderation is enabled in `/settings`.

**`/check` shows low probabilities.** Raise the model sensitivity by lowering
the threshold in `/settings` → ⚙️ Parameters, or use a category action other
than `off`.

## Security

- `.env` is git-ignored — never commit your keys.
- The bot stores only short message excerpts (up to 500 characters) and
  identifiers, used for statistics.
- Grant the bot the minimum rights it needs: delete messages and restrict
  members.
