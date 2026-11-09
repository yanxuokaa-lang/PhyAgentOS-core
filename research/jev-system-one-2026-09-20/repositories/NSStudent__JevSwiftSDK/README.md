# JevSwiftSDK

A dependency-free Swift package for [TypeSafe's Jev](https://docs.typesafe.ai/models), a remote decision model that returns typed judgments and probabilities.

**Independent, unofficial SDK.** This project is not affiliated with or endorsed by TypeSafe AI. It implements the [System One HTTP API](https://docs.typesafe.ai/api).

## Requirements

- Swift 6.0 or newer, with Swift 6 concurrency checking.
- iOS 15+, macOS 12+, or Linux with FoundationNetworking.
- A TypeSafe API credential for live service calls.

## Installation

For local development, add it as a local Swift package in Xcode, or use:

```swift
.package(path: "../JevSwiftSDK")
```

To install from GitHub, add this package dependency:

```swift
dependencies: [
    .package(url: "https://github.com/NSStudent/JevSwiftSDK.git", branch: "main")
],
targets: [
    .target(name: "YourApp", dependencies: [
        .product(name: "JevSwiftSDK", package: "JevSwiftSDK")
    ])
]
```

Use a version requirement once the repository has a release tag. The initial repository does not imply a published release.

## Quick start

This example belongs in a server or trusted command-line application. Supply the key explicitly, or opt into environment configuration as shown below.

```swift
import Foundation
import JevSwiftSDK

enum Department: String, Hashable, Sendable {
    case billing, technical, other
}

let configuration = try JevConfiguration(apiKey: serverProvidedAPIKey)
let client = JevClient(configuration: configuration)
let department = ChoiceQuestion<Department>(
    id: "department",
    instructions: "Which team should handle this ticket?",
    criteria: [
        .billing: "Payments, invoicing, and refunds",
        .technical: "Software bugs and outages",
        .other: "None of the listed teams"
    ]
)

let result = try await client.evaluate(
    state: "I was charged twice. Please help.",
    question: department
)
let team: Department = result.answer.choice
print(team, result.answer.confidence, result.answer.probabilities)
print(result.model, result.usage.inputTokens, result.usage.outputTokens)
```

### API key and environment configuration

Pass a credential directly when your application already manages it:

```swift
let configuration = try JevConfiguration(apiKey: serverProvidedAPIKey)
```

For servers and command-line tools, explicitly opt into reading the process environment:

```sh
export TYPESAFE_API_KEY='your-key'
# Optional:
export TYPESAFE_DEFAULT_MODEL='jev-latest'
export TYPESAFE_BASE_URL='https://api.typesafe.ai'
```

```swift
let client = JevClient(configuration: try .fromEnvironment())
```

`fromEnvironment()` reads `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, and `TYPESAFE_DEFAULT_MODEL`. Explicit arguments override environment values; blank environment values are ignored. Missing credentials or invalid configuration throw `JevError.configuration`. For deterministic tests, pass an environment dictionary:

```swift
let configuration = try JevConfiguration.fromEnvironment(
    ["TYPESAFE_API_KEY": "test-key"], model: "jev-latest"
)
```

The regular `JevConfiguration(apiKey:)` initializer remains independent of the environment. Neither API loads `.env` files. The SDK sends the credential in the `Authorization: Bearer …` header. For a distributed Apple app, use a backend as described in [Use from Apple applications](#use-from-apple-applications).

## Ask independent questions together

Each question evaluates the same state independently. Group questions in one request when they do not need each other's answers.

```swift
let urgent = NoulQuestion(
    id: "urgent",
    instructions: "Does the ticket explicitly request urgent action?"
)
let frustration = ScoreQuestion(
    id: "frustration",
    instructions: "How frustrated is the customer?",
    levels: ["Calm, no dissatisfaction", "Dissatisfied but polite", "Angry or threatening"]
)
let response = try await client.evaluate(
    state: ["ticket": "I was charged twice. Please fix this today."],
    questions: [
        department.eraseToAnyQuestion(),
        urgent.eraseToAnyQuestion(),
        frustration.eraseToAnyQuestion()
    ]
)
let team: Department = try response.answer(for: department).choice
let probabilityOfUrgency: Double = try response.answer(for: urgent).noul
let frustrationLevel: Double = try response.answer(for: frustration).score
```

`JevQuestion` associates each question with its response type. `AnyJevQuestion` erases the question type for heterogeneous batches. Missing answers, mismatched answer types, and invalid option mappings throw errors. The client checks every requested answer before returning a batch. Extra answer fields are tolerated, and original payloads are available in `response.answers`.

### Reusable batches with named answers

Use `JevQuestionSet` for a fixed group of questions and access results as properties:

```swift
struct TicketQuestions: JevQuestionSet {
    let department = ChoiceQuestion<Department>(
        id: "department", instructions: "Which team should handle this ticket?",
        criteria: [.billing: "Payments and refunds", .technical: "Software issues", .other: nil]
    )
    let urgent = NoulQuestion(id: "urgent", instructions: "Does the ticket request urgent action?")

    var questions: [AnyJevQuestion] {
        [department.eraseToAnyQuestion(), urgent.eraseToAnyQuestion()]
    }

    struct Answers: Decodable, Sendable {
        let department: ChoiceAnswer<Department>
        let urgent: NoulAnswer
    }
}

let result = try await client.evaluate(
    state: "I was charged twice. Please fix this today.",
    questions: TicketQuestions()
)
let team: Department = result.answers.department.choice
let urgency: Double = result.answers.urgent.noul
```

Answer property names must match the question IDs; use `CodingKeys` when they differ. The client validates **every** requested answer against its original question before decoding the `Answers` struct, even if that struct intentionally ignores some answers. Missing properties or incompatible answer types throw `JevError.invalidResponse`. `model` and `usage` remain available on the typed result. Existing dynamic batches continue to work unchanged.

### Understand the three primitives

| Primitive | Swift result | Meaning |
| --- | --- | --- |
| Choice | `ChoiceAnswer<YourEnum>` | Selected option, per-option probabilities, and confidence |
| Score | `ScoreAnswer` | Fractional position on zero-based ordered levels, probabilities, legend, and confidence |
| Noul | `NoulAnswer` | Probability of yes, from 0 to 1; no separate confidence |

A Noul near 0.5 is uncertain between yes and no. It does not mean medium intensity. Score is measured on the level indices: three levels yield a score from 0 to 2. Confidence summarizes a distribution; it is not a guarantee that an answer is correct. Choose any action thresholds in application code and evaluate them on your own data.

Choice supports 1–255 options; Score supports 2–10 levels, following the current documented limits. Option descriptions can be `.null` when the names are sufficient. Use `ChoiceOption` for runtime-defined string options:

```swift
let candidate = ChoiceQuestion<ChoiceOption>(
    id: "candidate", instructions: "Which candidate fits?",
    criteria: ["candidate-a": nil, "candidate-b": "A specialist in Swift"]
)
```

For enums conforming to `CaseIterable`, omit criteria to include every case with a null description:

```swift
enum Category: String, CaseIterable, Sendable {
    case billing, technical, other
}
let category = ChoiceQuestion<Category>(id: "category", instructions: "Which category fits?")
```

Explicit criteria still define exactly the options you provide; a subset is not expanded automatically. The existing option-count validation also applies to auto-generated criteria.

## Structured state and instructions

`JSONValue` is `Codable`, `Sendable`, and supports Swift literals. State must be a string, object, or array. Instructions and individual rubric entries also accept explicit JSON null. Nested values support booleans and numbers.

```swift
struct Ticket: Encodable, Sendable {
    let message: String
    let attempts: Int
}
let ticket = Ticket(message: "Export crashes", attempts: 3)
let verified = NoulQuestion(
    id: "verified",
    instructions: [
        "question": "Does `message` describe a reproducible software failure?",
        "focus": ["Specific failure", "Repeated attempts"]
    ],
    trueCriteria: ["definition": "Concrete behavior that failed", "examples": ["Export crashes"]],
    falseCriteria: "A feature request or vague dissatisfaction"
)
let result = try await client.evaluate(state: ticket, question: verified)
```

All evaluation forms accept `Encodable & Sendable` state directly. Its encoded root must still be a string, object, or array; scalar booleans, numbers, and null are rejected before sending. Direct encoding preserves Swift integer precision in the outgoing JSON, including `Int64` values above 2^53. Model interpretation of those values is a separate concern.

`JSONValue.number` uses `Double`; when constructing JSONValue manually, send identifiers or integers requiring more than 53 bits of precision as strings. Pass a configured `JSONEncoder` to `JSONValue.encoding(_:encoder:)` when you need custom date/key encoding, or implement `Encodable` on the state model. Score legends preserve JSON descriptions, including structured rubrics.

## Configuration, concurrency, and errors

```swift
let configuration = try JevConfiguration(
    apiKey: serverProvidedAPIKey,
    model: "jev-latest", // Or a specific supported model version.
    timeout: 10,
    retryPolicy: RetryPolicy(maxRetries: 2)
)
let client = JevClient(configuration: configuration)
let models = try await client.listModels()
```

The model can also be overridden per evaluation. `jev-latest` follows service updates; pin a version when reproducibility matters. The response retains the model reported by the service.

The immutable client is `Sendable` and can be shared across tasks. Task cancellation propagates as `CancellationError`, including while waiting to retry. Logging is off by default; when enabled, events contain operational metadata only.

`JevError` distinguishes configuration, request validation, HTTP failure, URL transport errors, malformed responses, missing answers, and answer-type mismatches. HTTP errors retain the response body and headers for explicit inspection; localized descriptions omit their contents.

```swift
do {
    let result = try await client.evaluate(state: "Help", question: urgent)
    print(result.answer.noul)
} catch is CancellationError {
    // The caller cancelled the operation.
} catch JevError.http(let statusCode, _, _) {
    // Handle authentication, validation, overload, or other service failures.
    print("Service returned HTTP", statusCode)
} catch {
    print(error.localizedDescription)
}
```

### Options for one request

```swift
let result = try await client.evaluate(
    state: ticket, question: urgent,
    options: RequestOptions(
        timeout: 3,
        retryPolicy: .disabled,
        headers: ["X-Correlation-ID": UUID().uuidString]
    )
)
let models = try await client.listModels(options: RequestOptions(timeout: 5))
```

Options apply only to that call and do not mutate the client. Omitted values use client settings. A supplied `retryPolicy` replaces the entire client retry policy; start from a copy of your policy to change a single field. Time intervals are in seconds.

Configure shared custom headers with `JevConfiguration(defaultHeaders:)`, together with the required API key. Per-call headers override them case-insensitively. The SDK owns `Authorization`, `Accept`, and `Content-Type`; URLSession owns routing and framing headers (`Host`, `Content-Length`, `Transfer-Encoding`, `Connection`). Overrides of those headers are ignored. Invalid header names, control characters, and duplicate names with different casing within one dictionary are rejected before any network request.

### Structured HTTP diagnostics

Existing `.http(statusCode:body:headers:)` catch patterns remain valid. `httpDetails` adds structured inspection without changing the error case:

```swift
do {
    _ = try await client.evaluate(state: ticket, question: urgent)
} catch let error as JevError {
    if let details = error.httpDetails {
        print(details.statusCode)
        print(details.requestID ?? "No request ID")
        // Available for explicit inspection:
        // details.message, details.validationIssues, details.retryAfter
        // details.json, details.body, details.headers
    }
}
```

Messages are extracted from common service error shapes, including validation arrays with locations, messages, and error codes. Request IDs are read case-insensitively from `x-typesafe-request-id` or `x-request-id`. `retryAfter` reports the server's delay in seconds before applying the policy cap; HTTP-date delays are relative to when details are constructed. Non-JSON bodies are preserved without inventing a message. Service messages can contain input data, so the SDK never includes them in logs or localized error descriptions.

### Optional diagnostic events

```swift
struct ConsoleLogger: JevLogger {
    func log(_ event: JevLogEvent) {
        print(event.operationID, event.kind, event.attempt, event.statusCode ?? 0)
    }
}

let client = JevClient(
    configuration: try .fromEnvironment(),
    logger: ConsoleLogger(),
    logLevel: .info
)
```

Levels are `debug`, `info`, `warning`, `error`, and `off`. A logger and a non-off level are both required. Events report request starts (debug), HTTP responses and cancellation (info), scheduled retries (warning), and terminal transport/HTTP failures (error). Each operation has one UUID across all its attempts; attempts are one-based. Durations and retry delays are in seconds. Response events describe HTTP completion, not semantic validation of model answers.

Events contain only fixed API paths, methods, status/error codes, timings, attempt counts, and the generated operation ID. Bodies, credentials, arbitrary headers, server messages, and configured URLs are never passed to the logger, even at debug level. Read server request IDs explicitly from `httpDetails`. Loggers must handle concurrent calls and return promptly; no logging framework dependency is required.

Defaults follow the official JavaScript SDK's retry policy: two additional attempts for transient connection failures, timeouts, HTTP 408, 429, and 5xx (including 529). Delays start at 0.5 seconds, double up to 5 seconds, and subtract up to 25% jitter. `retry-after-ms` takes priority over `Retry-After`; valid delays up to 60 seconds are honored, otherwise backoff applies. `Retry-After` supports seconds and HTTP dates. Authentication and request validation errors, malformed responses, and cancellation are never retried. Set `.disabled` to disable retries. Configurable retry delays are limited to one day.

`timeout` configures the URL request timeout per attempt; retries and their delays can extend total elapsed time. URLSession applies its request timeout semantics, so use caller cancellation when a strict overall deadline is required. Retrying after an interrupted response can repeat an evaluation; the service does not document an idempotency key.

## Use from Apple applications

Keep the shared TypeSafe service key on your backend. The backend authenticates the app, applies its own usage policy, and forwards the request to TypeSafe. It can use this same package on a Swift server.

For a proxy that exposes the same contract, initialize `JevConfiguration(apiKey: appSessionToken, baseURL: proxyRoot)`. The SDK appends `/v1/systemone` or `/v1/models` and sends that token as Bearer authentication. The proxy must verify the app token and replace it with the server-held TypeSafe credential upstream. Use HTTPS in production. A custom `JevTransport` can adapt other authentication or transport needs. This repository does not include a backend or provision credentials.

## Build, test, and run examples

```sh
swift build
swift test
swift run JevExamples
```

The default example run makes no network requests. Live usage must be explicitly enabled:

```sh
export TYPESAFE_API_KEY='your-key'
swift run JevExamples --live
# Optional additional dynamic batch, standalone evaluation, model listing, and logging:
swift run JevExamples --live --dynamic --single --models --log
```

The live example uses environment configuration, an Encodable state model, CaseIterable options, a reusable typed batch, and per-call options. It prints model outputs and token usage and consumes service quota. The optional flags make additional calls or enable metadata logging. No live requests run in CI. Offline tests use injected `JevTransport` and `JevRetryTiming` implementations to check wire contracts, validation, typed responses, retries, and cancellation without actual waits.

CI builds and tests on Swift 6.0/Linux and macOS, and compiles the library for iOS Simulator. To compile the simulator target locally:

```sh
xcodebuild -scheme JevSwiftSDK -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .build/xcode CODE_SIGNING_ALLOWED=NO build
```

## Publishing

The public repository is [NSStudent/JevSwiftSDK](https://github.com/NSStudent/JevSwiftSDK), with `main` as its default branch. Tag a semantic version only after CI passes on the published repository.

## License

MIT. See [LICENSE](LICENSE).
