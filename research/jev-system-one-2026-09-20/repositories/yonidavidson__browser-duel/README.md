# browser-duel

**Who picks better links — an LLM or TypeSafe's Jev?**

Everyone is wiring LLMs into browsers now, one click at a time. This is a small, fair
experiment: the same browser, the same page, the same candidate links, two different
decision makers choosing where to click next. A wiki race, run twice.

## Method

- **Browser**: `agent-browser` (Chrome over CDP), one session, navigation by clicking the
  chosen link.
- **Each step**: extract the first 60 content links from the article (`#mw-content-text`),
  **text only — no URLs**, deduplicated, nav/citation lines filtered out. Both drivers see
  exactly the same list.
- **Drivers**:
  - `jev` — one TypeSafe `systemone` request per step: a Choice over the link ids (option
    description = link text), plus a `goal_reached` Noul. One more option, `none`, means
    "the current page already is the goal page".
  - `gpt-5.6-luna` / `gpt-5.6-sol` — one chat completion per step: the same goal, visited
    pages, and link list; the answer must be one link id or NONE.
- **Stop**: reached the goal article (URL/title check), the driver says NONE, or the step
  budget runs out. The harness detects clicks that fail to navigate and stops with `stuck`.
- Clicking is a programmatic `element.click()` on the visible anchor — the CLI's
  coordinate click silently misses some Wikipedia links (found the hard way).

Two tasks:

| task | start | goal | why |
| --- | --- | --- | --- |
| easy | Coffee | **Sanaa** — "the capital city of Yemen" | 2 hops, one fact (Yemen is where coffee spread from) |
| hard | Coffee | **Albert Einstein** — the physicist | needs a semantic chain through science/history; the link is never on the page |

## Results

### easy — Coffee → Sanaa

| driver | result | clicks | deciding | cost |
| --- | --- | ---: | ---: | ---: |
| jev | ✅ reached | 2 | 2.0 s | $0.000232 |
| gpt-5.6-luna | ✅ reached | 2 | 1.9 s | $0.000239 |
| gpt-5.6-sol | ✅ reached | 2 | 5.2 s | $0.004108 |
| hybrid (jev<0.5→luna) | ✅ reached | 2 | 2.1 s | $0.000232 |

Both routes: Coffee → Yemen → Sanaa. Everyone got it; Jev was the cheapest by a hair and
18× cheaper than `sol`. The hybrid never needed to escalate (Jev's confidence was 1.00 on
both steps).

### hard — Coffee → Albert Einstein

| driver | result | clicks | deciding | cost |
| --- | --- | ---: | ---: | ---: |
| jev | 🛑 gave up | 8 | 3.3 s | $0.001064 |
| gpt-5.6-luna | ✅ reached | 8 | 29.5 s | $0.003077 |
| gpt-5.6-sol | ✅ reached | 5 | 23.6 s | $0.017396 |
| hybrid (jev<0.5→luna) | ⏱ max steps | 14 | 62.9 s | $0.006481 |

Routes:

- **luna**: caffeine → Stimulant → cognition → Thought → thought experiments → physics →
  relativity → **Albert Einstein**
- **sol**: Avicenna → physics in the medieval Islamic world → History of physics → Modern
  physics → **Albert Einstein**
- **jev**: caffeine → PubChem → Wikidata → English Wikipedia → Main Page → English
  language → List of countries… → British Empire → gave up. Without world knowledge it
  can't bridge "coffee" to "Einstein", drifts into meta pages (Wikidata, namespace pages),
  and stops when nothing looks promising (its `none` choice, p=0.27).
- **hybrid**: caffeine → Stimulant → cognition → philosophy → German → Science →
  philosophy of science → Modern → Contemporary → philosophy of science → History →
  History of philosophy → German idealism → Kant → Copernican Revolution → Isaac Newton,
  then ran out of steps. Jev's confidence stayed below 0.5 on 12 of the 14 steps, so the
  gate escalated almost every decision to `luna` — the expensive path became the default,
  and the hybrid cost 2× luna while doing worse. A confidence gate only pays off when the
  cheap model is *usually* confident and *occasionally* wrong; on an out-of-distribution
  task like this, low confidence everywhere defeats it.

## Hybrid: Jev decides, GPT only when Jev is unsure

The third driver runs Jev first and escalates the step to `luna` when Jev's confidence
falls below a threshold (`--threshold`, default 0.5):

| task | escalations | cost | result |
| --- | ---: | ---: | --- |
| easy | 0 / 2 | $0.000232 | ✅ reached (pure Jev) |
| hard | 12 / 14 | $0.006481 | ⏱ ran out of steps |

That is the honest version of the confidence-gated routing idea: it works beautifully when
the cheap model knows what it knows (easy task — never escalated), and it degrades to
"pay for both" when the task is outside its training distribution.

## Trade-offs

| | Jev (System One) | GPT-5.6 (luna / sol) | hybrid (jev→luna) |
| --- | --- | --- | --- |
| **value** | typed, constrained choice; always a valid link; great on direct, well-posed steps | plans multi-hop routes; brings world knowledge the prompt doesn't contain | Jev quality on in-distribution steps, LLM quality on the hard ones — when the gate is trustworthy |
| **speed** | ~0.3–1.1 s per decision (median ≈0.4 s) | ~0.8–7.7 s per decision (median ≈2.5 s) | Jev speed when it stays below the bar |
| **cost / decision** | ~$0.00012 | luna ~$0.0004 (hard) · sol ~$0.0035 | $0.00012, or $0.0006 when it escalates |
| **cost / episode (hard)** | $0.0011 (no result) | luna $0.0031 · sol $0.0174 (both reached) | $0.0065 (no result — over-escalated) |
| **ease of integration** | one endpoint; answer guaranteed to be one of your ids; probabilities + confidence to gate on | one endpoint; free-text answer needs parsing and validation; transient 500s need retries | two endpoints and a threshold to calibrate |
| **failure mode** | no world knowledge → wanders, then gives up | cost and latency; occasional off-format or server errors | gate fires everywhere → pays both, or gate never fires → misses |

The short version: **for narrow, well-posed decisions Jev is ~3–30× cheaper and ~6× faster
with a stronger interface; for the decisions that need general knowledge, the LLM still
wins.** The natural hybrid — Jev on every step, escalating to an LLM when its confidence
is low (TypeSafe's confidence-gated routing pattern) — is the obvious next experiment.

## Run it

```sh
npm install
export OPENAI_API_KEY=...           # for the GPT drivers
export TYPESAFE_API_KEY=...         # for the Jev driver
npm run duel                        # both tasks, all drivers
npm run duel -- --drivers=jev       # one driver (jev, luna, sol, hybrid)
npm run duel -- --tasks=hard        # one task
npm run duel -- --drivers=hybrid --threshold=0.5   # confidence gate
```

## Layout

```
src/browser.ts   agent-browser wrapper: open, extract 60 content links, click, wait
src/jev.ts       TypeSafe driver: a Choice over link ids + a goal NONE
src/openai.ts    GPT driver: same list in a prompt, answer parsed and validated
src/race.ts      the loop: extract → decide → click → check goal
src/run.ts       tasks, tables, flags
```

## Notes

- Link ids are stripped of URLs on purpose: the drivers judge *text*, not hints like
  `/wiki/Albert_Einstein`.
- Jev's instructions were tuned once after the first run (it answered "none" immediately);
  the guidance is generic ("avoid meta pages"), not answer-leaking.
- Runs are single samples on a live web; Wikipedia's link set changes over time.
