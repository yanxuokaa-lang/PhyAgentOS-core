# rspamd-jev

[日本語の導入ガイド](docs/README.ja.md)

A host-independent **shadow-evaluation plugin for Rspamd** using TypeSafe Jev. It works with plain Rspamd; Ollama, OpenAI, and Rspamd's `gpt` module are **optional comparison baselines**, not dependencies.

**Experimental: disabled by default, no external requests by default, no filtering decisions.** Jev observations have zero score and do not change delivery actions or set Bayes learning flags. This is an evaluation tool, not a production-ready replacement for existing spam filters. Live model quality and service availability still need evaluation with your own authorized data.

## Requirements

| Use | Requirements |
|---|---|
| Plugin | A working Rspamd installation with its bundled Lua runtime/modules, administrative access to its local configuration, and readable logs |
| Compatibility | Native CI covers Ubuntu 24.04's Rspamd 3.8.1. This is the oldest tested version, not a recommendation to run an outdated release. Validate your supported distribution/version before deployment |
| Live Jev | TypeSafe account/API access, an API key, an available pinned model version, DNS and outbound HTTPS to `api.typesafe.ai:443`, trusted CA certificates |
| Data approval | Permission to send the selected mail content externally; an explicit allowlist of SMTP recipient domains; review of retention, processing location, and contractual requirements |
| Local mock and reports | Python 3.10+; standard library only |
| Developer tests | Python 3.10+, `make`, and LuaJIT or Lua; native smoke tests additionally need Linux/Unix, `rspamd`, and `rspamadm` |
| Optional GPT comparison | A working Rspamd `gpt` module exposing `GPT_CHECK` and `GPT_SPAM` / `GPT_HAM` / `GPT_UNCERTAIN`; support depends on the installed Rspamd version/provider |

Python and a separate Lua interpreter are **not required to run the plugin itself**. No GPU, NPU, MLX, OpenVINO, Redis, or local inference runtime is required. Jev inference runs at TypeSafe, not on the mail server. If API access is waitlisted, complete the mock setup first.

This project does not install Rspamd, configure an MTA, or set up Ollama. Ensure your existing filtering pipeline works before adding it.

## How it works

```text
Existing Rspamd checks (+ optional GPT provider)
  -> JEV_CHECK: select eligible messages, sample, query Jev asynchronously
  -> JEV_LOG: record Jev, the final Rspamd action/score, and any GPT verdict
```

- Default `require_gpt = false`: no GPT dependency or GPT-based selection. Evaluate eligible mail even without a GPT result. If GPT runs, its verdict is collected at the final logging stage.
- Optional `require_gpt = true`: wait for `GPT_CHECK`, then only evaluate messages with an observed GPT verdict. This preserves the original paired-comparison workflow.
- Neither GPT verdicts nor the overall Rspamd score are sent to Jev. Authentication-check symbols are included as evidence.
- `JEV_HAM`, `JEV_SPAM`, `JEV_PHISHING`, `JEV_UNCERTAIN`, and `JEV_ERROR` have registration scores and insertion weights of zero. Do not add them to action rules, composites, or learning conditions.

Asynchronous HTTP avoids blocking a worker's event loop, but the **individual mail scan still waits for Jev**. Budget for the extra latency.

## Installation

### 1. Obtain the source and inspect your deployment

```sh
git clone https://github.com/rioriost/rspamd-jev.git
cd rspamd-jev
rspamd --version
sudo rspamadm configtest
sudo rspamadm configdump modules
```

Back up your local Rspamd configuration outside the repository. Check the actual configuration directory, service user/group, reload mechanism, worker count, and MTA/Rspamd timeout budgets. Examples below use `/etc/rspamd`; installations using `/usr/local/etc/rspamd` or other paths must substitute their own directory.

The recommended loading mechanism is `modules.try_path` pointing to the local `plugins.d` directory. Do not replace the existing module paths. See **Custom loaders and containers** below if your installation differs.

### 2. Install the files, initially disabled

Run on the Rspamd host, from the checkout. These commands are for a **first installation**; if either file already exists, stop and use the update procedure.

```sh
CONFDIR=/etc/rspamd
sudo test ! -e "$CONFDIR/plugins.d/jev.lua" &&
sudo test ! -e "$CONFDIR/local.d/jev.conf" &&
sudo install -d -m 0755 "$CONFDIR/plugins.d" "$CONFDIR/local.d" &&
sudo install -m 0644 rspamd/jev.lua "$CONFDIR/plugins.d/jev.lua" &&
sudo install -m 0644 rspamd/jev.conf "$CONFDIR/local.d/jev.conf"
```

Append this block **once** to your existing `rspamd.conf.local`. Do not replace that file, edit package-managed defaults, or include the new plugin twice:

```ucl
jev {
  .include "$LOCAL_CONFDIR/local.d/jev.conf"
}
```

`$LOCAL_CONFDIR` above is a Rspamd configuration variable, not a shell variable. The supplied `jev.conf` contains the **inside** of this block; do not wrap it in another `jev {}` block.

The sample configuration has `enabled = false`. Validate before reloading:

```sh
sudo rspamadm configtest
# Only after a successful check; adapt to your service manager:
sudo systemctl reload rspamd
```

If reload is unsupported, schedule a restart. A valid configuration alone does not prove the plugin was loaded; confirm its symbols/logs in the next step.

### 3. Exercise the mock without an API key

Start the mock in the **same network namespace as Rspamd**, in a separate terminal:

```sh
python3 tools/mock_jev.py --outcome phishing
curl --fail http://127.0.0.1:18080/health
```

Edit the existing values in `local.d/jev.conf` (do not append duplicate keys):

```ucl
enabled = true;
mode = "mock";
url = "http://127.0.0.1:18080/v1/systemone";
allow_external = false;
require_gpt = false;
sample_rate = 1.0;
```

After `configtest` and reload, scan a **synthetic** message through your local scanner. The command below assumes the normal worker listens on `127.0.0.1:11333`; adapt it to your deployment, not the MTA's milter port.

```sh
printf 'From: sender@example.test\nTo: recipient@example.test\nSubject: Synthetic Jev test\nMIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\nThis is synthetic mail for plugin verification.\n' |
  rspamc -h 127.0.0.1:11333
```

Expect `JEV_PHISHING` with score 0 and a `JEV_EVAL` log record containing `"mode":"mock"`. Compare the delivery action/score with the plugin disabled. If existing settings skip this scan, use a dedicated test instance (`make smoke`) instead of weakening production policies. Your MTA/worker must supply SMTP recipients for **live** evaluation; the simple mock scan above does not exercise that gate.

The mock returns the selected outcome regardless of content. It also supports `ham`, `spam`, `uncertain`, `429`, `500`, `529`, and `malformed`; `--delay 3` exercises timeouts. It listens only on loopback and rejects real API keys. Its outputs are **not accuracy measurements**.

Set `enabled = false` and reload when finished, then stop the mock with Ctrl-C. While waiting for API access, leave the plugin disabled.

### 4. Activate live evaluation

Approve the data flow first. Jev receives potentially sensitive message content; there is **no automatic anonymization**. Customer-data training exclusion is not the same as zero retention. Check [TypeSafe's data policies](https://docs.typesafe.ai/legal), model access, and account quotas.

Store the API key in a file outside the repository. Use your actual Rspamd user/group; `_rspamd` is only an example:

```sh
CONFDIR=/etc/rspamd
RSPAMD_USER=_rspamd
RSPAMD_GROUP=_rspamd
KEY_FILE="$CONFDIR/jev-api-key"
# Creates a protected empty file only if it does not already exist:
sudo test ! -e "$KEY_FILE" &&
sudo install -o root -g "$RSPAMD_GROUP" -m 0640 /dev/null "$KEY_FILE"
sudoedit "$KEY_FILE"
sudo chown root:"$RSPAMD_GROUP" "$KEY_FILE"
sudo chmod 0640 "$KEY_FILE"
sudo -u "$RSPAMD_USER" test -r "$KEY_FILE"
```

Enter just the key on one line, without `Bearer`, quotes, or variable assignments. Do not put keys in command arguments, shell history, Git, or issue reports. Rootless containers should use equivalent ownership for their runtime UID and a read-only secret mount.

Edit `local.d/jev.conf`:

```ucl
enabled = true;
mode = "live";
url = "https://api.typesafe.ai/v1/systemone";
model = "jev-1.13.0";
allow_external = true;
api_key_file = "/etc/rspamd/jev-api-key";
recipient_domains = ["evaluation.example.com"];
require_gpt = false;
sample_rate = 0.05;
```

Replace the key path and recipient domain with values approved for **your** installation. All SMTP recipients must match the allowlist exactly. Unknown recipients, unapproved co-recipients, and authenticated submissions are skipped. No implicit subdomain matching or wildcards are supported.

Verify that the pinned model is available to your account. `jev-latest` and other moving aliases are rejected. The live endpoint is restricted to the official HTTPS URL and TLS verification stays enabled.

Run `configtest`, check key-file readability, reload, and inspect initial `JEV_EVAL` records and error logs. Keys are read at configuration load; rotation also requires a reload.

## Optional comparison with Ollama or another GPT provider

First configure and validate Rspamd's [`gpt` module](https://docs.rspamd.com/modules/gpt/) separately. The plugin works with either provider's standard GPT symbols; there is no Ollama host or model hardcoded here.

```sh
# Inspect locally: configuration dumps can contain credentials; do not publish them.
sudo rspamadm configdump gpt
```

Set `require_gpt = true` only if you want **GPT-selected paired evaluation**. Jev will depend on `GPT_CHECK` and skip messages without a GPT verdict (`no_gpt_result`). Merely setting this option does not install or enable GPT. Older Rspamd versions without that module can still use standalone Jev.

Keep `require_gpt = false` if you want independent Jev sampling; GPT observations, when present, are still collected after all postfilters finish. A missing GPT result is `not_observed`, never an assumed ham verdict. Existing GPT settings, models, scores, and autolearning are not changed.

These are comparisons on the same messages, not necessarily identical prompts/input extraction. GPT's own selection rules and any existing autolearning affect the experiment.

## Configuration reference

All options live inside the `jev` configuration section. See [`rspamd/jev.conf`](rspamd/jev.conf).

| Option | Default | Meaning |
|---|---|---|
| `enabled` | `false` | Enable the plugin |
| `mode` | `"mock"` | `mock` or `live`; changing mode also requires the matching URL |
| `url` | loopback port 18080 | Mock permits only `http://127.0.0.1:PORT/v1/systemone`; live requires the official URL |
| `model` | `"jev-1.13.0"` | Pinned three-component model version |
| `allow_external` | `false` | Explicit live-data approval gate |
| `api_key_file` | `""` | Absolute readable key-file path; required in live mode |
| `recipient_domains` | `[]` | Exact SMTP domain allowlist; nonempty in live mode; enforced in mock too if supplied |
| `require_gpt` | `false` | Require a prior GPT verdict; otherwise GPT is optional |
| `sample_rate` | `0.05` | Deterministic digest-based sampling, 0..1 |
| `timeout` | `1.5` | HTTP timeout in seconds; no retries |
| `requests_per_second` | `1` | Per-worker request start rate |
| `max_inflight` | `2` | Per-worker outstanding-request limit |
| `cooldown` | `60` | Per-worker pause in seconds after an error |
| `max_message_bytes` | `1048576` | Skip larger messages |
| `max_body_bytes` | `6000` | Combined UTF-8 body byte budget, not characters |
| `max_request_bytes` | `24576` | Skip requests whose serialized JSON exceeds this limit |
| `max_urls` / `max_attachments` | `16` / `8` | Evidence item limits |
| `probability_threshold` / `confidence_threshold` | `0.9` / `0.9` | Both must be met to emit a category rather than `uncertain`; never change scores |

Limits and cooldowns are **per worker**, not shared across hosts/processes. Budget `worker count × requests_per_second` plus other account usage against your quota, with headroom. There is no queue, retry, Redis rate limiter, or response cache. Repeated scans can make additional paid requests.

## Logs and reports

`JEV_LOG` writes `JEV_EVAL { ... }` to your existing Rspamd log. It records the message digest, mode/model/prompt, selection settings, probabilities, latency, token use, errors/skips, optional GPT baseline, and final Rspamd score/action. Tasks skipped by Rspamd itself may produce no Jev record.

The plugin's JSON record excludes bodies, subjects, addresses, URLs, keys, and raw upstream error bodies. Existing Rspamd log prefixes/other lines can still contain mail metadata. Protect logs and labels; digests can be linked to mail.

```sh
python3 tools/summarize.py /path/to/rspamd.log --mode mock
python3 tools/summarize.py /path/to/rspamd.log --mode live
journalctl -u rspamd -o cat | python3 tools/summarize.py - --mode live
python3 tools/summarize.py /path/to/rspamd.log --labels /private/path/labels.csv
```

Labels must be independently human-verified, not copied from another classifier. CSV header: `message_digest,label`; labels: `ham`, `spam`, `phishing`. Actual mail, CSVs, keys, and evaluation logs must stay outside Git.

| Report | Interpretation |
|---|---|
| `statuses`, `skip_error_reasons` | Success, failure, and exclusion counts |
| `agreement`, `baseline_vs_jev` | Jev vs optional GPT predictions; agreement is **not** accuracy |
| `http_latency_ms` | Jev HTTP p50/p95/p99, not GPT or total mail-scan time |
| `estimated_success_cost_usd` | Successful-response input-token estimate, not a verified bill; adjust `--price-per-million` |
| `paired_labeled_*` | Jev vs GPT on the same labeled, comparable subset |
| `pipeline_paired_labeled_rspamd`, `pipeline_paired_labeled_jev` | Existing Rspamd pipeline vs Jev, including deployments without GPT |
| `current_pipeline_actions` | Existing pipeline's final actions |

Binary metrics combine spam and phishing. Uncertain/unobserved/conflicting predictions are excluded from the corresponding paired metrics, with coverage reported separately. Pipeline actions map `no action` to ham and `reject` / `add header` / `rewrite subject` / `quarantine` / `discard` to spam; deferrals such as `greylist` and `soft reject` are unresolved. Check that this interpretation matches your site's policy.

Quality metrics use the latest successful result per digest; latency/cost include all requests with relevant observations. Mixed models, prompts, thresholds, sampling/selection policies, or GPT configurations are rejected: split logs by experiment. No labels means no claim of measured accuracy. Prioritize ham false positives, missed-spam reduction, and abstention coverage, not aggregate accuracy alone.

### Migration from the initial comparison-only defaults

- The default `require_gpt` changed from `true` to `false`. Existing configurations explicitly setting `true` keep the old behavior. Set it explicitly before updating if you relied on the implicit old default; the new default can broaden the set sent to Jev.
- Do not overwrite your `jev.conf` with the new sample. The sample no longer assumes a key-file location.
- Records now include `require_gpt`. Older schema-1 logs remain readable on their own, but must not be mixed with newly recorded selection policies.
- Use `pipeline_paired_labeled_rspamd` in new consumers. `pipeline_paired_labeled_rspamd_ollama` remains an identical deprecated alias for existing report consumers; it does not imply Ollama was used.

## Custom loaders and containers

Paths are examples, not host identities. For custom layouts, use the directory represented by your deployment's `$LOCAL_CONFDIR`. If your installation does not load `plugins.d` via `modules.try_path`, use its documented custom Lua loader: place `jev.lua` outside auto-loaded directories and add a single `dofile('/absolute/path/to/jev.lua')` to the existing `rspamd.local.lua`. The `jev` configuration block is still required. Do not use both loaders.

For containers, persist or bind-mount the plugin and local configuration rather than editing an ephemeral container. Mount secrets read-only, verify the runtime UID can read them, and validate/reload **inside** the container. In mock mode, loopback refers to that container's network namespace. Run the mock in the same namespace (or use the isolated smoke test); a separate host or ordinary sidecar has different loopback. Do not expose the mock on a public interface or disable live TLS checks.

## Updating, disabling, and removing

1. Back up your installed plugin and local configuration. Review the diff and migration notes; use a reviewed commit from the repository.
2. Update **only** the plugin file, merging any desired configuration changes manually. Never overwrite a live configuration or key with sample files.
3. Run `configtest`, reload, and verify a synthetic scan plus log output. If validation fails, restore the backed-up plugin/configuration before reloading. No schema/data migration is needed.

To disable, set `enabled = false`, validate, and reload. To remove, first disable, then remove only the added `jev` include/optional `dofile` and the dedicated plugin/config/key files. Do not remove the entire local configuration file or change other classifiers.

## Limits and testing

The evidence contains subject, From/Reply-To, up to four non-attachment text parts (HTML tags removed), URLs/visible text/hosts, attachment names/types, and selected authentication symbols. It excludes attachment contents and recipient lists. URLs are not fetched. Body/URL fields can contain secrets or personal data; no automatic redaction is performed. UTF-8 truncation is recorded but is not an exact token-budget calculation.

There is no image/OCR analysis, shared cache/rate limiter, automatic enforcement, or learning from Jev. Confidence is not a false-positive-rate guarantee, and instructions to ignore malicious content are not a prompt-injection defense guarantee. Empty/partial evidence, language differences, unavailable subscription history, and dataset selection all require local evaluation.

```sh
make test                 # LuaJIT + Python tests
make test LUA=lua         # Alternative standalone Lua
make smoke               # Linux: isolated real Rspamd, no existing service changes
```

Native tests install into a temporary custom configuration directory using the shipped sample and `modules.try_path`. They cover disabled defaults, standalone operation, explicit GPT selection, late optional GPT observations, and HTTP error/timeout handling with synthetic mail. GPT results are simulated; neither a real GPT service nor a TypeSafe account is used. CI coverage does not establish live-model accuracy or compatibility with every deployment.

## Licensing and references

This project is licensed under the [MIT License](LICENSE).
Copyright (c) 2026 Rio Fujita.

- [TypeSafe API](https://docs.typesafe.ai/api), [models and limits](https://docs.typesafe.ai/models), [known model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- [Rspamd GPT module](https://docs.rspamd.com/modules/gpt/), [Lua HTTP API](https://docs.rspamd.com/lua/rspamd_http/)
