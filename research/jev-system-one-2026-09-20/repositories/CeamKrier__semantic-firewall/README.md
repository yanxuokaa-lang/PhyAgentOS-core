# Semantic Firewall for LLM Agents with TypeSafe Jev

Gate an AI agent's tool calls with **Jev**, TypeSafe's System One decision
model, served through OpenRouter (`typesafe/jev-1.13`,
`POST /api/alpha/decisions`). The generative LLM proposes one action. Jev
answers five yes/no questions about it with calibrated probabilities. Plain
code turns those numbers into `ALLOW / ASK_USER / REVISE / BLOCK` and says
which rule fired.

```text
LLM   = proposal engine
Jev   = semantic control plane   "what is true about this state?"
Code  = authority                "given that, what is allowed?"
```

Nothing is executed. Tools are mocks. 585 lines of TypeScript, zero runtime
dependencies.

## Architecture

```text
user request
  → generator LLM        src/generator.ts   one action as JSON, schema-validated
  → Jev, 5 noul checks   src/jev.ts         goalAlignment, authorization, sideEffect,
                                            untrustedInstruction, evidenceSufficient
  → deterministic policy src/policy.ts      thresholds in one object, rules in order
  → decision + triggered rules
```

Jev never returns a decision. `untrustedInstruction` is skipped by code when
there is no untrusted content.

## Run

```bash
npm install
cp .env.example .env                    # OPENROUTER_API_KEY
npm run dev                             # interactive
npm run eval                            # 30 fixture cases through Jev + policy
npm run eval -- --runs 5 --baseline     # stability + direct-LLM baseline
npm run eval -- --e2e --baseline        # live generator proposals
npm test                                # policy rules, no network
```

Flags: `--runs N`, `--e2e`, `--baseline`, `--case ID`, `--tag TAG`, `--debug`.
Raw records go to `results/`. Models are set in `.env`
(`GENERATOR_MODEL`, `JEV_MODEL`).

## Results

30 cases, 5 runs each, fixture proposals. Full write-up with six failures:
[`REPORT.md`](REPORT.md).

```text
                     Jev + policy      gpt-4.1-mini as policy
exact accuracy       140/150           114/150
false allows         0                 10
decision flips       0/30 cases        4/30 cases
predicate sd         <= 0.021          n/a
latency p50          345 ms            840 ms
cost per call        $0.000032         $0.000102
```

The accuracy gap is mostly labelling taxonomy. The false-allow, stability and
cost differences are the result. Not yet tested: adversarial `reason` text from
the generator, which moved one predicate across a threshold in the end-to-end
run. That is the next experiment.

## Limitation

Not a security product. Jev is probabilistic and can be wrong. It sits on top
of hard authorization, tenant isolation, schema validation and permission
checks, never in place of them.

## Links

- Jev on OpenRouter: <https://openrouter.ai/typesafe/jev-1.13>
- System One API: <https://docs.typesafe.ai/api>
- Jev 1.13 jagged edges: <https://docs.typesafe.ai/model-jaggedness/jev-1.13>
