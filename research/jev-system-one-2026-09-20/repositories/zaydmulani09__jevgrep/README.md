# jevgrep

```bash
pip install git+https://github.com/zaydmulani09/jevgrep
```

**Semantic code search that feels like grep.** Ask in plain English —
`"where's the auth check before writing to the db"` — and get back ranked
`file:line` matches by *meaning*, not exact text. One network call, no
loading spinner.

```
$ jevgrep "auth check before writing to the db"
api/handlers.py:88    91.2%  if not user.is_authenticated: raise Forbidden()
db/write.py:41        74.5%  def persist(record): _guard(); session.add(record)
api/handlers.py:92    31.0%  session.commit()
-- 3 results | candidates via ripgrep | 240 ms
```

## Why it's fast

Naive semantic search embeds or LLM-scores the *whole repo* on every query —
slow and expensive. jevgrep uses two stages:

1. **Local candidate pass (instant).** [ripgrep](https://github.com/BurntSushi/ripgrep)
   scans the repo for your query's keywords and shortlists the ~30 strongest
   lines. This throws away 99% of the repo before any network call. If ripgrep
   isn't installed, a built-in pure-Python scanner does the same job (slower on
   huge repos, zero dependencies).
2. **One semantic re-rank.** The shortlist goes to
   [TypeSafe's **Jev**](https://openrouter.ai/typesafe/jev-1.13) model via
   [OpenRouter's Decisions API](https://openrouter.ai/typesafe) in a **single
   batched call** — each candidate is one option of a `choice` question scored
   against your query. Jev is a "System One" classifier (fast, typed,
   calibrated), *not* a chat LLM, so it isn't called through `/chat/completions`
   — it has its own `/decisions` endpoint. The returned per-option
   probabilities are your ranking.

**Why this split:** keyword matching is great at recall, terrible at intent
("auth" ≠ the *auth check before a write*). A full-repo embedding index would
give better recall but costs an index build + storage + staleness on every edit.
Ripgrep needs no index and is always current, and Jev supplies the intent
ranking the keyword pass can't — you get semantic quality at grep latency
without maintaining an index.

## Install

```bash
pip install -e .        # from a clone
# or, once published:
pip install jevgrep
```

Requires Python 3.9+. [ripgrep](https://github.com/BurntSushi/ripgrep) is
recommended (`brew install ripgrep`, `winget install BurntSushi.ripgrep.MSVC`,
`apt install ripgrep`) but optional.

## Configure

jevgrep needs a single OpenRouter API key. Copy the template:

```bash
cp .env.example .env
```

and fill in:

```
OPENROUTER_API_KEY=...
```

`.env` is auto-loaded from the repo you search or the current directory. Real
environment variables override it. `.env` is gitignored — don't commit it.

### Getting the key (if you don't have one yet)

1. Sign up at <https://openrouter.ai> — no credit card required, and new
   accounts get a small amount of **free credit**.
2. Go to **<https://openrouter.ai/keys>** → **Create Key** → copy it once.
3. Paste it into `.env` as `OPENROUTER_API_KEY`.

Jev 1.13 is cheap (~$0.042 per million input tokens, output free), so a query's
tiny shortlist costs a fraction of a cent — the free credit covers plenty.

## Usage

```bash
jevgrep "natural language query"                 # search current dir
jevgrep "retry logic for failed uploads" -p ../app   # search another repo
jevgrep "rate limit middleware" -n 20            # show more results
jevgrep "where do we validate the JWT" -c 40     # bigger shortlist (<=50)
jevgrep "parse the config file" --json           # machine-readable
jevgrep "auth check" --dry-run                   # local shortlist only, no API call, no key
```

| Flag | Meaning |
|------|---------|
| `-p, --path DIR` | repo root to search (default: cwd) |
| `-n, --limit N` | results to display (default: 10) |
| `-c, --candidates N` | shortlist size sent to Jev (default: 30, keep ≤50) |
| `--dry-run` | show the local candidate shortlist and stop — no key needed |
| `--json` | emit JSON `[{path, line, score, text}]` |
| `--model ID` | override the model id (default `typesafe/jev-1.13`) |
| `--no-color` | disable ANSI color |

`--dry-run` is the fast way to sanity-check the candidate pass (and works with
no OpenRouter key at all).

## How the Jev call is shaped

Jev is a decision model, not a chat model, so it uses OpenRouter's **Decisions**
endpoint (not `/chat/completions`). One `choice` question, each shortlist line
an option; `state` and `questions` are top-level:

```jsonc
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer $OPENROUTER_API_KEY
{
  "model": "typesafe/jev-1.13",
  "state": "Code search query: auth check before writing to the db",
  "questions": {
    "match": {
      "type": "choice",
      "instructions": "Select the candidate whose code best matches the query...",
      "criteria": {
        "c0": "api/handlers.py:88: if not user.is_authenticated: ...",
        "c1": "db/write.py:41: def persist(record): ...",
        "...": "..."
      }
    }
  }
}
```

Jev returns `answers.match.probabilities` (`{c0: 0.91, c1: 0.74, ...}`); jevgrep
maps those back to `file:line` and sorts. Jev's 32k-token context is why the
shortlist is capped at ~50 short candidates.

## Why this beats grep (real demo)

Run against a real [Flask](https://github.com/pallets/flask) checkout — a repo
that actually loads env vars and parses config files.

### Query: `"where do we load environment variables"`

**jevgrep** — the real env-loading code, ranked by intent:

```
flask/cli.py:701    27.0%  """Load "dotenv" files to set environment variables. A given path takes
flask/cli.py:559    15.0%  If installed, python-dotenv will be used to load environment variables
flask/config.py:129 12.0%  """Load any environment variables that start with ``FLASK_``,   ← from_prefixed_env
flask/cli.py:521    11.0%  "Load environment variables from this file, taking precedence over"
```

**plain grep, same goal:**

```
$ rg -i "load environment variables"     # grep the query words
flask/cli.py:521:  "Load environment variables from this file, taking precedence over"
flask/cli.py:559:  If installed, python-dotenv will be used to load environment variables
# 2 hits, both docstrings — misses the mechanism entirely

$ rg "os\.environ"                        # grep the real symbol (you had to know it)
# 14 hits across app.py, helpers.py, config.py, cli.py — NO ranking, eyeball them all
```

### Query: `"where do we parse the config file"`

**jevgrep** — pulls the actual parse line to the top, all in `config.py`:

```
flask/config.py:209  68.0%  exec(compile(config_file.read(), filename, "exec"), d.__dict__)   ← from_pyfile
flask/config.py:270   5.0%  app.config.from_file("config.json", load=json.load)
flask/config.py:273   3.0%  app.config.from_file("config.toml", load=tomllib.load, text=False)
```

**plain grep:**

```
$ rg "parse config file"
# 0 hits — those words never co-occur in the code
```

The `#1` result (`config.py:209`) contains none of the query words — no "parse",
no "config file". grep can't reach it. jevgrep ranks it first because that's the
line that *actually reads and executes the config file*. That's text match losing
to meaning.

## License

MIT © Zayd Mulani. See [LICENSE](LICENSE).
