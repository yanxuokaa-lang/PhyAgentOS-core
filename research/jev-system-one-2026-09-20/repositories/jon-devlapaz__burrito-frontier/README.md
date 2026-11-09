# burrito-frontier

Location-agnostic Grok / agent skill: Pareto-optimal menu picks on **cost**, **macros**, **deliciousness**, and **reviews** for **any** restaurant.

Pass a menu + restaurant name/area at run time. The skill does **not** hardcode cities, chains, or house dishes.

## Install

Copy [`SKILL.md`](./SKILL.md) into your agent skills folder as `burrito-frontier/SKILL.md`, or import into Grok Bot.

Needs a TypeSafe API key for Jev deliciousness Scores.

## Usage

1. Menu (photo / PDF / link / paste)
2. Restaurant name + location (for prices/reviews)
3. Optional: constraints, weights, `named_builds`, `serving_mode`

## Design notes

- Jev scores deliciousness only; macros/cost stay in code
- Named builds for BYO, multi-item counter meals, and by-the-pound service
- Shareable/dip gates and solo-diner adequacy rules
- Top-k-first output with confidence-aware picks

Dogfood history (where patches were validated) lives in [CHANGELOG.md](./CHANGELOG.md) only.

## License

MIT
