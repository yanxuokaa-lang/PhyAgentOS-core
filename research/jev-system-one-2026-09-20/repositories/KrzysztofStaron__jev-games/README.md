# Jev Tetris

TypeSafe Jev plays Tetris through Vercel AI Gateway.

Open `http://localhost:3000`, click Start, and watch. Each piece's well is sent to Jev as glyphs plus a list of legal placements. Jev picks a placement id. The session holds, rotates, DAS-shifts, and hard drops that landing, then asks again. Play stops at the score goal, top-out, or Emergency stop. Each of those muxes an mp4 you can download. The mp4 has no Jev wait time.

## Run

Needs Node 20+, FFmpeg on `PATH`, and `AI_GATEWAY_API_KEY` in `C:\Users\kisie\.vercel-ai-gateway.env`.

```
npm install
npm start
```

Then open `http://localhost:3000` and click Start. The video lands in `videos/`.

## Test

```
npm test
npm run typecheck
```
