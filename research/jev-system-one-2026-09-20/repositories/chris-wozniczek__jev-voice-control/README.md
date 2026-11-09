# Jev Voice

A macOS menu-bar app that turns spoken commands into actions using
[TypeSafe AI's Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
— a System One model that returns *typed decisions with probabilities* instead of
generated text.

Press **⌥Space**, say something, and Jev decides what to do:

- "open chrome and go to google.com"
- "quit spotify"
- "type hello world"
- "set volume to 30"
- "search for swift concurrency"
- "maximize chrome"
- "full screen safari"
- "restore chrome"

App names support common aliases such as “chrome”, “code”, “cmux”, and
“settings”. The app can speak short execution replies using the selected macOS
voice, and Settings can enable **Ask before running commands** for a
voice-confirmation step.

Speech is transcribed **on-device** (SFSpeechRecognizer). Only the transcript is
sent to the Jev API.

## How it works

```
microphone ──> SFSpeechRecognizer (on-device) ──> transcript
                                                      │
                                          ClauseSplitter (multi-verb clauses)
                                          │
                              POST /v1/systemone  ──> Jev (typed answers)
                                per clause: action?   target_app?
                                            system_action? mentions_url?
                                            refers_to_frontmost?
                                                      │
                                 Decision + SlotExtractor (url/query/text/%)
                                                      │
                              Executor (NSWorkspace / CGEvent / osascript / pmset)
```

Jev never produces free text — each clause is one `systemOne` call with a state
payload (`clause`, `full_transcript`, `frontmost_app`, `installed_apps`) and five
questions:

| question | type | shape |
|---|---|---|
| `action` | choice | one of `openApp`, `closeApp`, `openURL`, `webSearch`, `dictate`, `system`, `none` |
| `target_app` | choice | installed app names (≤254) + `none` |
| `system_action` | choice | `volumeSet`, `mute`, `lockScreen`, `screenshot`, … |
| `mentions_url` | noul | probability the clause names a website |
| `refers_to_frontmost` | noul | "quit it" → the frontmost app |

Arguments (URLs, queries, dictation text, percentages) can't come from Jev —
it's decision-only — so they're extracted deterministically by `SlotExtractor`
heuristics.

Most commands execute locally without a network call. Commands Jev handles
remain typed decisions; low-confidence or ambiguous commands ask for
confirmation before anything executes.

## Install with Homebrew

This repository doubles as a Homebrew tap (see `Casks/jev-voice.rb`):

```sh
brew tap chris-wozniczek/jev-voice https://github.com/chris-wozniczek/jev-voice-control
brew install --cask jev-voice
```

Homebrew 7+ refuses untrusted third-party taps; if prompted, run
`brew trust chris-wozniczek/jev-voice` first.

Releases are produced by `.github/workflows/release.yml`: bump
`CFBundleShortVersionString` in `Info.plist`, push a matching `vX.Y.Z` tag, and
the workflow builds `Jev-Voice-X.Y.Z.zip`, publishes a GitHub release, and
commits the new version/sha256 into the cask.

## Build from source

```sh
make app    # builds build/Jev Voice.app (ad-hoc signed)
make run    # launches it
make test   # unit tests (pure logic: clause splitting, slot extraction, codecs)
make dist   # zips the app into build/Jev-Voice-<version>.zip and prints its sha256
```

Then set your API key in the popover's Settings (gear icon), or:

```sh
defaults write com.chriswozniczek.jevvoice typesafeAPIKey <key>
# or export TYPESAFE_API_KEY=... before launching
```

### Permissions

- **Microphone** — hear commands
- **Speech Recognition** — transcribe (on-device when supported)
- **Accessibility** — required for the Cmd+V paste used by dictation
- **Automation** — required for `osascript` volume/brightness actions

## Limitations

- Jev is text-only and never generates strings, so URLs/queries/dictation come
  from heuristics over the transcript, not from the model.
- System actions are AppleScript/`pmset` based; brightness key codes may vary
  on some hardware.
- App launching scans standard macOS application directories and running
  regular applications, with aliases and user-defined aliases from Settings.

## Privacy

- Speech recognition runs on-device (`requiresOnDeviceRecognition` when supported).
- Only the transcript, frontmost app name, and installed app list are sent to
  `api.typesafe.ai`. Your API key stays in local `UserDefaults`.
