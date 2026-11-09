# JEV Domain Scout

[![CI](https://github.com/catorch/jev-domain-auctions/actions/workflows/ci.yml/badge.svg)](https://github.com/catorch/jev-domain-auctions/actions/workflows/ci.yml)

A read-only acquisition research pipeline for GoDaddy Auctions expiry inventory. It streams the public inventory feed, applies cheap deterministic filters, asks TypeSafe's JEV model for narrow semantic judgments, and optionally re-checks the finalists against GoDaddy's live Auctions API.

This is a ranking tool, not a valuation guarantee. Automated appraisals, backlink counts, and model judgments can all be wrong. Every candidate remains a manual-review item, especially for trademark, backlink-spam, language, and legal risk.

## How it works

1. Download and stream a GoDaddy JSON inventory ZIP without expanding it to disk.
2. Reject adult listings, prices over budget, unwanted TLDs, long names, and malformed names.
3. Rank the remainder with observed signals: price/appraisal gap, search and CPC demand, registered/developed TLDs, SEO authority, age-independent name structure, and TLD quality.
4. Send only the top pre-filtered names to JEV. One request per name evaluates brandability, commercial utility, linguistic clarity, and semantic cleanliness in parallel.
5. Combine the reusable deterministic and semantic dimensions in code, then optionally verify availability and current micro-unit pricing through GoDaddy.
6. Write auditable JSON and CSV reports. Results below the configured JEV confidence are marked for review rather than silently discarded.

## Setup

Requires Node.js 22.12 or newer.

```bash
npm install
cp .env.example .env
```

Fill in `TYPESAFE_API_KEY` in `.env`. To use live verification, add a production Classic Developer Key and secret as `GODADDY_API_KEY` and `GODADDY_API_SECRET`. A Personal Access Token will not work with the Auctions API. Keep `GODADDY_CUSTOMER_ID=MY` unless you have retrieved the account's customer UUID.

## Run

Try the deterministic path against the synthetic fixture without credentials:

```bash
npm run scan -- --input examples/sample-inventory.json --no-jev
```

Scan the current closeout feed with JEV:

```bash
npm run scan -- --feed closeout_listings.json.zip --max-price 500 --prefilter 40 --top 20
```

Verify the final shortlist against GoDaddy after ranking:

```bash
npm run scan -- --feed closeout_listings.json.zip --max-price 500 --prefilter 40 --top 20 --verify
```

Use `--limit 10000` while tuning. Other useful controls are `--tlds com,ai,io`, `--max-length 15`, `--min-jev-confidence 0.6`, and `--output reports`.

Require a Semrush Authority Score above 5 while staying below $50:

```bash
npm run scan -- --max-price 49.99 --min-authority-score 5 --prefilter 40 --top 20 --verify
```

## Safety and calibration

- There is deliberately no bid or purchase endpoint in this project.
- With `--verify`, credentials are checked before inventory processing or JEV calls.
- Live verification is read-only and batches up to 50 domains, matching GoDaddy's limit.
- JEV results are cached by domain and feed price to control cost during repeated experiments.
- Tune weights and thresholds on recorded outcomes, not intuition alone. The best next step is to label at least 100 historical wins, rejects, and false positives, then measure precision among the top 10/20.
- Run trademark screening and manually inspect backlink provenance before bidding. "Clean semantics" is not trademark clearance.

## References

- [GoDaddy expiry API announcement](https://www.godaddy.com/resources/news/godaddy-auctions-expiry-apis-automate-domain-acquisition)
- [GoDaddy Auctions API overview](https://developer.godaddy.com/en/docs/api-users/auctions)
- [GoDaddy listing availability](https://developer.godaddy.com/en/docs/references/rest/auctions/listings-availability)
- [TypeSafe JavaScript SDK](https://docs.typesafe.ai/sdk/javascript)
- [TypeSafe composite scoring](https://docs.typesafe.ai/patterns/composite-scoring)

## Contributing

Issues and focused pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a change.

## License

MIT
