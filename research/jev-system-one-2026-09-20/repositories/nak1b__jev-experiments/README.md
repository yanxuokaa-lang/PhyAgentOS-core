# jev-experiments

Small experiments with Jev, each in its own folder.

## Jev and TypeSafe

[TypeSafe](https://typesafe.ai) builds System One models: models that make fast, structured decisions instead of writing text.
Jev is their first one.
You send it some text and a set of typed questions, and it answers each one with probabilities and a confidence.
A Choice picks one option from a list, a Score rates against a scale, and a Noul answers yes or no as a probability.
Jev answers in well under a second, and only input tokens are billed.
Read more in the [TypeSafe docs](https://docs.typesafe.ai/introduction).

## Experiments

| Experiment | What it tries | Stack | Run from the root |
| --- | --- | --- | --- |
| [flight-search](flight-search/README.md) | Turns a trip described in plain words into a live flight search, and shows the cost, tokens and speed of every Jev call. | Next.js, TypeScript, Tailwind | `npm run dev:flight-search` |

## Setup

1. Run `npm install` at the root. It installs every experiment and the git hooks.
2. Create your local env file with `cp .env.example .env.local`.
3. Paste your key from the [TypeSafe console](https://console.typesafe.ai/settings/keys) into `.env.local`.
4. Keep the file private with `chmod 600 .env.local`.
5. Start an experiment with the command in the table.

Every experiment reads the key from this one root `.env.local`.
It is gitignored, and a pre-commit hook blocks any commit that contains it.

## Checks

Run `npm run lint`, `npm run typecheck` and `npm test` at the root to check every experiment at once.

## Adding an experiment

Create a folder at the root, add it to `workspaces` and add a `dev:<name>` script in the root `package.json`.
Give it a README that explains how it works and how it uses Jev, then add it to the table above.
