[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

# jevis

Jevis is a Dart package that runs on Flutter's `integration_test` framework to test Flutter apps with TypeSafe's Jev model. **Register the actions your test may use, describe a goal, and set an action budget.** Jev chooses the next action from the current UI and evaluates whether the goal has been reached.

[![Watch the Jevis demo on YouTube](https://img.youtube.com/vi/pfnfXmgHioU/hqdefault.jpg)](https://www.youtube.com/watch?v=pfnfXmgHioU)

[▶ Watch the Jevis demo on YouTube](https://www.youtube.com/watch?v=pfnfXmgHioU)

[How to start](#how-to-start) · [Actions](#actions) · [Goals and execution](#goals-and-execution) · [Observation and limits](#observation-and-limits) · [Logging](#logging) · [Example and tests](#example-and-tests) · [License and contributing](#license-and-contributing)

```dart
final agent = JevisTester(
  tester: tester,
  actions: [
    JevisActions.tap(),
    JevisActions.enterText(values: ['Buy milk']),
    JevisActions.scroll(),
    JevisActions.back(),
  ],
);

await agent.test(
  goal: 'A Buy milk todo is completed.',
  instruction: 'Add Buy milk, then mark it complete.',
  attempts: 20,
);
```

The `actions` list defines available capabilities, not an execution sequence. The constructor does not require a goal, a fixture map, or a `successCondition`. This is a Flutter test package: it requires the Flutter SDK, not just a standalone Dart installation.

<a id="how-to-start"></a>
## How to start

### 1. Prepare Flutter and install the package

You need a Flutter app, the Flutter SDK with Dart 3.4 or later, and a device, emulator, or simulator supported by your app. Check your environment:

```bash
flutter doctor
```

Add [jevis from pub.dev](https://pub.dev/packages/jevis) to your app's `pubspec.yaml` under `dev_dependencies`:

```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  integration_test:
    sdk: flutter
  jevis: ^0.1.1
```

Install the dependencies from your app's root:

```bash
flutter pub get
```

### 2. Get and configure your API key

Sign in to the [TypeSafe console](https://console.typesafe.ai/) and obtain an API key. The [official TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart) links to the dashboard for API keys.

Create `jev.local.json` in **your app's root**, next to `pubspec.yaml`:

```json
{
  "TYPESAFE_API_KEY": "YOUR_TYPESAFE_API_KEY"
}
```

Add this entry to your app's `.gitignore` before saving a real key:

```gitignore
jev.local.json
```

Keep the key out of source control. Jevis reads `TYPESAFE_API_KEY` from Dart compile-time definitions. The JSON file is **not loaded automatically**: pass `--dart-define-from-file=jev.local.json` when running the test. Merely exporting a shell environment variable does not configure the default client. You can also supply `apiKey:` directly to `JevisTester` from your own configuration.

The default client calls the real Jev API. A missing key fails during initialization. The model ID remains `jev-latest`, and `jev.local.json` is the configuration filename used in these examples.

### 3. Write your first test

Create `integration_test/jevis_smoke_test.dart` in your app:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:jevis/jevis.dart';
import 'package:your_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Jevis adds and completes a todo', (tester) async {
    app.main();
    await tester.pumpAndSettle();

    final agent = JevisTester(
      tester: tester,
      actions: [
        JevisActions.tap(),
        JevisActions.enterText(values: ['Buy milk']),
        JevisActions.scroll(),
        JevisActions.back(),
      ],
    );

    await agent.test(
      goal: 'A Buy milk todo is completed.',
      instruction: 'Add Buy milk, then mark it complete.',
      attempts: 20,
    );
  }, timeout: const Timeout(Duration(minutes: 5)));
}
```

Replace `your_app` with the package name from your app's `pubspec.yaml`. This template assumes a todo UI; adapt the goal, instruction, and input values to your app. `tester` is the Flutter UI execution context. To try the repository's own UI instead, see [Example and tests](#example-and-tests).

### 4. Run the test

Start a simulator or emulator, or connect a physical device before running the test. Then run this command from your app's root:

```bash
flutter test integration_test/jevis_smoke_test.dart --dart-define-from-file=jev.local.json
```

A successful run returns a `JevisReport`. If the goal is not reached, Jevis throws `JevisTestFailure`, failing the Flutter test.

If setup fails, first check that `flutter pub get` succeeds, that a simulator is running or a device is connected, and whether the command includes `--dart-define-from-file`. API requests contain current UI text and action descriptions, so use test accounts and test data.

<a id="actions"></a>
## Actions

### Discover standard controls

Register only the capabilities your scenario needs. `JevisActions` discovers concrete targets from the current screen:

```dart
final agent = JevisTester(
  tester: tester,
  actions: [
    JevisActions.tap(),
    JevisActions.focus(),
    JevisActions.enterText(values: ['Alex', 'alex@example.com']),
    JevisActions.clearText(),
    JevisActions.keyboardAction(), // Uses the field's declared IME action.
    JevisActions.longPress(instruction: 'Hold a sample note to reveal its delete button.'),
    JevisActions.doubleTap(),
    JevisActions.drag(offset: const Offset(-250, 0)),
    JevisActions.selectOption(),
    JevisActions.adjustSlider(),
    JevisActions.scroll(),
    JevisActions.back(),
  ],
);
```

- `focus()` offers inputs that are not focused. `clearText()` offers editable inputs with a value.
- `keyboardAction()` uses the field's IME action; specify `action: TextInputAction.done` to choose one explicitly.
- `selectOption()` opens a dropdown, then offers its enabled visible options on the next observation. `values: ['High priority']` restricts option labels.
- `adjustSlider()` offers valid increase/decrease directions for Material Slider. Use `direction` and `steps` to control adjustment.
- `dragTo(destination: find.byKey(const ValueKey('catalog_drop_target')), holdDuration: const Duration(milliseconds: 650))` discovers a Draggable source. You specify the destination and timing.
- `wait()` and `waitUntil(condition: ...)` provide explicit waiting. An action's `instruction` adds guidance to the candidate description; it is not evidence that the action succeeded.

Input strings must be supplied through `values` or `value`; Jevis does not generate arbitrary text. More than 254 available candidates causes an explicit failure. Reduce input choices or registered capabilities when needed.

### Target specific widgets or add custom actions

You can combine discovered actions with explicit `JevisAction` targets. Add stable keys to your widgets:

```dart
FilledButton(
  key: const ValueKey('save_todo'),
  onPressed: saveTodo,
  child: const Text('Save'),
)
```

```dart
JevisAction.tap('Tap Save.', key: 'save');
JevisAction.tap('Open Settings.', finder: find.text('Settings'));
JevisAction.enterText('Enter email.', key: 'email', value: 'test@example.com');
JevisAction.scroll('Explore the list.', key: 'list', offset: const Offset(0, -300));
JevisAction.wait();
JevisAction.custom('Perform a custom gesture.', run: (tester) async {
  await tester.longPress(find.byKey(const ValueKey('item')));
});
```

Explicit gestures and waits can also be combined:

```dart
JevisAction.longPress(
  'Long-press the Buy milk todo to reveal its delete icon.',
  key: 'milk_todo',
  waitFor: JevisWait.visible(key: 'delete_todo'),
);
JevisAction.drag(
  'Swipe the todo left to reveal its actions.',
  key: 'milk_todo',
  offset: const Offset(-250, 0),
  duration: const Duration(milliseconds: 500),
);
```

For a targeted action, provide exactly one of `key` or `finder`. The finder must resolve to one visible target. The package generates action IDs. Use `availableWhen: () => ...` for additional availability conditions on custom controls. Pinch gestures are not built in. See the [action reference](doc/actions.md) for supported targets, timing, and examples.

<a id="goals-and-execution"></a>
## Goals and execution

### Goal, instruction, and attempts

`test()` uses named parameters. `goal` and `attempts` are required; `instruction` and `verify` are optional. When `instruction` is omitted, `goal` is also used as the action instruction.

Write the goal as an observable final state and the instruction as the work to perform. If you provide a separate instruction, include all values needed to act, such as a target volume of 70%.

```dart
await agent.test(
  goal: 'The Widget Catalog displays "Drop status: Delivered".',
  instruction: 'Navigate to Widget Catalog. Find Parcel and drag it onto Drop zone.',
  attempts: 50,
);
```

`attempts: 20` allows **at most 20 UI action executions**, not 20 restarts of the scenario or 20 API retries. For example, creating ten items through open/input/save takes at least 30 actions, before navigation or completion actions.

Goal evaluation runs before actions and after the last allowed action. A run can make at most `attempts + 1` Noul calls and `attempts` Choice calls. Success returns immediately. Failure to reach the goal, inability to proceed, low confidence, repetition, and API errors fail the test.

Each `test()` call resets exploration memory, action history, and repetition counters. App state remains intact, so you can run goals sequentially with the same agent. Do not run them concurrently on the same UI.

```dart
await agent.test(goal: 'A Buy milk todo exists.', instruction: 'Add a todo titled Buy milk.', attempts: 10);
await agent.test(goal: 'The Buy milk todo is completed.', instruction: 'Mark Buy milk complete.', attempts: 10);
```

### How Noul and Choice work together

Each step follows: observe → Noul → Choice if needed → execute → observe again.

- **Noul** receives `{goal, screen}` and checks whether the current screen satisfies the goal. It does not receive action candidates or action history.
- **Choice** receives `{actionInstruction, previousActions, screen}` and available candidates, then selects the next action. `actionInstruction` comes from `instruction`, or from `goal` when omitted.

The two requests use the same current screen. If Noul reaches `goalThreshold`, the run succeeds without calling Choice. Choice is called only when the goal is unfinished, attempts remain, and actions are available. `decisionTimeout` covers both HTTP calls in a step. A failed Noul request does not lead to Choice or a UI action.

A simplified Noul request looks like this; the actual request also includes the model and criteria:

```json
{
  "state": {"goal": "Goal", "screen": {"visibleText": [], "widgets": []}},
  "questions": {"goal_reached": {"type": "noul", "instructions": "Is the goal already achieved on the current screen?"}}
}
```

The screen contains current text, visible controls, and scroll state. Choice candidates are sent in `questions.next_action.criteria`. `previousActions` contains summaries of successfully executed actions in order, including repetitions. It is not truncated by `historyLimit`.

Previous screens, initial state, exploration memory, change lists, custom `observe` data, and earlier probabilities are excluded from the default client's requests. They remain available locally and to custom brains. `JevisRequest.toJson()` is local context serialization, not the HTTP request body; use `onRequest` to inspect the latter.

Choice can select `__stop__` when it considers the instruction complete. Jevis then observes the screen again and performs one final Noul check, without another Choice call or UI action. A confirmed goal succeeds; otherwise the run fails with `stopped`. No available actions leads to `noActions`; exhausted action budgets lead to `attemptsExhausted`. Repetition and execution-error checks still apply.

### Verify the result

The default success threshold is `goalThreshold: 0.6`. This is a **probabilistic model judgment, not a deterministic guarantee**. Reports use `completionBasis: model`. Hidden state, persistence, and server-side effects cannot be established from UI evidence alone.

Add `verify` when you need a deterministic check after model completion:

```dart
await agent.test(goal: 'The saved name is Alex.', instruction: 'Enter Alex and save the form.', attempts: 15,
  verify: () => repository.savedName == 'Alex',
);
```

`repository` is your own application or test dependency. If `verify` returns false or throws, the test fails with `verificationFailed`; its completion basis is `model+assertion`.

<a id="observation-and-limits"></a>
## Observation and limits

The observer reads hit-testable standard Flutter controls and creates concrete actions such as tapping an item, entering a supplied value, scrolling, or going back. Disabled and offscreen targets are excluded from executable candidates. Targets are revalidated before execution.

It collects up to 100 visible `Text` strings, labels, input values or password emptiness, checkbox/switch state, slider values, and scroll position and boundaries. Standard buttons, lists, inputs, Material Slider, DropdownButton, Draggable, Dismissible, and supported GestureDetector/InkWell callbacks can be observed. The initial state and recent history are available locally; `historyLimit` defaults to 8.

Give list items stable data-based keys such as `ValueKey(item.id)`. Identical labels can then be distinguished. Avoid index keys for reorderable or removable items. Unkeyed list items can be operated on when visible, but are not accumulated in exploration memory.

`memory.elements` stores the last observation for up to 500 stable keyed targets; overflow sets `memory.truncated`. `changes` records newly observed and changed targets. An entry with `visible: false` is historical evidence, not proof that the item still exists or has the same state. Scroll extent is not treated as an item count. Use visible totals or `verify` for exact final counts.

Custom observation data must be JSON-serializable. It is recorded locally and is not sent by the default `JevisClient`:

```dart
final agent = JevisTester(
  tester: tester,
  actions: actions,
  observe: () => {'screen': currentScreen, 'saveStatus': saveStatus},
);
```

Obscured input values are excluded from default collection, but ordinary UI text and action descriptions are sent to the API. Do not place passwords in descriptions. Use test data and accounts.

The package does not interpret screenshots, custom canvas/game content, WebViews, or the business meaning of arbitrary gestures. OS permission dialogs, visual inspection, pinch gestures, and free-form input generation are not built in. Use explicit/custom actions or a separate verification strategy where needed. Hit testing is not a complete visual occlusion check.

By default, an animation that never settles can cause a `pumpAndSettle` timeout. Use an action's `waitFor` condition to wait for a specific outcome on screens with continuous animation. The examples use English goals and instructions; accuracy across languages and any improvement from the Noul/Choice chain have not been established by this project's tests.

<a id="logging"></a>
## Logging and tuning

```dart
final agent = JevisTester(
  tester: tester,
  actions: actions,
  model: 'jev-latest',
  options: const JevisOptions(
    goalThreshold: 0.6,
    actionThreshold: 0.2,
    maxRepeatedAction: 2,
    decisionTimeout: Duration(seconds: 30),
    settleTimeout: Duration(seconds: 5),
    stepDelay: Duration(milliseconds: 300),
  ),
  onReport: (report) => print(report.toJson()),
);
```

The returned report, `agent.lastReport`, and `JevisTestFailure.report` contain observations, goal probabilities, action confidence and distributions, returned model IDs, executed actions, and failure details. The API key is not included in reports. Use `onRequest` and `onResponse` to inspect HTTP bodies when debugging; those bodies may contain test UI data.

ANSI colors in failure logs are enabled by default. Disable them with `--dart-define=JEVIS_LOG_COLORS=false` or `JevisTester(useColors: false)`. An explicit `useColors` takes precedence over the build setting.

Action confidence is not an accuracy score. Tune thresholds against your app's test data. The bundled catalog tests currently use `goalThreshold: 0.6` and `actionThreshold: 0.2`; these are also the package defaults.

<a id="example-and-tests"></a>
## Example and tests

The bundled [Widget Catalog integration tests](example/integration_test/todo_agent_test.dart) use the real Jev API. From the repository root:

```bash
cd example
flutter pub get
```

Create `example/jev.local.json` with your API key as described in [How to start](#how-to-start). Start a simulator or emulator, or connect a physical device before running the test. Run the following command from `example/`:

```bash
flutter test integration_test/todo_agent_test.dart --dart-define-from-file=jev.local.json
```

To check the package locally without a real API key, run the mock-backed and widget tests from the repository root:

```bash
flutter test
flutter analyze
```

These local tests check package behavior; they do not establish the accuracy of live model decisions. See the [action reference](doc/actions.md) and [changelog](CHANGELOG.md) for more details.

<a id="license-and-contributing"></a>
## License and contributing

Copyright (c) 2026 Jaewon Gwon.

Licensed under the [Apache License 2.0](LICENSE). Contributions are accepted under the same license and require a [Developer Certificate of Origin (DCO) 1.1](DCO) sign-off for each commit. See [Contributing](CONTRIBUTING.md) for instructions.
