# Scam Shield

Checks a text message for scam signals with TypeSafe's Jev model, then turns those signals into
an explainable verdict with rules you control.

## Run it

```bash
cp .env.example .env.local   # then add your TypeSafe API key
npm run dev                  # http://localhost:5173
npm test                     # unit tests for link parsing and policy (no API calls)
npm run eval                 # live run over the labeled samples
```

## How it works

1. **Code** extracts facts it can observe: link domains, URL shorteners, risky TLDs, IP links,
   and whether the sender is a phone number, short code, or email address
   ([signals.ts](src/server/signals.ts)).
2. **TypeSafe** answers eleven narrow questions in one parallel call: eight Nouls (asks for credentials,
   unusual payment, link doesn't match the brand, and so on), one Score (pressure), and one Choice
   (scam pattern) ([check.ts](src/server/check.ts)).
3. **Policy** combines judgments and code signals into a weighted risk score, with a floor so
   any single serious red flag at 90%+ can't be marked safe ([policy.ts](src/shared/policy.ts)).
   It is a pure function, so the threshold sliders re-score results without new API calls.

The API key stays on the server. `/api/check` is one Web-standard handler
([handler.ts](src/server/handler.ts)), served by a Vite plugin in `dev` and `preview`
([api.ts](src/server/api.ts)) and by a Vercel Function in production ([api/check.ts](api/check.ts)).

## Deploy

The site is hosted on Vercel. Set `TYPESAFE_API_KEY` in the Vercel project's environment
variables; pushes to `main` deploy automatically. The endpoint has no auth or rate limit, so anyone
with the URL can spend TypeSafe credits. Take it down or add protection after the demo.

## Accuracy, honestly

On the 16 hand-written samples in [samples.ts](src/shared/samples.ts), the default policy flags
9/9 scams with 0/7 false alarms. The weights and two questions were adjusted after looking at
those same samples, so treat this as a smoke test, not a measured accuracy. Run
`npm run eval -- your-messages.json` on real labeled texts before trusting the thresholds.
