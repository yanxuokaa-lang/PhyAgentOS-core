# jev — natural-language `WHERE` clauses for DuckDB

`jev` lets you filter, rank and classify rows with plain English. Every row is judged by
[TypeSafe's Jev](https://docs.typesafe.ai), a System One model that returns calibrated
probabilities instead of generated text. No index, no embeddings, no vector column.

```sql
INSTALL jev FROM community;
LOAD jev;
SET jev_api_key = 'your-key';   -- or export TYPESAFE_API_KEY

SELECT * FROM people p WHERE jev(p, 'the name is European');
SELECT subject, jev_prob(t, 'the customer is angry') AS p FROM tickets t ORDER BY p DESC LIMIT 20;
SELECT jev_choice(t, 'which team should handle this?', ['billing', 'technical', 'security']) AS team, count(*)
FROM tickets t GROUP BY 1;
```

`jev()` is an ordinary boolean scalar, so it composes with `AND`, joins, `GROUP BY` and
`ORDER BY jev_prob(...)`.

Inspired by [pg-jev](https://github.com/realZachi/pg-jev) for PostgreSQL — see [Credits](#credits).

## Install

**From the community repository** (once the extension is listed there — see Status):

```sql
INSTALL jev FROM community;
LOAD jev;
```

**Until then, load a build directly.** Every push builds binaries for Linux, macOS and
Windows in the [Actions](https://github.com/recodelabs/duckdb-jev/actions) tab (artifact
`jev-…-<platform>` inside the "Build extension binaries" run), or build it yourself:

```bash
git clone --recurse-submodules https://github.com/recodelabs/duckdb-jev.git && cd duckdb-jev
GEN=ninja make release          # needs cmake, ninja and OpenSSL (vcpkg or brew/apt); compiles DuckDB too
# -> build/release/extension/jev/jev.duckdb_extension
```

A locally built or downloaded extension is unsigned, so start DuckDB with unsigned
extensions allowed and `LOAD` it by path:

```bash
duckdb -unsigned
```
```sql
LOAD '/path/to/jev.duckdb_extension';
```
```python
import duckdb
con = duckdb.connect(config={"allow_unsigned_extensions": "true"})
con.execute("LOAD '/path/to/jev.duckdb_extension'")
```

The extension is built against DuckDB **1.5.5**; use the matching DuckDB version.

## Usage

Get an API key from https://console.typesafe.ai and give it to the session:

```sql
SET jev_api_key = 'your-key';           -- or: export TYPESAFE_API_KEY=your-key before starting DuckDB
```

Then ask questions about rows. `rec` is the table alias, so every column is visible to the model:

```sql
CREATE TABLE cities AS SELECT * FROM (VALUES
  ('Nairobi','Kenya'), ('Mombasa','Kenya'), ('Abuja','Nigeria'), ('Lagos','Nigeria'),
  ('Canberra','Australia'), ('Sydney','Australia'), ('Bern','Switzerland'), ('Zurich','Switzerland')
) t(city, country);

-- filter
SELECT city FROM cities c WHERE jev(c, 'the city is the capital of the country');
-- Nairobi
-- Abuja
-- Canberra
-- Bern

-- rank by probability, then pick your own threshold
SELECT city, round(jev_prob(c, 'the city is the capital of the country'), 2) AS p
FROM cities c ORDER BY p DESC;
-- Nairobi  0.98
-- Abuja    0.98
-- Canberra 0.98
-- Bern     0.91
-- Lagos    0.07
-- Zurich   0.06
-- Sydney   0.05
-- Mombasa  0.04

SELECT city FROM cities c WHERE jev(c, 'the city is the capital of the country', 0.95);  -- stricter
-- Nairobi
-- Abuja
-- Canberra

-- classify
SELECT city, jev_choice(c, 'which continent is this city on?', ['africa', 'europe', 'asia', 'oceania'])
FROM cities c;
-- Nairobi  africa
-- Mombasa  africa
-- Abuja    africa
-- Lagos    africa
-- Canberra oceania
-- Sydney   oceania
-- Bern     europe
-- Zurich   europe

-- grade on an ordered scale (0 = first level … n-1 = last level)
SELECT city, jev_score(c, 'how large is the city population?', ['under 500k', '500k-2M', '2M-10M', 'over 10M'])
FROM cities c ORDER BY 2 DESC;
-- Lagos    2.69
-- Sydney   1.96
-- Nairobi  1.79
-- Abuja    1.19
-- Mombasa  1.16
-- Zurich   0.52
-- Canberra 0.11
-- Bern     0.11

-- the raw answer, including per-option probabilities and confidence
SELECT jev_eval(c, 'which continent is this city on?', 'choice', ['africa', 'europe']) FROM cities c LIMIT 1;
-- {"type":"choice","choice":"africa","confidence":1.0,"probabilities":{"africa":1.0,"europe":0.0}}

-- what did that cost?
SELECT jev_stats();
-- {"requests":4,"retries":0,"batches":4,"rows_evaluated":25,"cache_hits":16,
--  "input_tokens":3093,"output_tokens":670,"estimated_cost_usd":0.000129906,
--  "api_ms":2120,"errors":0,"cache_entries":25}
```

Probabilities depend on the whole table sent in each request (the rows are the model's
context), so the same city can score differently in a different table.

Only the columns you select are sent, so a subquery or view narrows what the model sees:

```sql
SELECT s.city FROM (SELECT city, country FROM cities) s WHERE jev(s, 'the city is coastal');
```

Answers are cached per row content for the life of the database instance, so re-running
a query, changing the threshold or sorting by `jev_prob()` costs nothing extra. The cache
has no size limit and no expiry — a long-lived session judging millions of distinct rows
will keep them all until `jev_cache_clear()`. Each API request prints one line to stderr
(rows, tokens, estimated cost, time); those lines come from several DuckDB threads, so
they can arrive interleaved. Turn them off with `SET jev_notices = false`.

Tips for conditions: state the exact condition (`'the customer threatens to leave or
dispute a charge'` beats `'churn risk'`), keep arithmetic and exact matches in SQL, and
look at the `jev_prob()` distribution before choosing a threshold — ambiguous rows really
do land near 0.5.

## Functions

| Function | Returns | Notes |
|---|---|---|
| `jev(rec, condition)` | BOOLEAN | `jev_prob(...) >= jev_threshold` |
| `jev(rec, condition, threshold)` | BOOLEAN | `jev_prob(...) >= coalesce(threshold, jev_threshold)` |
| `jev_prob(rec, condition)` | DOUBLE | P(row satisfies condition), 0..1 |
| `jev_score(rec, question, levels)` | DOUBLE | probability-weighted level index, 0..n-1 |
| `jev_score_norm(rec, question, levels)` | DOUBLE | the same, rescaled to 0..1 |
| `jev_choice(rec, question, options)` | VARCHAR | most likely option |
| `jev_confidence(rec, question, kind, options)` | DOUBLE | confidence of a score or choice answer |
| `jev_eval(rec, question, kind, options)` | JSON | the raw answer object |
| `jev_stats()` | JSON | requests, retries, tokens, estimated cost, cache hits (per database instance) |
| `jev_cache_clear()` | BOOLEAN | forget cached judgments |
| `jev_version()` | VARCHAR | extension version |
| `jev_set_api_key(v)`, `jev_set_api_url(v)`, `jev_set_model(v)` | VARCHAR | for clients that cannot issue `SET` |

`rec` is any struct: a table alias (`jev(p, ...)`), a subquery alias, or
`struct_pack(...)`. `kind` is `'noul'`, `'score'` or `'choice'`; `options` is the list of
levels or choices and may be `NULL` for `'noul'`.

`jev` builds on DuckDB's `json` extension (autoloaded) to turn a row into the JSON
document the API sees.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `jev_api_key` | env `TYPESAFE_API_KEY` | TypeSafe API key |
| `jev_api_url` | `https://api.typesafe.ai/v1/systemone` | endpoint (proxies, mocks) |
| `jev_model` | `jev-latest` | model name |
| `jev_threshold` | `0.5` | probability at which `jev()` is true |
| `jev_batch_size` | `40` | rows per API request (must be >= 1) |
| `jev_concurrency` | `6` | parallel requests per vector, capped at 64 |
| `jev_timeout` | `90` | seconds per request |
| `jev_notices` | `true` | print one line per API request to stderr |

## How it works

DuckDB hands the extension up to 2048 rows at a time. Rows that share a question, a kind
and a set of options are grouped, identical rows are judged once, and whatever is not
already cached is split into `jev_batch_size` batches that run on up to `jev_concurrency`
threads. Answers and usage counters live in a database-scoped cache that every connection
of that database shares; `jev_cache_clear()` empties it.

`jev_concurrency` is per DuckDB thread, not per query: DuckDB may evaluate the function on
several threads at once, so the requests in flight can reach DuckDB threads x
`jev_concurrency` (capped at 64 per thread). The default batch of 40 rows carries 40
questions in one request, which the live API answers in well under a second.

Requests retry 429, 529, 5xx and transport errors with exponential backoff (0.5 s doubling
to 8 s, six attempts); a `Retry-After` header on a 429 or 503 wins over that schedule, up
to 30 s. Any other status raises `jev: TypeSafe API error <code> <body>`.

See [docs/DESIGN.md](docs/DESIGN.md) for the full design.

## Building and testing

```bash
GEN=ninja make release      # first build compiles DuckDB itself
./test/run.sh               # starts test/mock_api.py, runs make test, stops it again
```

The SQL tests never touch the real API: `test/mock_api.py` is a deterministic stand-in on
`127.0.0.1:8765`. They only run when `JEV_MOCK_RUNNING=1` is exported (`test/run.sh` does
it), so a bare `make test` on a machine without the mock skips them instead of failing.

## Status

Version 0.1.0. Builds and tests are green on Linux, macOS and Windows; submission to the
[DuckDB community extension repository](https://github.com/duckdb/community-extensions)
is pending, so for now install from a build (see [Install](#install)).

## Credits

duckdb-jev was inspired by [pg-jev](https://github.com/realZachi/pg-jev), Zachi's
natural-language `WHERE` clauses for PostgreSQL, which showed how well a calibrated
yes/no model fits inside a SQL predicate. This is an independent implementation of that
idea for DuckDB; the two share no code. Row judgments come from
[TypeSafe's Jev](https://docs.typesafe.ai).
