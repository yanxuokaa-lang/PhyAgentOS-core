# Cybercab

A browser game where a robotaxi drives down a three-lane highway at dusk and
**Jev**, [TypeSafe](https://docs.typesafe.ai/)'s decision model, is at the
wheel. You throw things at the road (cones, stalled cars, plastic bags, a
child's ball) and watch how it copes.

![The robotaxi passing a stalled car. Jev rates the car "avoid 98%" and the plastic bag "drive over 92%"; the lane signals show it chose the clear right lane with 100% probability.](docs/screenshot.jpg)

Built with Three.js, Express and the
[TypeSafe JavaScript SDK](https://docs.typesafe.ai/sdk/javascript).

## Quick start

```bash
npm install
cp .env.example .env    # add your key from https://console.typesafe.ai/keys
npm start               # open http://127.0.0.1:3000
```

Needs Node 22.9 or newer. Without an API key the game still runs, and a
simple rules planner drives instead of Jev.

## How to play

Jev drives. Your job is to test it.

| Key | Action |
| --- | --- |
| `1` to `=` | Drop an obstacle in the car's lane (or click the tray) |
| `M` | Switch driver: Jev, the rules planner, or you |
| `B` | Turn the safety layer (emergency braking) on or off |
| `J` | Show exactly what Jev was sent and answered for the last decision |
| Arrow keys | Steer and set speed when you drive |
| `P` or Space | Pause (no Jev calls while paused) |

You have three lives. The HUD shows:
- **Lane signals** (top): green ↓ means open, red ✕ means blocked, amber ↘ means moving over. The numbers under the signals are Jev's odds for each lane.
- **Speed sign** (bottom left): the speed and the current speed decision.
- **Panel** (right): Jev's speed odds, the danger score, "someone may step in", and counters for vetoes, safety stops and late answers.

### Obstacles

Every obstacle has a plain-English description, and that is all Jev gets.
Whether it is actually solid is used only for collisions, and Jev never sees it.

| Key | Obstacle | What Jev reads | Solid? | Jev: safe to drive over |
| --- | --- | --- | --- | --- |
| `1` | Traffic cone | An orange traffic cone standing on the road | yes | 0.31 |
| `2` | Stalled car | A broken-down hatchback with its hazard lights flashing | yes | 0.02 |
| `3` | Slow truck | A delivery truck driving slowly in the same direction | yes | 0.02 |
| `4` | Plastic bag | An empty plastic shopping bag blowing along the asphalt | no | 0.95 |
| `5` | Flat box | A flattened, empty cardboard box lying flat on the road | no | 0.89 |
| `6` | Heavy box | A taped-up cardboard box, bulging and sagging under the weight of the tools inside | yes | 0.14 |
| `7` | Truck tire | A loose truck tire lying on the road | yes | 0.10 |
| `8` | Leaves | A thin scatter of dry autumn leaves | no | 0.92 |
| `9` | Puddle | A shallow rain puddle | no | 0.91 |
| `0` | Ball | A child's red ball bouncing into the road (a child runs after it) | no | 0.48 |
| `-` | Pedestrian | An adult walking across the road | yes | 0.02 |
| `=` | Deer | A deer standing frozen on the road | yes | 0.02 |

The last column is what `jev-1.13.0` answered in testing. The game treats an
object as safe to drive over only at 0.80 or higher.

The rules planner only gets a coarse sensor category ("debris", "box").
It can't tell a bag from a tire, so it swerves around both, and it doesn't
slow down for a ball. Press `M` to compare it with Jev.

## How it works

```
browser (60 fps game loop)                  server.js                      TypeSafe
──────────────────────────                  ─────────                      ────────
every 250 ms, numbers only ──POST /api/decide──▶ validate the numbers
  car: lane, x, speed                            describe the road in words
  obstacles: kind, x, gap,                       build the questions    ──▶ Jev answers all
  closing and sideways speed                                                 questions in one
                                                                             request (~300 ms)
act on the answer          ◀──── answers ──────── pick out the answers  ◀──
  drop it if it is stale
  check the lane before moving
  gate on confidence
safety layer checks every frame, whoever is driving
```

**The key stays on the server.** The browser sends only numbers and obstacle
keys; the server writes every word Jev reads. The endpoint can't be used as a
general Jev proxy, it is limited to 10 calls a second, and it listens on
127.0.0.1 only. `.env` is ignored by git.

**Code does the maths, Jev makes the judgments.** Jev is weak with numbers, so
`public/shared/snapshot.js` turns distances into phrases such as "1.5 to 3
seconds away" or "too close for the car to stop before reaching it". It also
describes lanes relative to the car (`current_lane`, `lane_to_the_left`).
Each request then asks, in parallel:

| Question | Type | Asks |
| --- | --- | --- |
| `lane` | Choice | Stay, move left or move right? |
| `speed_current`, `speed_left`, `speed_right` | Choice | Speed up, hold, slow down or brake? Asked once for each lane the car could end up in; the game uses the one for the lane it takes. |
| `drive_over_<id>` | Noul | Can a car drive over this object? Asked once per object and remembered. |
| `person_may_enter` | Noul | Is a person or animal likely to step into the road? |
| `hazard` | Score | How dangerous is the road ahead, from clear (0) to critical (3)? |

**Code decides whether to act** (`public/js/driver.js`, thresholds in
`public/shared/policy.js`):

- **Stale answers:** answers older than 900 ms are dropped, and a failed call hands the wheel to the rules planner for 2 s.
- **Lane changes:**
  - The car changes lanes when Jev's confidence is at least 0.35, but only into a lane the code has checked is clear, including anyone crossing within 70 m.
  - If Jev is torn and the code can see the current lane is blocked, the code tries each side in the order Jev prefers.
- **Speeding up and braking:**
  - Speeding up needs confidence of at least 0.6, unless the code can see the lane is clear.
  - A "brake" below 0.5 confidence counts as "slow down", and "slow down" never undoes an earlier "brake".
  - If someone may step into the road, the car stays under 45 km/h.
- **Cruise control:** when the code sees a clear lane, Jev's danger score is below 1.5 and nobody is likely to step in, only a firm "brake" is followed. Otherwise the car goes back to 90 km/h.
- **Getting unstuck:**
  - Stopped behind something for 2.5 s, or crawling behind it for 4 s: the rules planner picks a lane once.
  - Stopped with nothing in the way for 3 s: the car pulls away.
- **Safety layer:** automatic emergency braking. It runs under every driver and fires only when an emergency stop is nearly the last option, so the driver gets to act first.

## How well it drives

This is from a scripted 80-second drive with `jev-1.13.0`, dropping one of each
obstacle in the car's lane, followed by 20 s of normal traffic:

| | |
| --- | --- |
| Crashes | 0 |
| Safety-layer stops | 0 |
| Distance | 1.63–1.67 km |
| Time under 40 km/h | 14–19% |
| Failed calls / late answers dropped | 0 / 0–2 of about 250 |
| Average round trip | ~320 ms (the first call takes 0.8–1 s) |
| Input tokens per request | ~2,000 |

In the first version the car stopped for plastic bags, sat behind a deer, and
crawled behind slow trucks: 0.92 km, 37% of the time under 40 km/h. These
changes fixed it:

- **Speed and danger questions:** they now say that things a car can drive over are not obstacles. Before that, Jev answered "brake" for a bag.
- **Stopped car:** the state says "a short way ahead of the stopped car" instead of "not getting closer". With that wording, Jev moves over.
- **Truck ahead:** it is described by the actual speed difference ("pulling away" when it is faster than the car).
- **Speed rules:** the cruise-control, low-confidence brake and tie-break rules above replaced blunter ones that caused stop-go driving.

The thresholds are still starting points. Press `J` while playing to see what
Jev saw, and tune from there.

## Cost

About 2,000 input tokens per decision and about three decisions a second. At
$0.042 per million input tokens (output is free), that is roughly **$1 per hour
of play**. Nothing is sent while the game is paused, on the title screen, or in
a background tab.

## Project layout

```
server.js                 Express server: static files and the /api/decide relay
src/questions.js          Everything Jev is asked
src/validate.js           Checks the browser's decision request
public/index.html         HUD markup and styles
public/js/main.js         Game loop, input, camera
public/js/driver.js       Jev / rules / manual driving, safety layer, policy
public/js/obstacles.js    Obstacle models, spawning, collisions, labels
public/js/world.js        Road, lights, scenery
public/js/cybercab.js     The robotaxi model
public/js/hud.js          HUD updates
public/shared/catalog.js  Obstacles, descriptions and ground truth
public/shared/policy.js   Thresholds, timing and car limits
public/shared/snapshot.js How the road is described to Jev
.claude/skills/           TypeSafe agent skill for Claude Code
```

`public/shared/` runs in both the browser and the server.

## Debugging

- **Console access:** add `?debug` to the URL to get `window.cybercab` in the browser console:
  ```js
  cybercab.drop("deer")          // drop an obstacle
  cybercab.driver.history        // the last 400 decisions: answers, actions, speeds
  cybercab.driver.stats
  ```
- **Other servers:** the SDK reads `TYPESAFE_BASE_URL` and `TYPESAFE_DEFAULT_MODEL`, so you can point the game at a stand-in API or pin a model version (see `.env.example`).
- **Screenshots:** `?autostart&drop=stalled_car` skips the title screen and drops obstacles, which is handy for headless browser runs.

## Disclaimer

This is a game. Nothing in it is suitable for controlling a real vehicle.
The robotaxi is a stylised model built from simple shapes. The project is not
affiliated with Tesla or TypeSafe.
