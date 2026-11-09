# qa-duel

**Three ways to QA a website, compared: TypeSafe Jev, a GPT-5.6 reviewer, and a hybrid.**

Black-box QA of [saucedemo.com](https://www.saucedemo.com/) — a public demo shop whose
accounts are documented to carry known defects, which gives us ground truth without
touching anyone's production site.

## Method

1. **Capture** seven page states with a real browser (agent-browser + Chrome):
   login, locked-out error, inventory (standard / problem / visual users), item detail,
   and a checkout validation error. For each state we save:
   - visible elements with pixel boxes, font sizes, colors, contrast ratios
   - images with natural sizes and sources
   - candidate overlaps and cut-off elements, console errors
   - **a screenshot**
2. **Judge with three modes**:
   - `jev` — one TypeSafe request per state: a 6-check rubric (Nouls + a Score) plus a
     `verdict` Choice (clean / minor / serious). No screenshots.
   - `llm` — gpt-5.6-sol gets the same state **plus the screenshot** and writes a full
     markdown report (severity, evidence, fix).
   - `hybrid` — Jev screens every state; a state is escalated to the LLM when Jev's
     verdict confidence is below 0.6.
3. **Score against truth**: `inventory-problem` and `inventory-visual` carry the
   documented defects; the other five states are healthy controls.

```sh
npm install
export OPENAI_API_KEY=... TYPESAFE_API_KEY=...
npm run duel                # capture + judge + write reports/
npm run duel -- --fresh     # ignore the cached model results and call again
```

## Results

| mode | states flagged | TP/FP/FN/TN | documented-defect recall | extra states flagged | cost | wall time | report |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| jev | 7 / 7 | 2/5/0/0 | 100% (by accident) | 5 | $0.0014 | 3.7 s | 505 words (mostly tables) |
| llm | 5 / 7 | 2/3/0/2 | 100% | 3 | $0.196 | 103 s | 730 words, actionable |
| hybrid | 5 / 7 | 2/3/0/2 | 100% | 3 | $0.196 | 106 s | 823 words |

## What actually happened

**The LLM found the real defects.** On `inventory-problem`:

> **Major — All products display the same incorrect image.** Each of the six cards shows
> an identical dog photo despite representing different products; all image URLs reference
> `/assets/sl-404-Cq1a9k9X.jpg`, indicating a fallback/404 asset. **Recommended fix:**
> Restore the correct product-specific image URLs and verify asset delivery for every
> catalog item.

On `inventory-visual` it caught the pug-where-a-backpack-should-be plus the misleading
asset path, and on the healthy states it correctly said "clean" (login, locked-out,
standard inventory). Its three "extra" flags are not nonsense either — e.g. on the item
page it reports the 20×20 px menu button as a minor tap-target issue. Strict, but fair.

**Jev never said "clean".** Its verdicts were `minor`/`serious` on all seven states
(confidence 0.24–0.49), and on the state with the real defect it flagged generic items
(overlap, small targets, contrast) while **missing the broken media entirely**
(`broken_media = 0.25`). As a standalone QA judge it over-flags and under-explains.

**The hybrid degenerated.** Because Jev's confidence was below 0.6 on every state, the
gate escalated 7/7 — the hybrid paid the full LLM cost and shipped the longest report
with no extra value. The gate only saves money when the cheap model is *usually confident*
and occasionally wrong; here it was honest about being unsure everywhere.

## Where each mode fits

| | Jev | LLM | hybrid |
| --- | --- | --- | --- |
| cost per full pass (7 states) | $0.0014 | $0.196 | $0.196 (gate fired everywhere) |
| time | 3.7 s | 103 s | 106 s |
| output | typed checks + verdict | narrative report with fixes | Jev lines + LLM write-ups |
| strength | cheap, fast, typed, no parsing | finds real defects, explains root cause, writes the fix | would combine both *if* the confidence gate discriminated |
| weakness here | no pixels, vague rubric → flags everything, misses the real defect | 140× the cost; strict on minor targets | paid LLM cost for decoration |

Practical reading: use the LLM where a human will read the report; use Jev only with a
much crisper, mostly-mechanical checklist (exact thresholds, explicit evidence rules) as a
cheap first pass — and calibrate its confidence on your own pages before trusting a gate.

## Layout

```
src/browser.ts    capture a page state (elements, images, overlaps, console, screenshot)
src/questions.ts  the rubric, serialization, prices
src/jev.ts        the Jev judge
src/llm.ts        the LLM judge (with screenshot)
src/run.ts        capture → three modes → reports/ → score
states/           captured JSON + PNG per state (evidence)
reports/          jev.md · llm.md · hybrid.md · summary.md
truth.json        documented-defect ground truth
```
