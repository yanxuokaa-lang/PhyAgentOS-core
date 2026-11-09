# jev

A Claude Code plugin that wraps [TypeSafe's Jev](https://openrouter.ai/typesafe).
You ask in plain language, Claude turns it into typed questions, and you get a
typed answer with a probability.

```
> /jev:ask is this diff risky to ship on a Friday?

has_migration    noul    0.98
is_reversible    noul    0.13
risk             score   1.94 / 2   confidence 0.90
```

Jev doesn't generate text. It takes state plus named, typed questions and
returns one typed answer each. Good for classification, routing, triage, scoring
and yes/no calls. Useless for anything you'd ask a chat model.

Worth knowing before you read an answer: a noul of 0.5 means *cannot tell*, not
"moderately true". A confidence near zero means Jev can't tell either way, and
the plugin labels those. Output tokens are free, so seven narrow questions about
one ticket cost about what one costs.

## Install

```
/plugin marketplace add sebastianbugal/jev
/plugin install jev
```

It prompts for an OpenRouter API key on enable. Get one at
<https://openrouter.ai/keys>; no TypeSafe waitlist needed. The key goes to your
OS keychain. Needs Node 18+.

Check it works with `/jev:check`, which costs about a hundredth of a cent.

## What leaves your machine

Asking Jev about your code sends that code to a third party. Claude puts
whatever the question depends on into the request, and it goes to OpenRouter's
Decisions endpoint, served by TypeSafe. Both have their own retention terms.

The plugin talks to that one endpoint and nothing else, writes nothing except a
credentials file you create yourself, and never executes what it gets back.

If your work is under terms that forbid third-party inference, don't install it.

## Details

The three question types, how to read the distributions, and the batching rules
are in the [plugin README](./jev/README.md). The API contract, verified against
the live endpoint, is in [reference/decisions-api.md](./jev/reference/decisions-api.md).

The server is plain Node with no dependencies. `cd jev && npm test` runs 58
offline tests.

MIT. Not affiliated with TypeSafe or OpenRouter.
