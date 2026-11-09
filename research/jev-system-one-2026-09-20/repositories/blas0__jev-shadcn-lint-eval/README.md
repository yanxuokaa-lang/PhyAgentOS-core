# jev-shadcn-lint-eval

This checks [shadcn-ui/lint](https://github.com/shadcn-ui/lint) (commit `53de86f`)
with TypeSafe's Jev model (`jev-latest`). The repo's own eval measures how agents
style UI before and after lint feedback. This one asks Jev whether each lint
result is right and whether its message tells you what to change.

## What's here

- `design-system.json`: the source of truth for what Jev is told about each
  project: the real color tokens, component files and their variants for five
  shadcn-ui/lint fixtures. `extract-design-system.mjs` regenerates it.
- `rules.json`: the six rules, what each one reports, and how to fix it.
- `questions.json`: the questions sent to Jev, grouped by what they judge
  (a single finding, a test case, or a whole agent task).
- `rule-cases.jsonl`: 131 rule test cases (79 should be reported, 52 shouldn't).
- `run-rule-cases.mjs`: runs the real linter on each case, asks Jev, and saves
  `records.json` (every answer) and `summary.json` (the scores) under `results/`.
- `build-states.mjs`: turns an agent run into states for Jev (sample:
  `state.example.json`). Tested once on a made-up run; not sent to Jev yet.
- `LICENSE`: MIT. The test cases and fixture data come from shadcn-ui/lint,
  also MIT; its notice is included.

## Running it

You need a checkout of shadcn-ui/lint with `pnpm install` and `pnpm build` done.
To rebuild `rule-cases.jsonl`, temporarily change `createTester()` in
`packages/lint/test/helpers.ts` to write each test case to a file, then run the
six rule test files. Then:

```bash
node extract-design-system.mjs --repo <lint checkout>   # only when the lint repo changes
export TYPESAFE_API_KEY=...                             # never commit it
node run-rule-cases.mjs rule-cases.jsonl --repo <lint checkout> [--limit n]
```

## Test results (2026-09-17)

One run, against the lint repo's real components and theme colors. Details are
in `results/rule-cases-2026-09-17T07-42-43-159Z/`.

**Does the code break the rule?** Jev caught 91% of real violations. It was
weaker on clean code and flagged 16 of 52 clean cases. Overall it answered 82%
of the 131 cases correctly (counting a probability of 0.7 or more as "yes").
The clean cases it got wrong mostly used things a rule deliberately ignores,
like `bg-[#333]` under `no-raw-colors`. `rules.json` doesn't tell Jev about
those yet.

**Does the message say what to change?** Jev scored the linter's 115 messages
from 0 (no help) to 2 (names the exact variant, color, or file). They averaged
1.41. The weakest were messages like "its contract denies flex", which say
what's wrong but not what to use instead.

The run made 246 requests with no errors and used 249,384 input tokens (Jev
bills input tokens only). Two earlier runs without component data scored 79%
and 82%, so adding the components didn't clearly change accuracy.

## Next steps

- Tell Jev what each rule ignores (in `rules.json`), then rerun.
- Send `build-states.mjs` output from a real agent run to Jev, and compare its
  answers with the lint repo's own outcome labels.
