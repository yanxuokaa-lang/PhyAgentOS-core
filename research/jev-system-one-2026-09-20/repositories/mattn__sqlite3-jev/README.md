# sqlite3-jev

SQLite extension that calls [TypeSafe Jev](https://docs.typesafe.ai/) — a
decision-only model that returns typed answers (yes/no probability, choice,
score) instead of text — straight from SQL.

Written in C, depends only on libcurl. Builds on Linux, macOS and Windows
(MinGW-w64).

## Usage

```sql
.load ./jev

-- API key comes from $TYPESAFE_API_KEY, or set it per connection:
SELECT jev_config('api_key', 'sk-...');

-- yes/no → probability 0..1
SELECT jev_noul('Help! My payouts have been failing for 3 days.',
                'Does this convey urgency?');
-- 0.92

-- pick one option → chosen option
SELECT jev_choice('Help! My payouts have been failing for 3 days.',
                  'Which team should handle this?',
                  '{"billing": "Payments, invoicing, refunds",
                    "technical": "Bugs, outages, integrations",
                    "sales": "Pricing, upgrades, new accounts"}');
-- 'technical'

-- rate on ordered levels → probability-weighted score
SELECT jev_score('Help! My payouts have been failing for 3 days.',
                 'How frustrated is the customer?',
                 '["Calm", "Frustrated", "Very angry"]');
-- 1.6

-- classify a whole table
SELECT id, jev_choice(body, 'Which team should handle this?',
                      '["billing", "technical", "sales"]') AS dept
FROM tickets;
```

### Functions

| Function | Returns |
|---|---|
| `jev_noul(state, instructions [, true_desc, false_desc])` | REAL, probability that the answer is yes |
| `jev_choice(state, instructions, criteria)` | TEXT, the chosen option |
| `jev_choice_json(state, instructions, criteria)` | JSON answer: `choice`, `probabilities`, `confidence` |
| `jev_score(state, instructions, levels)` | REAL, weighted score across `levels` |
| `jev_score_json(state, instructions, levels)` | JSON answer: `score`, `legend`, `probabilities`, `confidence` |
| `jev(state, questions)` | JSON `answers` object for several questions in one call |
| `jev_raw(state, questions)` | full response JSON (`model`, `answers`, `usage`) |
| `jev_config(name [, value])` | get/set `api_key`, `model`, `base_url`, `timeout` |

* `criteria` for `jev_choice` is either a JSON object `{"option": "description"}`
  (description may be `null`) or a JSON array of option names.
* `levels` for `jev_score` is a JSON array of at least two level descriptions,
  in order.
* `questions` for `jev` / `jev_raw` is the `questions` map from the
  [API reference](https://docs.typesafe.ai/api.md); all question types can be
  mixed and are evaluated in one request.
* `state` and `instructions` are sent as strings. To send structured JSON
  (chat logs, records, ...), pass a value produced by SQLite's JSON functions
  — `json_object(...)`, `json_array(...)`, `json('...')` — and it is embedded
  as-is:

  ```sql
  SELECT jev_noul(json_object('from', sender, 'text', body),
                  'Is this spam?')
  FROM mail;
  ```

* The `*_json` functions and `jev()` return JSON with SQLite's JSON subtype, so
  `->`/`->>` and `json_extract` chain naturally:

  ```sql
  SELECT jev_choice_json(body, 'Which team?', '["billing","technical"]') ->> '$.confidence'
  FROM tickets;
  ```

Errors from the API (401, 422, ...) are raised as SQL errors. `429` and `529`
are retried with exponential backoff (up to 3 times).

### Configuration

| `jev_config` name | Environment variable | Default |
|---|---|---|
| `api_key` | `TYPESAFE_API_KEY` | (none) |
| `model` | `JEV_MODEL` | `jev-latest` |
| `base_url` | `JEV_API_URL` | `https://api.typesafe.ai/v1/systemone` |
| `timeout` | `JEV_TIMEOUT` | `60` (seconds) |

Environment variables are read when the extension is loaded;
`jev_config(name, value)` overrides them for the current connection.
`jev_config('api_key')` only reports whether a key is set (`1`/`0`).

`base_url` accepts a bare host: `localhost:8080`, `http://host/` and
`host:port` all expand to `http://host:port/v1/systemone`; a URL with a path
is used as given. Without an API key no `Authorization` header is sent.

### Local models with tensai

[tensai](https://github.com/mattn/tensai) serves the same request and response
shape on `POST /v1/systemone`, answered by a local GGUF model, so the same SQL
runs against it with nothing but `base_url` changed:

```sh
tensai serve -q8 -model ~/.cache/tensai/gemma-3-1b-it-Q8_0.gguf   # 127.0.0.1:8080
```

```sql
SELECT jev_config('base_url', 'localhost:8080');
SELECT state, jev_choice(state, 'いま何を飲む？', '["コーヒー","ビール","紅茶"]')
FROM (SELECT '金曜の夜、友人と居酒屋' AS state);
-- ビール
```

`tensai serve -api-key ...` pairs with `jev_config('api_key', ...)` or
`$TYPESAFE_API_KEY`.

## Build

Requirements: C compiler, `sqlite3ext.h`, libcurl (`pkg-config` is used if
present).

```sh
make            # → jev.so / jev.dylib
make test       # runs test/run.py against a local mock server (python3)
make install    # → /usr/local/lib/sqlite3/
```

Debian/Ubuntu: `apt install libsqlite3-dev libcurl4-openssl-dev`
macOS: `brew install sqlite curl`

### Windows (MSYS2 / MinGW-w64)

```sh
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-sqlite3 mingw-w64-x86_64-curl
make                 # → jev.dll (dynamically linked to libcurl)
make CURL_STATIC=1   # link libcurl statically
```

Load it with `.load ./jev` in `sqlite3.exe`, or from any SQLite binding that
supports `load_extension`.

## License

MIT

## Author

Yasuhiro Matsumoto (a.k.a. mattn)
