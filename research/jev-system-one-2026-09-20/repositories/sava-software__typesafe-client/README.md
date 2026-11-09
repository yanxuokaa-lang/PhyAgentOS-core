# TypeSafe Client [![Gradle Check](https://github.com/sava-software/typesafe-client/actions/workflows/build.yml/badge.svg)](https://github.com/sava-software/typesafe-client/actions/workflows/build.yml)

Java client for the [TypeSafe](https://typesafe.ai) System One API. A System One model
(Jev) takes application state and narrow typed questions and returns calibrated
probabilities: a **Choice** over named options, a **Score** on described levels, or a
**Noul** yes/no probability. It does not generate text. Code owns the workflow; the model
supplies the judgment.

No dependencies beyond the JDK, [json-iterator](https://github.com/sava-software/json-iterator),
and sava-rpc's `JsonHttpClient` transport. Built with the shared
[sava-build](https://github.com/sava-software/sava-build) convention plugins; published to
GitHub Packages.

| Module | Java module | Purpose |
|---|---|---|
| [`typesafe-client`](typesafe-client/README.md) | `software.sava.typesafe` | the client, question and answer types, and a recording/replay decorator |
| `typesafe-examples` | `software.sava.typesafe_examples` | runnable usage; not published |
| `typesafe-evals` | `software.sava.typesafe_evals` | evaluation harness for the experiments in [`docs/findings.md`](docs/findings.md); not published |

## Usage

```java
try (final var httpClient = HttpClient.newHttpClient()) {
  final var client = TypeSafeClient.clientBuilder()   // reads TYPESAFE_API_KEY
      .httpClient(httpClient)
      .createClient();

  final var request = SystemOneRequest.builder()
      .state(JsonContent.object()
          .put("message", "I was charged twice and the export button crashes Safari.")
          .build())
      .question("department", Question.choice("Which team should handle `message`?",
          new LinkedHashMap<>(Map.of("billing", "Payments, invoicing, refunds"))))
      .question("refund_requested", Question.noul("Does `message` ask for money back?"))
      .question("frustration", Question.score("How frustrated is the writer of `message`?",
          "Calm and neutral.", "Concerned but civil.", "Very angry or using strong language."))
      .build();

  final var response = client.systemOne(request).join();
  response.choice("department").choice();        // "billing"
  response.noul("refund_requested").noul();      // 0.0 .. 1.0
  response.score("frustration").score();         // 0.0 .. 2.0
}
```

Ask every independent question about one state in the same request: they are evaluated
in parallel, and one request with ten questions costs about a tenth of ten requests.

See the [module README](typesafe-client/README.md) for the full surface, the error contract,
and `RecordingTypeSafeClient`.

## Dependency

```kotlin
// settings.gradle.kts: add the GitHub Packages repository for sava-software/typesafe-client
implementation("software.sava:typesafe-client:<version>")
```

## Build

```
./gradlew check
```

Hardening (PIT mutation suites, Jazzer fuzz targets) is described in [`AGENTS.md`](AGENTS.md).

## Experiments

`typesafe-evals` holds the two experiments described in [`docs/findings.md`](docs/findings.md).
Each is a `JavaExec` task that reads only public-repository content (checked with
`gh repo view --json visibility`, failing closed), records every API exchange under
`typesafe-evals/recordings/<experiment>/`, and writes a blind labeling sheet plus a report
under `typesafe-evals/experiments/<experiment>/`.

```
./gradlew :typesafe-evals:rot       -PevalArgs="--manifest <MANIFEST.txt> --golden-fleet <dir> --checkouts <dir> --out <dir> --recordings <dir> --mode record"
./gradlew :typesafe-evals:dedupe    -PevalArgs="--projects <dir,dir> --out <dir> --recordings <dir> --mode record"
./gradlew :typesafe-evals:hardening -PevalArgs="--checkouts <dir> --repos <name,name> --out <dir> --recordings <dir> --mode record"
./gradlew :typesafe-evals:docsMine  -PevalArgs="--checkouts <dir> --repos <name,name> --out <dir>"
```

`docsMine` makes no API call: it mines git history for the doc-comment label source that
Experiment C1 needed and records why that source is empty on this fleet.

`--mode replay` re-renders a report from the recordings with no key and no cost; add
`--labels <labeling-sheet.tsv>` once the `label` column is filled in. Nothing here accepts,
merges, or gates anything: Jev proposes, code and humans dispose.

## License

Apache-2.0 (as the rest of the sava fleet).
