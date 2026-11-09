# Jev for engineers — eight minimal working examples

[TypeSafe's](https://typesafe.ai) **Jev** is a *System One* model. It does not
write text. You give it a **state** — any text or JSON — and a map of **named,
typed questions**, and it returns one typed answer per question with a
**calibrated probability distribution** attached.

There are exactly three question types:

| Type | Ask | Get back |
|---|---|---|
| `noul` | a yes/no question | `0.92` — the probability the answer is yes (**no confidence field**) |
| `choice` | pick one from a closed set | the winner, the full distribution, and a confidence |
| `score` | rate against ordered levels | a probability-weighted float that can land *between* levels, plus a legend, distribution and confidence |

Every question in a request sees the same state and is answered independently,
so twelve questions in one call cost about what one call costs. TypeSafe
measured a 13-question briefing as **12.2× cheaper and 10.0× faster** batched
into one call than asked one at a time, with no change in the answers. So don't
loop — fan out.

These examples are aimed at mechanical and electrical engineering work: CAD,
CAE, CAM, BOMs, drawings and change control. Each one ends by taking **a
decision in ordinary Python**, because that is the actual argument. Jev supplies
calibrated inputs; your policy stays in your code, in the open, where it can be
reviewed.

## Status — what has actually been run

**Every example below has been executed against the live API** (`jev-latest`,
2026-09-17). Models available to the account: `jev-latest`, `jev-preview`.

Three results worth quoting, because they are the ones that could have gone
badly and didn't:

- **06 separates the pair that string similarity gets backwards.** A line
  reading "SOCKET HEAD CAP SCREW M6X20 A2-70" against one reading
  "Cilinderschroef met binnenzeskant M6x20 DIN 912 RVS A2" — different
  language, different numbering, same screw — scored **1.91/2.00, confidence
  0.86 → merge**. `M6x20` against `M6x25`, one character apart, scored
  **0.01, confidence 0.99 → keep separate**. (Sample data only; see
  [`data/README.md`](data/README.md) — the part numbers are invented.)
- **03 rejected a diverged solve.** `converged 0.03`, `mesh_limited 0.93`,
  `trust 0.02` on a log whose last lines are `too many cutbacks`. The 214.8 MPa
  figure was refused before it could reach a design review.
- **08 caught a bad idea that passes every deterministic check** — an 11.2 mm
  full-depth pass with a 3 mm cutter — at `one_pass_too_deep 0.78`.

**Three defects were found by running it, and all three were mine, not Jev's.**
They are documented in the files where they happened, because the mistake is
more instructive than the fix:

1. **05 rejected the correct answer.** The guard asked whether the value came
   "from the revision history"; `+/-0.1` appears in *both* note 7 and the REV C
   line, so a truthful `0.77` threw out the right tolerance. The question was
   wrong, not the threshold.
2. **08 asked a judgement model to do arithmetic.** It answered at confidence
   **0.04–0.28** with nouls near 0.5 — total ignorance — and the gates still
   said BLOCK, which *looked* like a success. The depth check now lives in
   Python where it belongs; Jev is asked only what a subtraction cannot decide.
3. **07's thresholds were guesses.** `0.70` sat in the middle of the measured
   confidence cluster and an obvious purchasing substitution missed it by
   `0.01`. Now `0.60` / `0.85`, set from a measured run.

**What is still not established:** these are ten synthetic ECRs, eight BOM
pairs, and one solver log. That is a demonstration, not a calibration. Every
threshold here is fitted to a sample far too small to build on — **re-measure on
your own data.** The code annotates each one with what it was measured against
so you can see what you are inheriting.

There are no mocked or recorded responses anywhere. The only response fixtures
in the test suite are copied verbatim from
[TypeSafe's published examples](https://docs.typesafe.ai/api) and labelled as
such, because a fixture you write yourself can only confirm your own model of
an API.

There are deliberately **no recorded or mocked responses** anywhere in this
repo. A fixture you write yourself can only confirm your own model of an API —
it stays green while the first real call returns something else. The only
response fixtures in the test suite are copied verbatim from
[TypeSafe's own published examples](https://docs.typesafe.ai/api) and are
labelled as such.

Sample inputs under `data/` are **entirely synthetic** — see
[`data/README.md`](data/README.md). The manufacturer names are real companies;
the part numbers, prices and descriptions attached to them were made up to look
plausible. Don't read an engineering conclusion out of any of it, and don't use
the BOM file as a cross-reference table.

## Running

Python 3.10+. **No dependencies** — `jev.py` is about a hundred lines of stdlib.

Every example runs without an API key, printing the exact request it would send:

```bash
python 01_three_question_types.py          # dry run
python -m unittest discover -v             # 28 offline tests
```

To make real calls, create a key at
<https://console.typesafe.ai/settings/keys> and export it:

```bash
export TYPESAFE_API_KEY="..."              # bash
$env:TYPESAFE_API_KEY = "..."              # PowerShell
python 03_fem_triage.py
```

For production code prefer the official SDK (`pip install typesafe-sdk`).
`jev.py` is deliberately small so you can see what goes on the wire.

## The examples

| | Shows | The point |
|---|---|---|
| **01** `three_question_types` | all three types in one call | a shop-floor note becomes a structured, actionable decision |
| **02** `intent_routing` | Choice as a router | "thicken the web" vs "will the web hold" differ by *intent*, not vocabulary — a keyword table cannot separate them |
| **03** `fem_triage` | object state + strict gates | a solver can finish, write a readable result, and still have converged on nothing. Exit status doesn't tell you; grepping for `ERROR` doesn't either |
| **04** `dfm_screen` | speculative fan-out | twelve questions at once, including companion questions read *only* when their parent fires |
| **05** `extraction_without_hallucination` | regex finds candidates, Jev selects | the model can only return a span cut from the document, so a fabricated dimension is **unrepresentable**, not merely unlikely |
| **06** `bom_alignment` | Score levels **are** the actions | merge / curator / keep-separate. No thresholds to fit — and string similarity gets this exactly backwards |
| **07** `confidence_routing_at_scale` | confidence as a second axis | ten change requests; the split between "cleared automatically" and "a human reads this" *is* the product |
| **08** `cam_guardrail` | deterministic checks first | a syntax checker says the G-code is valid. It is also 0.4 mm into the soft jaws |

Two ideas recur, and they are the ones worth taking away:

**The answer tells you *what*; confidence tells you *whether to act*.** Those are
different questions, and thresholds should scale with what being wrong costs —
one global number cannot express that a mis-routed purchase order and a
mis-routed E-stop change are different mistakes (see `07`).

**A `noul` carries no `confidence` field.** A gate that thresholds confidence on
a noul can therefore never fire. `jev.confidence_of()` derives one instead —
0.5 is maximal ignorance, either pole is a firm answer — and the test suite
pins all three points, because a guard that cannot fire is worse than no guard.

## Layout

```
jev.py                 ~100-line stdlib client; read this first
01..08_*.py            one example each, standalone, heavily commented
data/                  synthetic sample inputs
test_examples.py       28 offline tests; no key, no network, no spend
```

## Licence

MIT — see [LICENSE](LICENSE).
