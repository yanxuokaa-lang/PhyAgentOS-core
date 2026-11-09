# cwi-voice-command

Speak mixer commands on your phone — the page decides locally and drives the
mixer instantly. Client-side only, zero dependencies, GitHub Pages ready.

**"mute singer" → vocals mute. "pan it 50% to the left" → guitar pans left.
"mute singer, break, solo guitar" → three clauses, all-or-nothing.**

## Use it on your phone in under a minute

1. Open the deployed page URL on your phone.
2. Tap the big 🎙️ button and allow microphone access.
3. Speak a command — "mute singer", "set reverb 25%", "pan it 50% to the left".
   Watch the mixer nodes light up and the log show transcript → decision JSON →
   confidence → acted / confirmed / escalated.

Medium confidence? Real **Yes/No** buttons. Too unclear? The discussion lane
**speaks** a clarification question and your next utterance resolves in context.

No mic handy: switch STT to **Mock** in the Adapters panel and type commands.

## Architecture

`ARCHITECTURE.md` — the full picture. Short version:

- **Adapter layer** (`src/adapters/`): Decision / STT / TTS / Escalation lanes,
  each with a fixed interface and hot-swappable backends (`src/config.js`).
- **Decision** (`src/adapters/local-classifier.js`): rule-based $0 classifier
  emitting Jev-shaped typed decisions + confidence
  (`layer: 'local-classifier-v1'`). Same module runs in Node tests and the page.
- **Handover** (`src/handover.js`): Pipecat-style `command → confirm →
  escalated` state machine; 0.85 act / 0.60 confirm / below escalate;
  compound batches are atomic.
- **Mixer** (`src/mixer.js`): per-track mute/solo/reverb/pan/volume + transport;
  destructive actions gate at ≥ 0.85 confidence.

Tests: `npm test` — 51 tests, zero dependencies.

## Honest limits

- **No Jev integration.** TypeSafe's Jev is waitlist-only; the `jev` backend is
  wired but dormant — it refuses explicitly rather than fabricating decisions.
- **No PSTN/telephony validation.** This is a local browser demo. The downstream
  telephony path is [cwi-voice-bridge](https://github.com/CumulativeWebInc/cwi-voice-bridge)
  (Twilio playout pacing, 25/25 tests green) — documented, not re-verified here.
- **STT is the browser's service.** Recognition runs through the Web Speech API;
  audio may go to the browser vendor's speech service, and recognition quality
  is theirs, not ours. iPhone STT latency is unmeasured (see `LATENCY.md`).
- **Escalation v1 is template-based, not an LLM.** The discussion lane asks
  deterministic clarification questions and is labeled as such; the real-LLM
  wiring is dormant until a key exists.
- **Latency numbers are browser-loopback** (final transcript → state applied +
  DOM updated). They exclude STT time. See `LATENCY.md`.
