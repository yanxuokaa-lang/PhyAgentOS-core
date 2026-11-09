# ibmi-jev

**AI judgments as SQL functions on IBM i.**

ibmi-jev wraps [TypeSafe's Jev](https://docs.typesafe.ai) model in schema `JEV`, so Db2 for i can
classify, score, and filter rows by meaning, in plain SQL. Batched, cached, and exposed to agents through MCP.
Jev is a judgment model: it returns calibrated probabilities, not generated text. No embeddings, no vector column.

```sql
-- yes/no probability as a column
SELECT MESSAGE_TEXT, JEV.NOUL(MESSAGE_TEXT, 'Does this report a failed backup?') AS P_FAILED
  FROM QSYS2.MESSAGE_QUEUE_INFO
 WHERE MESSAGE_QUEUE_NAME = 'QSYSOPR'
 FETCH FIRST 20 ROWS ONLY;

-- classify a table with a sentence
CALL JEV.SEARCH_TABLE('SAMPLE', 'EMPLOYEE', 'FIRSTNME, LASTNAME', 'the surname is Italian');
```

## Requirements

- IBM i 7.4 or later, with 5770SS1 options 3 and 34 (`QSYS2.HTTP_*` functions)
- Outbound HTTPS from the IBM i to `api.typesafe.ai`
- A TypeSafe API key ([console.typesafe.ai](https://console.typesafe.ai))

## Install

1. Run `install.sql` with any SQL runner:

   | Runner | How |
   |---|---|
   | Db2 for i VS Code extension, ACS Run SQL Scripts | Open `install.sql`, run all |
   | RUNSQLSTM | `RUNSQLSTM SRCSTMF('/path/install.sql') COMMIT(*NONE) NAMING(*SQL) ERRLVL(30)` |

2. Set the API key. Edit and run `sql/set_api_key.sql`:

   ```sql
   UPDATE JEV.CONFIG SET VALUE = 'your-key', CHANGED = CURRENT_TIMESTAMP WHERE NAME = 'API_KEY';
   ```

3. Verify: run `examples/00_verify.sql`. It prints the version, confirms the key, proves TLS
   (expect HTTP 403 without a key), and makes a first judgment.

Re-running `install.sql` is safe. To uninstal run `sql/uninstall.sql` which drops the schema.

Grant access to other users:

```sql
GRANT EXECUTE ON FUNCTION JEV.NOUL, JEV.CHOICE, JEV.SCORE, JEV.ASK, JEV.SEARCH, JEV.SEARCH_CACHED TO SOMEUSER;
GRANT EXECUTE ON PROCEDURE JEV.SEARCH_JUDGE, JEV.SEARCH_TABLE TO SOMEUSER;
```

Callers need no authority to `JEV.CONFIG`. The routines adopt the installer's authority to read the key.

## Reference

| Object | Signature | Returns |
|---|---|---|
| `JEV.NOUL` | `(text, question)` | `DECFLOAT` probability of yes |
| `JEV.CHOICE` | `(text, question, 'a, b, c')` | `VARCHAR` the chosen label |
| `JEV.SCORE` | `(text, question, 'low, mid, high')` | `DECFLOAT` expected level, 0 = first |
| `JEV.ASK` | `(state_json, questions_json)` | Table: `HTTP_STATUS, MODEL, ANSWERS, INPUT_TOKENS, OUTPUT_TOKENS, RESPONSE` |
| `JEV.SEARCH` | `(rows_json, condition [, batch_size])` | Table: `ROW_INDEX, PROBABILITY, FROM_CACHE`. Judges on demand, 40 rows per request, cached |
| `JEV.SEARCH_JUDGE` | `(rows_json, condition [, batch_size])` | Procedure. Fills `JEV.SEARCH_CACHE` |
| `JEV.SEARCH_CACHED` | `(rows_json, condition)` | Table: `ROW_INDEX, PROBABILITY, JUDGED_AT, MODEL`. Read-only, usable in views |
| `JEV.SEARCH_TABLE` | `(schema, table, 'COL1, COL2', condition [, threshold, max_rows])` | Result set: `PROBABILITY, FROM_CACHE` plus the table's columns |
| `JEV.VERSION` | `()` | SDK version |
| `JEV.CONFIG` | table | `API_URL`, `MODEL`, `API_KEY`, `SEARCH_MAX_ROWS` |
| `JEV.SEARCH_CACHE` | table | Judgments keyed by `HASH_MD5(condition)`, `HASH_MD5(row JSON)` |

`rows_json` is a JSON array of objects, one per row, built with `JSON_OBJECT` and `JSON_ARRAYAGG`.
`ROW_INDEX` is the 1-based position in that array. Materialize rows in a QTEMP table with `ROW_NUMBER()`
before searching so the array and the join back agree (see `examples/06_search.sql`).

### Basic usage

```sql
-- yes/no as a predicate
SELECT MESSAGE_ID, MESSAGE_TEXT
  FROM QSYS2.MESSAGE_QUEUE_INFO
 WHERE MESSAGE_QUEUE_NAME = 'QSYSOPR'
   AND JEV.NOUL(MESSAGE_TEXT, 'Does this message need an operator to act?') > 0.7;

-- one label per row, then count
SELECT TEAM, COUNT(*)
  FROM (SELECT JEV.CHOICE(BODY, 'Which team should handle this?', 'billing, technical, security, other') AS TEAM
          FROM TICKETS) t
 GROUP BY TEAM;

-- a level on an ordered scale
SELECT SUBJECT, JEV.SCORE(BODY, 'How soon does the sender expect action?', 'can wait, this week, today') AS URGENCY
  FROM TICKETS
 ORDER BY URGENCY DESC;

-- a whole table with a sentence: PROBABILITY first, then the table's columns
CALL JEV.SEARCH_TABLE('SAMPLE', 'EMPLOYEE', 'FIRSTNME, LASTNAME, JOB', 'the job is hands-on technical work', 0.6);

-- the same, composed with your own query
CREATE TABLE QTEMP.T AS (SELECT ROW_NUMBER() OVER () AS N, e.* FROM SAMPLE.EMPLOYEE e) WITH DATA;

SELECT s.PROBABILITY, t.LASTNAME, t.JOB, t.SALARY
  FROM QTEMP.T t
  JOIN TABLE(JEV.SEARCH(
          (SELECT JSON_ARRAYAGG(JSON_OBJECT('name' VALUE LASTNAME, 'job' VALUE JOB) FORMAT JSON ORDER BY N) FROM QTEMP.T),
          'the job is hands-on technical work')) s
    ON s.ROW_INDEX = t.N
 WHERE s.PROBABILITY >= 0.6 AND t.SALARY < 30000
 ORDER BY s.PROBABILITY DESC;
```

The [usage guide](USAGE_GUIDE.md) walks through each function, the search cache, and how to write
conditions and rubrics.

## Examples

Scripts in `examples/`, in the style of Scott Forstie's gists. Run statement by statement.

| Script | Shows |
|---|---|
| `00_verify.sql` | Version, config, TLS check, first judgment, first batched search |
| `01_first_judgments.sql` | Noul, Choice, Score in one raw `HTTP_POST`; probabilities, confidence, structured criteria |
| `02_functions.sql` | `NOUL`, `CHOICE`, `SCORE`, `ASK` on operator messages |
| `03_operator_messages.sql` | QSYSOPR triage: judge new messages once, `JEV.OPERATOR_INBOX` view |
| `04_active_sql.sql` | Active SQL statements classified once by hash, `JEV.ACTIVE_SQL` view |
| `05_job_logs.sql` | Job logs reconstructed from spooled files and judged: outcome, root cause, key message |
| `06_search.sql` | `SEARCH_TABLE` one-liners, `SEARCH` over the SQL error log, `SEARCH_JUDGE` plus a view on `SEARCH_CACHED` |
| `07_search_sample.sql` | `SAMPLE.EMPLOYEE`: ranking, conditions mixed with SQL, GROUP BY, resume text search |

Examples 03 to 05 create their own judgment tables and views in `JEV`.

## MCP server

`tools/jev.yaml` exposes the SDK to agents through the [IBM i MCP server](https://github.com/IBM/ibmi-mcp-server).
The server's IBM i profile needs `EXECUTE` on the `JEV` routines and read authority to the tables it searches.

| Toolset | Tools |
|---|---|
| `jev_search` | `jev_search_table`, `jev_search_rows`, `jev_search_sql_errors`, `jev_search_judge`, `jev_search_cached`, `jev_search_stats`, `jev_search_forget` |
| `jev_judge` | `jev_noul`, `jev_choice`, `jev_score`, `jev_ask`, `jev_status` |

```bash
cat > .env <<'EOF'
DB2i_HOST=your-ibmi-host
DB2i_USER=your-profile
DB2i_PASS=your-password
DB2i_PORT=8076
DB2i_IGNORE_UNAUTHORIZED=true
EOF

npx -y @ibm/ibmi-mcp-server@latest --transport http --tools ./tools/jev.yaml
# http://127.0.0.1:3010/mcp   (--toolsets jev_search to load only the search tools)

claude mcp add --transport http jev http://127.0.0.1:3010/mcp
```

Test a tool with the [`ibmi` CLI](https://www.npmjs.com/package/@ibm/ibmi-cli):

```bash
ibmi tool jev_status --tools tools/jev.yaml --system <name>
ibmi tool jev_search_table --tools tools/jev.yaml --system <name> \
  --schema SAMPLE --table EMPLOYEE --columns "FIRSTNME, LASTNAME" --condition "the surname is Italian"
```

Notes:

- `jev_search_table`, `jev_search_judge`, `jev_search_forget` are `CALL`/`DELETE` and carry `readOnly: false`.
  Every search writes the cache; every judgment is an HTTPS request that spends tokens.
- `jev_search_rows`, `jev_search_judge`, `jev_search_cached`, `jev_ask` pass JSON through the model's context.
  Use them for dozens of rows. `jev_search_table` and `jev_search_sql_errors` keep rows on the IBM i.

## How it works

- `JEV.ASK` posts to `https://api.typesafe.ai/v1/systemone` with `QSYS2.HTTP_POST_VERBOSE`, building the
  body with `JSON_OBJECT` and reading answers with `JSON_VALUE`.
- The key is a row in `JEV.CONFIG` (`*PUBLIC *EXCLUDE`). Routines are compound statements with
  `USRPRF = *OWNER`; Db2 inlines single-statement SQL functions and an inlined function does not adopt
  authority. The key never appears in statement text, which is durable on IBM i (plan cache, monitors).
- Every call is an HTTPS request (about 0.3 s per request, batches of 40 for search). Judge once into a
  table, keep thresholds in views, re-judge when the questions change.
- Db2 for i specifics that shaped the code: `JSON_VALUE` accepts a computed path; `JSON_TABLE ... FOR ORDINALITY`
  explodes arrays; `SIGNAL ... SET MESSAGE_TEXT` takes a variable or constant, not an expression;
  `SYSTOOLS.SPOOLED_FILE_DATA` is `MODIFIES SQL DATA`.

TLS uses the `*SYSTEM` certificate store. If it does not trust the chain for `api.typesafe.ai`, add the
CA in Digital Certificate Manager or set `sslCertificateStoreFile` in `JEV.ASK`.

## Agent skill

`.agents/skills/ibmi-jev/SKILL.md` teaches a coding agent this SDK: the functions, the search cache, the
Db2 for i rules behind the code, and links to the Jev docs. `.bob/skills/ibmi-jev` links to it. It pairs
with the official TypeSafe skill, which covers Jev itself:

```bash
claude plugin marketplace add typesafe-ai/skills && claude plugin install typesafe@typesafe-ai   # Claude Code
npx skills add typesafe-ai/skills --skill typesafe-ai                                            # other agents
```

## Development

```
install.sql        generated from sql/*.sql by scripts/build.sh
sql/               the SDK: 00_schema, 10_config, 20_ask, 30_search, 40_version, set_api_key, uninstall
examples/          runnable scripts
tools/jev.yaml     MCP server tools
.agents/skills/    agent skill (linked from .bob/skills/)
```

Syntax-check a statement without executing it:

```bash
ibmi validate "$(sed -n '/^CREATE OR REPLACE FUNCTION JEV.SEARCH /,/^END;/p' sql/30_search.sql | sed '$ s/;$//')" --system <name>
```

## Credits

`JEV.SEARCH` is a port of [pg-jev](https://github.com/realZachi/pg-jev) by Zachi ([@iam_zachi](https://x.com/iam_zachi)),
a Postgres extension that judges rows with plain-language conditions. Try the live demo at [pgjev.com](https://pgjev.com).

Examples 04 and 05 build on Scott Forstie's [Db2 for i gists](https://gist.github.com/forstie).

## License

[Apache 2.0](LICENSE).
