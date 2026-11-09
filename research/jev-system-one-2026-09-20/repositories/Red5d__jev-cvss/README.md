# Jev CVSS Scoring Scripts

Score software vulnerability descriptions with CVSS using TypeSafe's Jev
(`jev-latest`) via the System One API. Jev reads the description and selects the
metric values; the numeric scores are computed in code, exactly per the official
FIRST specifications and verified against reference implementations.

## Requirements

All scripts read the TypeSafe API key from the **`TYPESAFE_API_KEY`** environment
variable. The scripts fail with a clear error if it is not set.

## Scripts

| Script | Version | Scores | Metrics elicited |
|---|---|---|---|
| `cvss3_jev.py` | CVSS v3.0 | Base, Temporal | AV, AC, PR, UI, S, C, I, A + E, RL, RC |
| `cvss31_jev.py` | CVSS v3.1 | Base, Temporal, Environmental | 8 Base + E, RL, RC + CR, IR, AR (Modified metrics default from Base) |
| `cvss4_jev.py` | CVSS v4.0 | Base (+ safety/E) | AV, AC, AT, PR, UI, VC, VI, VA, SC, SI, SA + E + safety Nouls (MSI/MSA:S) |

All scripts take the same input forms:

```bash
export TYPESAFE_API_KEY=...        # TypeSafe API key
python3 cvss31_jev.py "description text..."
python3 cvss31_jev.py -f advisory.txt
cat advisory.txt | python3 cvss31_jev.py
python3 cvss31_jev.py -f advisory.txt --raw   # dump unedited Jev answers
```

## Output

Each script prints:

- The score(s) with qualitative severity rating (None/Low/Medium/High/Critical)
- The vector string(s)
- Every metric value Jev selected, with the top-2 probability spread for each
  choice (useful for seeing which metrics were close calls)
- With `--raw`, the unedited answers JSON

## How scoring works

- **Jev does metric selection only.** One API request per description, with one
  Choice question per metric (plus Noul questions for v4.0 safety). The wire
  format requires `questions` to be a map keyed by question id (a list 422s).
- **Scoring is deterministic code, not the model:**
  - v3.0/v3.1: the closed-form equations from Section 8 (v3.0) / Section 7
    (v3.1) of the FIRST specification documents, including the spec quirks
    (PR weights 0.68/0.50 when Scope Changed; v3.1's ModifiedImpact exponent 13
    with `MISS x 0.9731 - 0.02` and the 0.915 MISS cap; true ceiling rounding).
  - v4.0: the MacroVector algorithm ported from FIRST's reference calculator
    (`cvss_score.js`), with the 270-entry `cvss_lookup.js` table embedded.
    The spec itself designates that file as the source of MacroVector scores.
  - v4.0 safety: base SI/SA only allow H/L/N per spec; the Safety value lives
    on Environmental MSI/MSA:S. Two Noul questions drive those when P(yes) >= 0.5.

## Verification status

- v3.0/v3.1 scoring: exact match on well-known NVD vectors (9.8, 10.0, 7.5, 6.1,
  5.4, 4.3, ...). v3.1 also cross-checked against the official RedHatProductSecurity
  `cvss` Python library on 300 randomized vectors including Environmental
  combinations - 0 mismatches.
- v4.0 scoring: 0/154 mismatches against FIRST's reference implementation run in
  Node, covering safety values, all Exploit Maturity values, and X-defaults.

## Calibration (important)

Descriptions are scored *as written*. Jev's metric choices were calibrated
against NVD conventions using real CVE descriptions; the conventions are baked
into the question criteria:

- **Arbitrary code execution** implies the impact metrics (C/I/A, VC/VI/VA) are
  High, since controlling the process covers confidentiality, integrity, and
  availability.
- **Attack Complexity Low** covers requiring a common deployment (e.g. "runs on
  Tomcat"); High is reserved for races, secrets, and rare target environments.
- **Attack Vector Network** covers browser components (renderer, JS engine, IPC,
  PDF) - a malicious website triggers them remotely. Victim interaction is the
  UI metric, not AV. Local means the attacker already has code execution on the
  system (local privilege escalation).
- **Integrity High** covers signature/validation bypasses where the attacker
  controls the content of what gets accepted (forged claims), even when a
  downstream compensating control limits the blast radius.
- **Scope**: prefer Unchanged when ambiguous (NVD practice is inconsistent).
- **Ignore severity labels in the text** ("Medium impact vulnerability",
  "critical") - judge from technical facts only.

When a score disagrees with an official one, the per-metric probability table
usually shows exactly which metric diverged and by how much.

## Limitations

- Scores only what the description says. Missing impact details cannot be
  recovered; vague descriptions produce vague scores (the probability spread
  will show it).
- Environmental metrics are not elicited for v3.0/v4.0 (v3.1 asks CR/IR/AR;
  Modified metrics default to Base values).
- v4.0 Temporal/Environmental groups other than E and safety are not elicited.
- First live run per script may need parser hardening if the API response shape
  changes - use `--raw` to see the actual answers JSON.

## Helper scripts

- `parse_nvd.py` - extracts descriptions + official CVSS vectors/scores from NVD
  API JSON (`https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-...`)
  into `/tmp/desc_<CVE>.txt` files for regression testing.
- `verify_cvss_scripts.py` - imports all three modules and checks known
  regression vectors.
