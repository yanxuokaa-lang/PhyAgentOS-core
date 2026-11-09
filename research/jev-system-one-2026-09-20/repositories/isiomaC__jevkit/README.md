# JevKit

JevKit is a native Swift package for [TypeSafe Jev](https://typesafe.ai/), a
System One model that returns typed decisions and probabilities. It lets Apple
platform applications send JSON-compatible state, ask narrow Choice, Noul, or
Score questions, and keep all execution policy in deterministic Swift code.

JevKit is early-stage software. Its network contract follows the documented
TypeSafe System One API; applications should validate decision thresholds with
their own data before relying on them.

## Requirements

- Swift 6.0 or newer
- macOS 13 or newer
- A TypeSafe Jev API key for live calls

## Install with Swift Package Manager

Add JevKit to a package dependency:

```swift
.package(url: "https://github.com/isiomaC/jevkit.git", branch: "main")
```

Then add `JevKit` to the target dependency list. Use a versioned requirement
instead once the first release tag exists.

## Configure a client

Pass a key from your host application. JevKit does not persist it or log it.

```swift
import JevKit

let configuration = try JevConfiguration(apiKey: apiKey)
let jev = JevClient(configuration: configuration)
```

For production Apple applications, store user-provided keys in Keychain and
pass them in memory. Do not add keys to source, application bundles, fixtures,
or logs.

## Choice

Use Choice when one option from a closed set is required.

```swift
enum Activity: String, CaseIterable, Codable, Sendable {
    case coding, debugging, researching, other
}

let criteria: [Activity: String?] = [
    .coding: "Writing or editing software source code.",
    .debugging: "Investigating or fixing a software problem.",
    .researching: "Seeking information to inform work.",
    .other: "None of the listed activities.",
]

let answer: ChoiceAnswer<Activity> = try await jev.choice(
    state: ["application": "Xcode"],
    instructions: "What is the user doing?",
    criteria: criteria
)

print(answer.value)
print(answer.probabilities)
print(answer.confidence)
```

## Noul and Score

Use Noul for the probability that a condition is true. It deliberately has no
synthetic confidence value.

```swift
let useful = try await jev.noul(
    state: ["text": "I am blocked by a compiler error"],
    instructions: "Would a small contextual suggestion likely be useful now?"
)

print(useful.probability)
```

Use Score for an ordered rubric with at least two concrete levels.

```swift
let severity = try await jev.score(
    state: ["report": "Export fails with no workaround."],
    instructions: "How severe is the reported issue?",
    criteria: [
        "Cosmetic; functionality works.",
        "A feature is degraded but a workaround exists.",
        "A blocking failure has no workaround.",
    ]
)

print(severity.score)
print(severity.probabilities)
print(severity.confidence)
```

## Confidence and policy

Choice and Score confidence are supplied by Jev from the shape of their
probability distributions. They are not a guarantee that the decision is
correct, and they never authorize an action by themselves. Noul exposes only
its true probability.

Keep policy in your application:

```swift
let policy = try DecisionPolicy(automaticThreshold: 0.90, suggestionThreshold: 0.65)
switch policy.disposition(for: answer.confidence) {
case .automatic: /* application decides what, if anything, is safe */
case .suggest:   /* surface a reviewable suggestion */
case .uncertain: /* do nothing or request more information */
}
```

JevKit never executes desktop or user actions.

## Test without networking

Inject `MockJevTransport` with queued `JevResponse` values or `JevError`s.
The mock is actor-isolated and records requests, making application tests
deterministic and independent of the live Jev service.

## CLI example

The package includes an all-Swift live example. It reads only `JEV_API_KEY`
from the environment:

```zsh
export JEV_API_KEY='your_key_here'
swift run JevCLI
```

Without a key, the CLI exits without sending a request.

## Development

```zsh
swift test
swift build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and
[TypeSafe's API documentation](https://docs.typesafe.ai/api.md) for the
authoritative Jev HTTP contract.

## Security and privacy

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability. Never include
an API key or sensitive application state in an issue, pull request, log, or
test fixture.

## License

JevKit is available under the [MIT License](LICENSE).
