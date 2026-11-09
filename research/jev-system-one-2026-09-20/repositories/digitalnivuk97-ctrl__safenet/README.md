# SafeNet

Terminal monitor for your own LAN: discovers WiFi/Ethernet devices, scores risk with typesafe JSON rules, builds trust over time, and (Phase 2) watches live connections from this laptop with process ownership.

Linux-first, portable Go single binary (also builds for macOS/Windows).

## The experiment

SafeNet is a testbed for a question: **can a structured-decision AI
(TypeSafe Jev) score network threats better than hand-written rules?**

- Local deterministic rules are the *senses*: instant, offline, free —
  new device? randomized MAC? known-bad server? young domain?
- Jev is the *brain*: one fanned-out API call per entity judges threat
  score, category, and two risk dimensions in parallel; code blends the
  verdict by confidence (confident leads, unsure nudges, clueless ignored).
- Every verdict is logged with latency, tokens, and your Trust/Block
  decisions as ground truth, so speed and accuracy are measurable:
  `./safenet --jev-bench 3` for speed, `./safenet --jev-stats` for agreement.
- **Rule self-audit:** weekly (or `A` key), Jev reviews your labeled history
  and proposes concrete tuning — blend weight, confidence bar, per-rule
  points. Proposals wait in the `A` modal: `y` applies (backup kept),
  `n` rejects. Nothing applies itself.

## Setup

Requirements: Go toolchain only for building; the binary itself needs
`ip`/`ping` on Linux (preinstalled) and nothing else.

```sh
git clone https://github.com/digitalnivuk97-ctrl/safenet && cd safenet
make build && ./safenet        # run from this directory
make install                   # → ~/.local/bin/safenet
./safenet --version            # check build
```

First run creates `~/.config/safenet/` (rules + config) and
`~/.local/share/safenet/safenet.db` (0600). Optional intel keys
(OTX, TypeSafe) go in `~/.config/safenet/config.yaml` — see
`configs/config.yaml.example`. They are never needed for basic use.

Releases: `make release` produces versioned binaries + `SHA256SUMS.txt`
in `dist/` (version comes from the git tag, e.g. `v0.1.0`).

## Roadmap

- **VirusTotal integration** — file/URL/domain reputation as another
  datapoint beside OTX and RDAP.
- **Background monitoring + notifications** — headless daemon mode that
  watches 24/7 and pings you (desktop alert) on new or high-risk
  devices/flows instead of requiring the open terminal.

## Background mode

```sh
./safenet --headless          # no TUI: scan + log + notify until Ctrl-C
make install && make systemd  # persist across reboots (user service)
systemctl --user enable --now safenet
journalctl --user -u safenet -f   # watch what it sees
./safenet                     # open the TUI anytime — same DB
```

Headless sends a desktop notification for every **new device** and every
**alert-routed flow** (confident hostile intent or hot score), gated by
`notify_enabled` in config. Everything else lands in the DB/events log
for later review in the TUI or `--jev-stats`.

## Keys

Tabs: `tab` / `1` devices · `2` connections

Devices: `enter` detail · `t` trust · `b` block · `u` unblock · `n` alias · `/` filter · `o` sort · `x` enrich · `s` settings · `l` live (1s) · `r` reload rules · `q` quit

Connections: `enter` flow detail · `b` block IP · `c` block /24 (or /64) · `u` unblock · `x` enrich

Settings edits apply live, no restart (intervals, trust bump, risk threshold, CIDR).

## How it works

- **Discovery** (`internal/net/discovery`): ping sweep + `ip neigh` on Linux, `arp -a` on macOS/Windows, `arp-scan`/`nmap` fallbacks. Correct /20–/32 v4 math; refuses infeasible ranges.
- **Risk** (`internal/risk`): `rules.json` decoded into strict structs (unknown fields rejected, no `eval`). Device + connection scopes. mtime-cached with last-good fallback and embedded defaults; `R` hot-reloads.
- **Trust** (`internal/trust` + `db`): new devices start 30/NEW, at most +1 per `trust_bump_min` (default 15m) of stable presence; anomalies and manual `T`/`B`/`U` write audited overrides. Missed scans → AWAY (3) → OFFLINE (10m).
- **Vendor ID** (`internal/net/oui`): IEEE OUI CSV parsed once into memory, weekly refresh, rate-limited web fallback for unknowns persisted in SQLite.
- **Connections** (`internal/conn`): gopsutil snapshot shared by TUI + high-risk logger (threshold configurable, 10-min dedupe, 7-day log). Categories: web/dns/ssh/mail/ntp/lan/loopback/remote. No root needed; unknown owners show `?`.
- **DB** (`internal/db`): single SQLite file, WAL, migrations for older DBs, sightings pruned after 30d.

## Config

`~/.config/safenet/config.yaml` (see `configs/config.yaml.example`). Everything is also tunable in the `S` settings modal.

### OTX threat intel (opt-in)

Public remote endpoints can be scored against AlienVault OTX. Set in config:

```yaml
otx_enabled: true
otx_api_key: <key from otx.alienvault.com → Settings → OTX Key>
```

Lookups run at most 20 per 20min (configurable), cached 24h in SQLite,
LAN IPs are never queried, and everything fails open offline. Hits add
+35 risk with pulse tags shown in flow detail and `otx_hit` events.

### RDAP domain age (on by default, no key)

Registrable domains behind public remote endpoints are aged via RDAP
(WHOIS's JSON successor): ≤180d → red `new-domain` tag (+25 risk),
6–12mo → yellow `young-domain` (+10), older → green `established-domain`
(no addition). New-domain hits also raise `rdap_hit` events. Creation
dates cache 30 days; tune with `rdap_*` settings.

## TypeSafe Jev (risk brain, opt-in)

Local rules are the senses (instant, offline, free); Jev is the brain.
One fanned-out call per entity judges threat score, category, is_threat
plus two dimension scores in parallel — extra questions cost no latency.
Code blends by confidence (`rules.json` → `jev:` weight 0.6, high 0.8,
low 0.5): confident Jev leads, mid blends, low keeps local. Operator
allow/block lists are never overruled. No MACs/IPs leave the device.

```sh
./safenet --jev-bench 3   # live speed test: latency + tokens per call
./safenet --jev-stats     # accuracy: agreement, confidence, labels
```

Evaluations trigger on new devices, anomalies, high-risk flows, and the
`X` key; verdicts cache 7 days by state hash. Every call is logged
(`jev_log`: verdict, latency, tokens, operator label from T/B/U).

Flows also get **intent routing**: Jev classifies each flow as normal_app,
telemetry_update, beaconing, or exfiltration. Confident hostile intent
pages you (event + desktop notification); noteworthy-but-quiet flows are
logged only; benign ones stay silent. Intent and route show in flow detail.

Beyond threat scores, Jev also classifies: **device roles** (phone, laptop,
IoT, printer…) shown in device detail and fed back as threat context;
**process masquerading** (typosquat detection, +30 risk when confident);
**hostname origin** (human/vendor/auto/spoofed, +20 when spoofed); and
**alias resolution** — rotated randomized MACs judged same-or-different
device, linked in device detail with `possible_alias` events.

## Test / build

```sh
make test        # full suite
make cross       # linux-amd64 + darwin-arm64 + windows-amd64 in dist/
make install     # → ~/.local/bin/safenet
make systemd     # user unit for background logging
```

## Scope

Your own network only. No packet interception, no deauth/blocking on the wire — "block" means flag + score, enforced nowhere. MACs/hostnames never leave the device.

## License

Copyright (C) 2026 SafeNet contributors.
Released under the GNU General Public License v3.0 or later — see LICENSE.

