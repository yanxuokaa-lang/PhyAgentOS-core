# bitrate-advisor

**Encoder settings for a live stream, decided from telemetry and history, in 300 ms for $0.00005.**

A phone in a gym has to pick a starting bitrate before the first frame goes out, and then keep
choosing every few seconds: hold, step down, step up, drop to 720p because the phone is hot. Most
encoders do this with a fixed ladder and a buffer heuristic that knows nothing about the venue,
the carrier, or what happened the last twelve times someone streamed from that bleacher.

bitrate-advisor puts a decision model in that seat. [TypeSafe's Jev](https://docs.typesafe.ai/introduction)
answers multiple-choice questions over a structured state with calibrated probabilities, fast and
cheap enough to ask on every tick. It reads the current measurements (uplink probe, RTT, jitter,
loss, encoder rate, dropped frames, send queue, thermal state, battery, network type, carrier ASN,
venue) together with priors aggregated from earlier sessions (sustained uplink percentiles, stall
rate per rung, thermal throttle rate) and picks the starting rung, the ceiling, the resolution and
frame rate, and the next step while live.

Then a **deterministic policy fences it in.** Jev may be as bold as the measured network allows and
as cautious as it likes, never bolder. Every clamp is written out in words so a log line explains
itself.

```
telemetry + history ──▶ state ──▶ Jev (one request, three heads) ──▶ answer
                                                                       │
                          policy envelope (probe × headroom, history p10/p50,
                          loss/queue/dropped-frame thresholds, thermal, battery)
                                                                       │
                                                                       ▼
                                          Advice {initialKbps, minKbps, maxKbps,
                                                  resolution, nextStep, targetKbps,
                                                  guardrails[], probabilities, cost}
```

## What it answers

| Question | Choices | When |
|---|---|---|
| `initial_bitrate_kbps` | the ladder (400 … 8000 by default) | start |
| `ceiling_kbps` | the ladder | start |
| `resolution` | 720p30, 1080p30, 1080p60 | start and tick |
| `next_step` | DOWN_1, HOLD, UP_1 | tick |

## Measured, 2026-09-18

Three states, one Jev request each, through OpenRouter (`usage.cost` as billed):

| State | initial | resolution | next step | cost | latency |
|---|---|---|---|---|---|
| iPhone 14, T-Mobile LTE, probe 4.2 Mbps, venue history p50 3.1 Mbps with stalls above 3.5 | 2000 kbps (p 0.72) | 720p30 | HOLD | $0.000041 | 0.39 s |
| iPhone 16 Pro, gym fiber Wi-Fi, probe 41 Mbps, history p50 24 Mbps | 6000 kbps (p 0.77) | 1080p60 (p 0.71) | UP_1 | $0.000041 | 0.25 s |
| same LTE phone, 7 minutes in, loss 2.1%, send queue 1.8 s, 6.5% dropped frames | | 720p30 | DOWN_1 (p 0.94) | $0.000044 | 0.29 s |

At one decision every 10 seconds that is about **$0.015 per hour of stream**.

## Use it

Deno, Node 20+ or an edge runtime; no dependencies; the only network call is to Jev. Import `mod.ts`.

```ts
import { advise, aggregateHistory } from "./mod.ts";

const history = aggregateHistory(pastSessions, { venueId, carrierAsn, deviceModel });

// before going live
const start = await advise("start", {
  platform: "iOS 19", deviceModel: "iPhone14", batteryPct: 35, thermalState: "fair",
  networkType: "cellular", carrierAsn: "AS21928", venueId: "foothill-ms-gym",
  uplinkProbeKbps: 4200, rttMs: 62, jitterMs: 18, packetLossPct: 0.4, secondsLive: 0,
}, history, { apiKey: OPENROUTER_API_KEY });
// start.initialKbps 2000, start.maxKbps 2000, start.resolution "720p30", start.guardrails [...]

// every 5 to 10 seconds while live
const tick = await advise("tick", { ...now, currentRungKbps: 3000, secondsLive: 410,
  packetLossPct: 2.1, sendQueueMs: 1800, droppedFramesPct: 6.5 }, history, { apiKey });
// tick.nextStep "DOWN_1", tick.targetKbps 2000
```

Every Jev call carries a per-attempt deadline (`timeoutMs`, 2.5 s) and a total budget across
retries (`totalBudgetMs`, 5 s); when either runs out the policy answers, so a stalled provider can
never hold up a go-live.

CLI: `deno task advise start examples/weak-lte-start.json`. Without an API key the same call
returns the policy's answer with `source: "policy"`, so a client never blocks on the model.

## The envelope

The policy is the safety envelope and Jev may only match it or be more conservative.

- Cap = min(uplink probe × headroom (0.7), history p10 × 1.1, 3000 when nothing is known).
  The starting rung and every target sit at or below it. A link that cannot carry the 400 kbps
  floor starts at the floor with a guardrail sentence saying stalls are expected.
- Ceiling = min(probe × headroom, history p50).
- A tick moves at most one rung. UP_1 needs 60 clean seconds (loss < 0.5%, queue < 200 ms,
  dropped < 0.5%). DOWN_1 is forced at loss > 2%, queue > 1 s or dropped frames > 3%.
- 1080p60 needs a target of 4500 kbps or more, a nominal thermal state, 30% battery and a low
  history of thermal throttling; serious or critical thermal drops to 720p30.

Inside that envelope Jev decides earlier and with more context than a buffer heuristic: it sees
that this venue on this carrier stalls above 3.5 Mbps two times out of five, that this phone model
throttles at 1080p60, that the send queue has been climbing for three ticks.

## Battery and thermal: finish the game

A stream that stalls is bad; a phone that dies in the fourth quarter is worse. Give the advisor
the battery level, whether it is charging, the measured drain (percent per minute, from two
battery readings a few minutes apart) and the minutes left in the game, and it adds a power plan:

| Plan | What changes |
|---|---|
| `FULL` | nothing, the phone will finish with margin |
| `SAVE_FPS` | 1080p60 becomes 1080p30 |
| `SAVE_RES` | drop to 720p30 |
| `SAVE_MAX` | 720p30 and the bitrate capped at 2000 kbps |
| `PLUG_IN` | it will not finish even at the floor: tell the streamer now, not at 3% |

The projection is deterministic (`projectPower`, with a 5% reserve; serious thermal forces at
least `SAVE_RES`, critical forces `SAVE_MAX`, Low Power Mode at least `SAVE_FPS`). Jev answers the
same question with the whole state in view and may only make the plan more conservative. The
result rides on the advice as `advice.power` and one more guardrail sentence.

## Events, not just ticks

`EventAdvisor` reacts the moment something happens instead of waiting for the next timer:

```ts
import { EventAdvisor } from "./mod.ts";
const ev = new EventAdvisor({ apiKey });
// urgent: disconnect, thermal_change, battery_low, network_change, dropped_frames_spike,
// send_queue_growing react immediately; the rest are debounced (3 s); ticks are throttled (5 s)
const advice = await ev.onEvent({ type: "thermal_change", atMs: Date.now(), detail: "fair -> serious" }, telemetry, history);
// or derive events from two consecutive telemetry samples
for (const e of EventAdvisor.eventsFromDelta(previous, current, Date.now())) await ev.onEvent(e, current, history);
```

Every event line lands in `recent_actions`, so Jev sees "t+412s thermal_change: fair -> serious"
right above the numbers.

## History

`aggregateHistory(sessions, key)` turns per-session summaries (sustained uplink, the rung at which
the session first stalled, resolution used, whether the device throttled) into priors, choosing
the narrowest scope with at least three sessions: venue + carrier, then carrier, then device model,
then everyone. Store one summary row per stream and you have the prior for the next one.

## Why we built it

bitrate-advisor is part of [Firmi](https://firmi.ai), the agent that runs a youth sports club's
app. Parents stream games from phones on gym Wi-Fi and cellular that changes by the quarter, and
the same venues come back every season. The history from every stream is the cheapest signal we
have, and Jev is cheap enough to consult it on every tick. MIT licensed; issues and pull requests
welcome, especially session summaries from other kinds of venues.

Sibling project: [ghosthands](https://github.com/affirmitv/ghosthands), the same decision model
driving a real mouse over legacy web systems.
