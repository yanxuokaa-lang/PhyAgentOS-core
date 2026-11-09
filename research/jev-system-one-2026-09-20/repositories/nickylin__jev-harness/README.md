# jev-harness

Typed decision control plane for agents, powered by [TypeSafe AI's Jev](https://typesafe.ai).

Supports multiple Jev backends:
- **TypeSafe Official** — Direct API at `api.typesafe.ai`
- **Vercel AI Gateway** — Via Vercel's AI SDK gateway

![Architecture overview](docs/architecture.png)

## Why jev-harness?

Agent frameworks often struggle with structured decision-making. Raw LLM JSON output is unpredictable—schemas drift, confidence scores vary, and routing logic scatters across prompts. **jev-harness** solves this by:

- **Typed questions**: Define exactly what you need answered (boolean, choice, score, text)
- **Typed decisions**: Get back `allow`, `deny`, `defer`, or `route` with confidence scores and metadata
- **Policy-driven**: Bundle questions + decision logic into reusable, testable policies
- **Multi-provider**: Choose TypeSafe official or Vercel AI Gateway with automatic detection
- **Mock-friendly**: Swap in `createMockEvaluate()` for deterministic unit tests—no API calls needed

## Installation

```bash
npm install jev-harness
# or
pnpm add jev-harness
```

**Peer dependency:** Requires `ai >= 3.0.0` for AI Gateway integration.

## Quick Start

### Provider Setup

jev-harness auto-detects your provider based on environment variables:

```bash
# Option 1: TypeSafe Official (preferred)
export TYPESAFE_API_KEY=your-typesafe-api-key

# Option 2: Vercel AI Gateway
export AI_GATEWAY_API_KEY=your-vercel-gateway-key
```

If both are set, TypeSafe Official takes priority.

### Minimal Example

```typescript
import { createHarness, storeReviewTriage } from 'jev-harness';

const harness = createHarness(); // auto-detects provider
harness.register(storeReviewTriage);

const decision = await harness.evaluate(
  { text: "Love the app but it crashes on startup", stars: 4 },
  'store-review-triage'
);

console.log(decision.action);     // 'route'
console.log(decision.route);      // 'bug_ack'
console.log(decision.confidence); // 0.9
```

### Explicit Provider Selection

```typescript
// Force TypeSafe Official
const harness = createHarness({ provider: 'typesafe' });

// Force Vercel AI Gateway
const harness = createHarness({ provider: 'vercel-gateway' });

// Auto-detect (default)
const harness = createHarness({ provider: 'auto' });
```

## Provider Comparison

| Feature | TypeSafe Official | Vercel AI Gateway |
|---------|-------------------|-------------------|
| Endpoint | `POST https://api.typesafe.ai/v1/systemone` | `POST https://api.vercel.ai/v1/chat/completions` |
| Model | `jev-latest` | `typesafe-ai/jev` |
| Auth Env Var | `TYPESAFE_API_KEY` | `AI_GATEWAY_API_KEY` |
| Question Types | `noul`, `choice`, `score` | `boolean`, `choice`, `score`, `text` |
| Boolean Responses | Probability 0-1 (normalized to boolean) | Direct boolean |

### Question Type Mapping

The library uses `boolean` in its API. When using TypeSafe Official, this is automatically mapped to `noul` (probability-based) and normalized back:

```typescript
// You write:
booleanQuestion('is_spam', 'Is this spam?')

// TypeSafe Official receives:
{ type: 'noul', key: 'is_spam', prompt: 'Is this spam?' }

// TypeSafe returns:
{ is_spam: { probability: 0.87 } }

// You receive (normalized):
{ is_spam: true, is_spam_probability: 0.87 }
```

The raw probability is available as `${key}_probability` for advanced use cases.

## Environment Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `TYPESAFE_API_KEY` | TypeSafe Official | API key from [typesafe.ai](https://typesafe.ai) |
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway | API key from Vercel AI Gateway |

### `.env.example`

```bash
# TypeSafe Official (preferred)
TYPESAFE_API_KEY=your-typesafe-api-key

# Vercel AI Gateway (alternative)
AI_GATEWAY_API_KEY=your-vercel-gateway-key
```

## Testing with curl

### TypeSafe Official

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -d '{
    "model": "jev-latest",
    "state": { "text": "Great app!", "stars": 5 },
    "questions": [
      { "type": "noul", "key": "is_positive", "prompt": "Is the sentiment positive?" },
      { "type": "choice", "key": "sentiment", "prompt": "Overall sentiment?", "choices": ["positive", "neutral", "negative"] }
    ]
  }'
```

### Vercel AI Gateway

```bash
curl -X POST https://api.vercel.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_GATEWAY_API_KEY" \
  -d '{
    "model": "typesafe-ai/jev",
    "messages": [
      { "role": "system", "content": "You are a precise evaluation assistant. Always respond with valid JSON only." },
      { "role": "user", "content": "Given {\"text\": \"Great app!\", \"stars\": 5}, is the sentiment positive? Answer as JSON: {\"is_positive\": true/false}" }
    ],
    "temperature": 0,
    "response_format": { "type": "json_object" }
  }'
```

## Store Review Triage Policy

![Store review triage flow](docs/usage-store-review-triage.png)

Triage app store reviews into response queues with the built-in `storeReviewTriage` policy:

```typescript
import { createHarness, storeReviewTriage, createMockEvaluate } from 'jev-harness';

const harness = createHarness();
harness.register(storeReviewTriage);

const decision = await harness.evaluate(
  {
    text: "Love the app but it crashes on startup",
    stars: 4,
  },
  'store-review-triage'
);

console.log(decision.action);     // 'route'
console.log(decision.route);      // 'bug_ack'
console.log(decision.confidence); // 0.9
console.log(decision.meta);       // { sentiment: 'negative', hasActionableFeedback: true, originalStars: 4 }
```

### Store Review Triage Routes

| Route | When Matched | Suggested Action |
|-------|--------------|------------------|
| `thanks` | Positive reviews with genuine praise | Send thank-you response |
| `bug_ack` | Bug reports or technical issues | Acknowledge and create ticket |
| `feature_note` | Feature requests or suggestions | Log for product review |
| `skip` | Spam, gibberish, or irrelevant content | No response needed |
| `defer_human` | Billing disputes, legal threats, complex issues | Escalate to human support |

## Defining Custom Policies

Create policies using the fluent `definePolicy()` builder or the inline `createPolicy()` function:

```typescript
import {
  definePolicy,
  booleanQuestion,
  choiceQuestion,
  scoreQuestion,
  allow,
  deny,
  route,
} from 'jev-harness';

const contentModerationPolicy = definePolicy('content-moderation')
  .description('Moderate user-generated content')
  .question(booleanQuestion('is_spam', 'Is this content spam or promotional?'))
  .question(booleanQuestion('is_harmful', 'Does this contain harmful or abusive content?'))
  .question(choiceQuestion('category', 'Content category?', ['discussion', 'question', 'announcement', 'other']))
  .question(scoreQuestion('quality', 'Content quality score', { min: 0, max: 1 }))
  .decide((answers, state) => {
    if (answers.is_harmful) {
      return deny(answers, { confidence: 0.95 });
    }
    if (answers.is_spam) {
      return deny(answers, { confidence: 0.8 });
    }
    if (answers.quality < 0.3) {
      return route(answers, 'review-queue', { confidence: 0.7 });
    }
    return allow(answers, { confidence: answers.quality });
  })
  .build();

// Or use createPolicy() for simpler inline definitions
import { createPolicy } from 'jev-harness';

const simplePolicy = createPolicy({
  name: 'approval-gate',
  questions: [booleanQuestion('approved', 'Should this be approved?')],
  decide: (answers) => answers.approved ? allow(answers) : deny(answers),
});
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Your Agent / App                         │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ state
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                           jev-harness                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │   Harness   │───▶│   Policy    │───▶│  Typed Questions    │   │
│  │  .evaluate()│    │  .decide()  │    │  boolean/choice/... │   │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   │ provider-specific request
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Provider Abstraction                        │
│  ┌─────────────────────┐    ┌───────────────────────────────┐    │
│  │  TypeSafe Official  │    │     Vercel AI Gateway         │    │
│  │  api.typesafe.ai    │    │     api.vercel.ai             │    │
│  │  model: jev-latest  │    │     model: typesafe-ai/jev    │    │
│  └─────────────────────┘    └───────────────────────────────┘    │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   │ normalized answers
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Decision                                 │
│        { action, route?, confidence, answers, meta? }            │
│                 allow | deny | defer | route                     │
└──────────────────────────────────────────────────────────────────┘
```

## Testing with Mocks

Replace the AI evaluator with deterministic mocks for unit testing:

```typescript
import { createHarness, createMockEvaluate, createFixtureEvaluate, storeReviewTriage } from 'jev-harness';

// Option 1: Static mock answers
const mockEvaluate = createMockEvaluate({
  sentiment: 'positive',
  is_bug_report: false,
  is_feature_request: false,
  contains_praise: true,
  needs_human: false,
  response_priority: 0.8,
  is_spam_or_irrelevant: false,
});

const harness = createHarness({ evaluateFn: mockEvaluate });
harness.register(storeReviewTriage);

const decision = await harness.evaluate(
  { text: 'Great app!', stars: 5 },
  'store-review-triage'
);
expect(decision.route).toBe('thanks');

// Option 2: Fixture-based answers (different answers per input state)
const fixtureEvaluate = createFixtureEvaluate({
  '{"text":"bug here","stars":2}': {
    sentiment: 'negative',
    is_bug_report: true,
    is_feature_request: false,
    contains_praise: false,
    needs_human: false,
    response_priority: 0.9,
    is_spam_or_irrelevant: false,
  },
});

const fixtureHarness = createHarness({ evaluateFn: fixtureEvaluate });
fixtureHarness.register(storeReviewTriage);

// Option 3: Swap evaluator on existing harness
const testHarness = harness.withEvaluate(createMockEvaluate({ is_spam_or_irrelevant: true }));

// Option 4: Mock TypeSafe noul responses with probabilities
import { createTypeSafeMockEvaluate } from 'jev-harness';

const noulMock = createTypeSafeMockEvaluate({
  is_spam: { probability: 0.2 },      // false (< 0.5)
  is_harmful: { probability: 0.9 },   // true (>= 0.5)
  category: 'discussion',
  quality: 0.85,
});
```

## API Reference

### Harness

```typescript
import { createHarness, Harness } from 'jev-harness';

// Create with factory function (recommended)
const harness = createHarness(config?: HarnessConfig);

// Or use constructor directly
const harness = new Harness(config?: HarnessConfig);

// HarnessConfig options
interface HarnessConfig {
  provider?: 'typesafe' | 'vercel-gateway' | 'auto';  // Default: 'auto'
  model?: string;           // Provider-specific default
  apiKey?: string;          // Provider-specific env var default
  baseURL?: string;         // Provider-specific default
  evaluateFn?: EvaluateFunction;  // Custom evaluator for testing
}

// Methods
harness.register(policy);              // Register a policy
harness.registerAll([policy1, ...]);   // Register multiple policies
harness.getPolicy(name);               // Get policy by name
harness.listPolicies();                // List registered policy names
harness.evaluate(state, policyName);   // Evaluate state against policy
harness.evaluateAll(state, names?);    // Evaluate against multiple policies
harness.withEvaluate(fn);              // Clone with custom evaluator
harness.withProvider(provider);        // Clone with different provider
harness.getProviderType();             // Get current provider type
```

### Provider Utilities

```typescript
import {
  detectProvider,
  resolveProviderConfig,
  createProvider,
  getProviderInfo,
} from 'jev-harness';

// Auto-detect provider from environment
const detected = detectProvider();
// { provider: 'typesafe', apiKey: '...' } or null

// Resolve full config with defaults
const config = resolveProviderConfig({ provider: 'auto' });
// { provider: 'typesafe', apiKey: '...', baseURL: '...', model: '...' }

// Get provider info for diagnostics
const info = getProviderInfo();
// { provider: 'typesafe', baseURL: '...', model: '...', envVar: 'TYPESAFE_API_KEY' }
```

### Question Helpers

```typescript
import {
  booleanQuestion,
  choiceQuestion,
  scoreQuestion,
  textQuestion,
} from 'jev-harness';

booleanQuestion('key', 'Prompt?');                           // Yes/no
choiceQuestion('key', 'Which one?', ['a', 'b', 'c']);       // Multiple choice
scoreQuestion('key', 'Rate 0-1', { min: 0, max: 1 });       // Numeric score
textQuestion('key', 'Describe...');                          // Free text
```

### Answer Accessors

```typescript
import { getBoolean, getChoice, getScore, getText, meetsThreshold } from 'jev-harness';

const flag = getBoolean(answers, 'is_valid');        // boolean (default: false)
const category = getChoice(answers, 'category');     // string | undefined
const score = getScore(answers, 'confidence');       // number (default: 0)
const desc = getText(answers, 'description');        // string (default: '')
const passes = meetsThreshold(answers, 'score', 0.7); // boolean

// Access raw probability from TypeSafe noul responses
const prob = getScore(answers, 'is_spam_probability'); // 0-1
```

### Decision Builders

```typescript
import { allow, deny, defer, route, decide } from 'jev-harness';

// Simple decisions
allow(answers, { confidence: 0.9, meta: { reason: 'valid' } });
deny(answers, { confidence: 0.8 });
defer(answers);  // Escalate to human
route(answers, 'target-queue', { confidence: 0.85 });

// Fluent builder
decide(answers)
  .routeTo('review-queue')
  .confidence(0.75)
  .meta({ flagged: true })
  .build();
```

### Types

```typescript
import type {
  Decision,
  DecisionAction,      // 'allow' | 'deny' | 'defer' | 'route'
  Policy,
  Question,
  BooleanQuestion,
  ChoiceQuestion,
  ScoreQuestion,
  TextQuestion,
  Answers,
  HarnessConfig,
  EvaluationContext,
  EvaluateFunction,
  ProviderType,        // 'typesafe' | 'vercel-gateway' | 'auto'
  ProviderConfig,
  ResolvedProviderConfig,
  JevProvider,
} from 'jev-harness';

// Built-in policy types
import type {
  StoreReviewState,
  StoreReviewRoute,
  StoreReviewMeta,
} from 'jev-harness';
```

### Zod Schemas

For runtime validation:

```typescript
import {
  DecisionSchema,
  PolicySchema,
  QuestionSchema,
  BooleanQuestionSchema,
  ChoiceQuestionSchema,
  ScoreQuestionSchema,
  TextQuestionSchema,
} from 'jev-harness';
```

## CLI Example

Run the included example to see store review triage in action:

```bash
# With mock evaluator (no API key needed)
pnpm example

# With live Jev API (uses auto-detected provider)
TYPESAFE_API_KEY=your-key pnpm example --live
# or
AI_GATEWAY_API_KEY=your-key pnpm example --live

# Evaluate a custom review
pnpm example --review "This app is amazing but needs dark mode"
```

## Future Providers

The provider abstraction is designed to support additional backends. Potential future providers:

- **Cloudflare Workers AI** — `typesafe/jev` model (not yet implemented)

To add a new provider, implement the `JevProvider` interface and add it to the provider factory.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT
