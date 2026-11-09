# jev-pii-checker

[![CI](https://github.com/coo-quack/jev-pii-checker/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/coo-quack/jev-pii-checker/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CLI for scanning text and files for PII using TypeSafe's Jev model, regex patterns, and word segmentation.

📖 **[Documentation](https://coo-quack.github.io/jev-pii-checker/)** — getting started, CLI reference, how the three layers work, categories and sensitivity levels, limitations.

> [!WARNING]
> **The scanned text is sent to TypeSafe's Jev API.** Detection happens on their servers, so this tool is not a local-only guard: everything you scan leaves your machine. Use it only on data you are allowed to hand to a third party, such as text you were going to send to an LLM anyway, and check TypeSafe's data-retention terms before scanning anything you would not send there directly. For a guard that never sends anything, see [sensitive-canary](https://github.com/coo-quack/sensitive-canary). Details in [SECURITY.md](SECURITY.md).

## Features

**Three-layer detection:**

1. **Gate** — 13 PII category Nouls (person name, email/phone, postal address, date of birth, government ID, financial account, health info, biometric, IP address, SNS handle, employment, race/religion) + 3-level sensitivity score (none/low/high, IBM taxonomy)
2. **Regex** — Extract emails, JP/intl phones, digit strings (10–16 chars); filter corporate addresses (noreply@, 0120-, server IPs)
3. **Segmentation** — Generate person-name candidates using `Intl.Segmenter`, query Jev for judgment, assemble overlapping spans, attach title suffixes

**Output:**

- JSON: machine-readable (categories, sensitivity level, findings with spans)
- Human: compact table per file, plaintext
- Exit codes: 0 = none, 1 = error, 2 = severity ≥ threshold

## Measured Results

- Gate accuracy: 100% on person_name / email_or_phone / phone presence (IBM corpus)
- Sensitivity levels: 22/24 correct (seminar/clinic context distinction works)
- Digit disambiguation: correctly classifies credit cards, My Numbers, order numbers, product serials

## Install

Install globally from npm:

```bash
bun install -g @coo-quack/jev-pii-checker
# or run without installing
bunx @coo-quack/jev-pii-checker report.txt --json
```

Requires Node.js 20+ or Bun.

### From source

```bash
bun install
bun run build
jev-pii-checker --version
```

## Usage

### Scan stdin

```bash
export TYPESAFE_API_KEY="your-key-here"
echo "佐藤健一郎さんの携帯は090-1234-5678、メールはk.sato@example.co.jpです。" \
  | jev-pii-checker --json
```

### Scan files

```bash
jev-pii-checker file1.txt file2.txt --json --show-values
```

### Exit on severity

```bash
jev-pii-checker data.txt --fail-on high
echo $?  # 2 if high-sensitivity PII detected, 0 otherwise
```

### Masking (default)

By default, PII values are masked as `first2…last1`:

- `john@example.com` → `jo…m`
- `090-1234-5678` → `09…8`

Use `--show-values` to disable masking (for debugging).

## Flags

```
--json                 Output JSON (default: human-readable)
--threshold <0-1>      Gate probability threshold (default: 0.5)
--span-threshold <0-1> Name candidate threshold (default: 0.8)
--no-spans             Skip name extraction (regex only)
--fail-on none|low|high Exit with code 2 if sensitivity >= level (default: none)
--show-values          Show unmasked PII values
--max-chars <n>        Chunk size in bytes (default: 4000)
--model <id>           TypeSafe model ID (optional; uses SDK default)
--concurrency <n>      Parallel requests (default: 4; not yet implemented)
--help                 Show help
--version              Show version
```

## Environment

- `TYPESAFE_API_KEY` — Required. TypeSafe API key.

**Setting up the key:**

```bash
# If your key file has no `export`:
set -a
source ~/.config/chata/typesafe.env
set +a
jev-pii-checker file.txt
```

## Limitations

- **Public figures**: Cannot distinguish historical or public figures (e.g., "Natsume Soseki" may be flagged as a person name). Names are always treated as PII unless reviewed manually.
- **Borderline HR/discipline records**: Sensitivity for confidential performance reviews and disciplinary records can flip between low and high across runs when the model's probabilities sit near 0.5 (e.g., 0.47/0.53 low/high boundary). Run multiple times for high-confidence assessments.
- **Candidate rules are list-based**: Political/military/legal/clerical titles and form labels (Name, Email, Phone, Subject, etc.) are hard-coded. Unknown titles may still be merged into a name.
- **Checksum verification**: Credit card Luhn checksums and passport/ID formats are not validated, so synthetic or invalid numbers may be flagged.
- **Code/config snippets**: JSON, SQL, regex patterns treated as plain text; variables named like PII attributes (e.g., `person_name`, `user_id`, `phone_number`) may be over-reported.
- **Organization names**: Out of scope; cannot identify company/brand/institution names.

## Development

```bash
bun install
bun run dev file.txt
bun run lint
bun run format
bun test
bun run build
```

### Integration tests

```bash
set -a
source ~/.config/chata/typesafe.env
set +a
JEV_PII_INTEGRATION=1 bun test tests/integration.test.ts
```

## License

MIT — see LICENSE for details.
