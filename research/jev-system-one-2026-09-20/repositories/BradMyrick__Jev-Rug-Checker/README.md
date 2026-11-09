# rugcheck

A one-file token screener for EVM chains. You give it a token (address or symbol),
it pulls free public data, asks the [TypeSafe](https://typesafe.ai) model **Jev** exactly one
question set, and prints a verdict: **PASS / CAUTION / AVOID** with the reasons that
produced it.

No dependencies. No API keys for the data sources. One environment variable
(`TYPESAFE_API_KEY`) for the judgment model.

```bash
python3 rugcheck.py                          # COQ on Avalanche (built-in sample)
python3 rugcheck.py --chain eth 0xdAC17F...  # USDT on Ethereum
python3 rugcheck.py --chain base BRETT       # symbol works too
python3 rugcheck.py --list-chains            # 22 chains
```

Example output, real run:

```
Token:     COQINU (COQ) on avalanche @ 0x420FcA0121DC28039145009570975747295f2329
Market:    price $0.00000009074, liq $477,147, fdv $6,298,001, age 1015.1d, vol24h $17,217

VERDICT:   CAUTION
  - Jev exit_liquidity 0.58 below 1.0
```

That verdict is honest: COQ is an established meme coin with a renounced contract and
zero taxes, but $477k of liquidity is still a thin door if you're moving size, and the
model split its judgment between "deep" and "moderate" liquidity (0.5 / 0.42). The
tool reports the split instead of pretending certainty.

---

## The idea: split the job between code and judgment

Screening a token has two very different halves.

**Half one is exact.** Is the contract a honeypot? What's the sell tax? Did the owner
renounce? How old is the pool, how deep is the liquidity? These come back as booleans
and numbers from [GoPlus Security](https://gopluslabs.io) and
[DexScreener](https://dexscreener.com), and plain `if` statements handle them better
than any model: they're free, instant, and never wrong about a fact they were given.

**Half two is fuzzy.** Does the token's own marketing match its on-chain reality? Is
the community organic or astroturfed? Could you actually exit this position, or would
your sell be the exit liquidity? You can't regex "the website promises CEX listings
but the pool is nine hours old". That gap, between what code can match exactly and
what a human reads in five seconds, is where rug losses live.

This tool sends the fuzzy half to Jev and keeps the exact half in code.

## What Jev is (the short version)

Jev is a [System One](https://docs.typesafe.ai) model from TypeSafe. The mental model
that stuck: **it's a match statement where the case labels are natural language.**

Code can `match` on values it can enumerate. The moment the input is *"the next 100x
Avalanche gem, audited, CEX listings incoming!"* and the arms are *hype / honest /
hostile*, a match statement can't help. Jev evaluates those fuzzy arms and returns
calibrated probabilities, never prose, never a value outside the set you defined.

It has three question types, and this tool uses all of them in a single request:

| Type | Answers | Returns | Used here as |
|---|---|---|---|
| **Noul** | yes/no | P(yes), 0–1 | "does the narrative overstate the chain facts?" |
| **Choice** | one of a set you define | full probability distribution | "which risk class fits?" |
| **Score** | position on levels you describe | weighted position + per-level probabilities | "how safe is the exit?" |

Two properties make it composable into real software: answers are constrained to the
options you supplied (a Choice over three risk classes returns exactly those three
probabilities, summing to 1), and probabilities are the interface (0.55 means
genuinely 55/45, and *your code* decides what that's worth, which is the whole
philosophy: the model judges, code decides).

## How the screening works

Four stages, one file, one Jev call:

1. **Resolve**  address, or symbol → best pair on your chain via DexScreener search
2. **Fetch**  keyless GETs: DexScreener (market, pool age, socials, profile text)
   and GoPlus (honeypot, taxes, mint authority, LP lock, holders)
3. **Judge**  one Jev request over the combined state, three questions in parallel
4. **Decide**  a two-layer policy in plain Python

The three questions sent to Jev (`rugcheck.py`, `QUESTIONS`):

- `risk_class`  Choice: `low_risk` / `speculative` / `red_flags`
- `narrative_vs_chain`  Noul: does the token's own marketing overstate what the
  on-chain facts support? (shill detector)
- `exit_liquidity`  Score over four concrete levels: from "a $10k exit barely moves
  the price" to "any sell crashes the price"

The policy layers (`rugcheck.py`, the constants block):

**Hard fails**  structured facts only, no model involved, any one means AVOID:

| Check | Threshold |
|---|---|
| GoPlus honeypot flag | any |
| Buy/sell tax | > 10% |
| Closed source contract |, |
| Mintable + owner not renounced | both |
| Pool liquidity | < $30k |
| Pair age | < 3 days |

**Jev layer**  for tokens that survive the hard fails:

- `risk_class = red_flags` → AVOID
- `speculative` + narrative overstatement ≥ 0.7 → CAUTION
- `exit_liquidity < 1.0` → CAUTION
- `risk_class` confidence < 0.4 → appended "consider manual review" note

### The policy is yours, and re-running it is free

Every threshold above is a constant. Change one, then:

```bash
python3 rugcheck.py --replay
```

`--replay` re-applies policy to the cached response with **zero API calls**. During
testing I flipped the exit-liquidity threshold and watched the COQ verdict move
CAUTION → PASS without touching the network. The judgment is reusable data; the
decision is code. Edit the decision as often as you like.

## Chains

22 EVM chains via `--list-chains`: Avalanche, Ethereum, BSC, Base, Arbitrum,
Optimism, Polygon, Fantom, Linea, zkSync, Blast, Scroll, Mantle, Cronos, Gnosis,
Moonbeam, Moonriver, Metis, Kava, Canto, Harmony, Aurora. GoPlus is EVM-only; on a
chain it doesn't cover, the hard-fail layer degrades with a visible warning and the
verdict rests on market facts plus Jev.

## Field notes

Two things the live testing taught, kept here because they'll bite anyone building
on public token APIs:

**Forked chains share addresses.** The first cross-chain test (`--chain eth`, USDT)
silently resolved to the *PulseChain fork* of USDT trading at $0.0009, and mixed
PulseChain market data with Ethereum security data. The fix: resolve through the
chain-scoped DexScreener endpoint and refuse to fall back across chains, ever. If
you build on `/latest/dex/tokens/{addr}`, check what chain you're actually reading.

**Correct rules can still misfire.** USDT itself gets an AVOID here, its owner can
mint and hasn't renounced, which is exactly the rug signature the hard-fail layer
looks for. For centrally-issued tokens that's legitimate operation, not malice.
The rule is right for the tokens this tool targets; if you screen established
issuers, whitelist them in the policy layer. Notably, Jev itself hedged on that run
(low_risk 0.6 / red_flags 0.37) it noticed the facts were rug-shaped even though
the classification was borderline.

## The other example: same pattern, different domain

[`examples/bug_triage.py`](examples/bug_triage.py) is a small bug-report triage tool
built the same way: one Jev call, three parallel questions (release-blocker Noul,
component-routing Choice, severity Score), and an ESCALATE / ROUTE / QUEUE verdict
computed from thresholds in code. It's included to show the pattern is the point
swap the domain and the shape holds.

## Limitations, stated plainly

- A PASS filters obvious rugs. It does not make a token a good investment, and it
  can't see anything your data sources don't (dev wallets spread across wallets,
  off-chain deals, market makers pulling quotes).
- DexScreener coverage is DEX-only; tokens whose liquidity lives on CEXs or
 Curve-style pools can look thinner than they are.
- Jev's probabilities are calibrated judgment, not omniscience. The confidence
  floors exist so weak answers ask for a human instead of acting alone.
- This is not financial advice. It's a filter that costs pennies to run.

## Requirements

- Python 3.10+ (stdlib only `urllib`, `json`, `argparse`)
- A TypeSafe API key: sign up at [docs.typesafe.ai](https://docs.typesafe.ai), then

```bash
export TYPESAFE_API_KEY="ts-..."
```

Each run makes 3–4 free data GETs and exactly one Jev call (~1k input tokens,
~83 output). 429/529 from the Jev API gets one backed-off retry.

## License

[MIT](LICENSE)
