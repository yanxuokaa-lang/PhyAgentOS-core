# LM Studio + TypeSafe chat

A small standalone Tkinter app. LM Studio generates replies locally; TypeSafe
classifies each new message's tone and supplies a gentle response-style hint.
With **Refine replies with Jev** enabled (the default), Jev also checks the draft
for stiff wording, unnecessary repetition, and failure to address the request.
By default, an issue probability of at least 0.75 triggers one LM Studio rewrite with targeted
instructions. This is a demo heuristic, not a validated quality threshold.
The transcript reports the review and whether a rewrite occurred. The rewritten
answer is not reviewed again, so improvement is not guaranteed. Uncheck the box
to keep the original single-generation flow.

## Live video narration

1. Load a vision-capable model in LM Studio (the downloaded LFM2.5-VL models are
   candidates). In **Vision**, refresh the list and choose the model. The main
   chat model is not used by live narration.
2. Open **Live narration**. Choose **Screen** or **Video file**.
   For Screen, play the video in your usual player and use **Select screen area**
   to drag around it; Escape cancels selection. Whole-screen capture covers the
   primary display. Prefer a crop that excludes this app's preview.
   For Video file, choose a local file. Its preview plays silently at the file's
   frame rate; use Screen mode if you want the player's original audio as well.
3. Set a check interval (default 3 seconds) and speech speed. Click **Start**.
   **F8** starts, **F9** stops, and **F10** mutes while the app has keyboard focus.
   You can also Tab to the buttons. Screen-area dragging may require sighted help;
   whole-screen and video-file modes do not require dragging.
4. Listen to Windows speech or read the narration transcript. Mute leaves text
   narration running. Stop ends capture and speech promptly; a pending HTTP
   request may finish later, but its result is discarded. Restart is enabled
   once the workers finish. Closing the app stops the session.

The vision model produces short frame descriptions; Jev compares each description
with the previous report and suppresses redundant information. **Narration
sensitivity** controls this while running: 0 announces at 95% new-information
probability, 50 (default) at 60%, and 100 at 25%. Move toward **More updates** to
announce less-certain changes, or **Fewer updates** to require stronger evidence.
Changes apply to the next Jev review. The slider affects frequency, not narration
length or sampling speed. Exact repeats still get skipped. The slider requires
Jev to be available; fallback narration does not use this threshold. This live change filter
is independent of chat strictness, mood, master prompt and code mode. If Jev fails,
new vision descriptions still appear and can be spoken, with a visible status.
No TypeSafe key means vision-only narration.

Frames stay in memory, are resized to at most 768 pixels on their longest edge,
and go only to the configured vision server. Descriptions go to TypeSafe when a
key is present. Nothing is recorded to disk. Capture keeps only the latest frame;
inference never builds a frame queue. Speech keeps at most one waiting description
and discards descriptions older than 20 seconds. Actual sampling is slower than
the chosen interval by the time required for vision and Jev inference.

Descriptions are approximate, can miss events, and can lag the video. A single
frame does not establish motion. This is an assistive prototype, not reliable
hazard detection or navigation guidance. Model speed and accuracy depend on your
hardware and selected model. If a thinking model returns truncated replies,
disable thinking in LM Studio or select a faster vision model.

Live dependencies: `opencv-python`, `Pillow`, `pywin32` (already present in the
Python installation used during development). Basic chat works without them;
live features report missing capture/speech support when started.

## Image descriptions with a dedicated vision model

Load an image-capable model (for example LFM2.5-VL) in LM Studio. In the app's
**Vision** tab, click **Refresh models** and select that model. The list may also
contain text-only models: select a VL/vision model. Leave the vision URL blank
to reuse the main server, or supply another OpenAI-compatible server URL and key.
The main server key is reused only when the normalized server URLs match.

Click **Attach image**, select a PNG/JPEG/WebP up to 10 MB, type a question, and
Send. An empty question becomes "Describe this image." The image goes only to
the configured vision server. Its extracted text goes to the main chat model and,
with refinement enabled, to Jev. Jev checks the reply for unsupported visual claims
against that text; it cannot independently verify the original image.

The description appears in chat and the Vision tab. It remains in conversation
history for follow-ups, but the image bytes are not kept in history. Successful
sends clear the attachment; failed sends retain it for retry. Clear chat removes
the attachment and last description. Extraction failures stop the request instead
of generating an answer without the image context. All network and file reads
run in the worker thread. This attachment feature handles still images.

## Python code review

Enable **Python code review (no execution)** and ask for Python code or paste code
to inspect. Keep **Refine replies with Jev** enabled for one optional repair pass.
Example: "Write a Python function that averages a list of numbers. Return None
for an empty list. Include example tests."

- LM Studio drafts the code. This mode bypasses user-tone classification and mood.
  The master prompt can supply relevant coding requirements; conversational
  personality checks are replaced by code checks. Clear chat when switching from
  roleplay to coding to reduce interference from old conversation context.
- Python compiles fenced `python`, `py`, or unlabelled code blocks in memory to
  check syntax and scope errors. Each block is checked separately. Generated
  code is never executed, imported, saved or tested. Other languages are not
  syntax-checked. Missing/unclosed Python blocks are reported, not treated as a pass.
- Jev estimates requirement mismatch, likely runtime/logic errors, and relevant
  edge-case gaps using the draft, request, recent context, master prompt and syntax
  findings. The strictness slider governs these estimates as before.
- A syntax issue or a Jev score reaching the threshold triggers at most one LM
  Studio repair. The final displayed answer is syntax-checked again; remaining
  errors are visible. A syntax repair can still occur if Jev is unavailable or no
  key is set. If refinement is unchecked, only local syntax checking occurs.
- **PASS means syntax only**, using the Python version running the app. It does
  not prove runtime behavior, dependencies, compatibility or tests pass. Example
  tests generated by the model are suggestions, not executed test results.

Checks run in the existing worker thread. Each block is limited to 100,000
characters for syntax inspection. Complete Markdown fences are required.
This is a Python review helper, not an isolated code execution environment.

## Master prompt

Open the **Master prompt** tab and paste your system prompt to define personality,
voice, role, and response requirements. It applies to the next reply; no Apply
button is needed. Leave it blank for the default assistant. Clear chat when
testing a different personality so previous replies do not influence it.

Example: "You are Mira, a curious, witty companion. Speak naturally, use light
humor, and usually keep replies to two or three sentences. Avoid canned greetings."

The master prompt is sent as part of LM Studio's system message for both initial
generation and rewriting. When refinement is enabled, Jev receives the same
prompt and checks for **personality mismatch** alongside the existing checks.
The strictness slider controls when this can trigger the one permitted rewrite.
Mood is a temporary variation within the master personality; the master prompt
takes precedence when they conflict. Adherence remains probabilistic.

The prompt is held in memory only and is not saved on exit. Clearing chat keeps
the prompt. With refinement enabled it is also sent to TypeSafe's cloud API.

## Assistant mood

The mood slider sets the assistant's writing style from **-100 Grumpy** through
**0 Neutral** to **+100 Cheerful**. Intermediate positions are reserved or warm.
It applies to the next message and stays separate from the user's detected tone.
Grumpy means dry and mildly irritable, while still giving useful, respectful answers.
Explicit style requests in chat take priority; sensitive topics can soften the mood.

The target is passed to LM Studio when generating and to Jev during draft review.
Jev checks for a clear mood mismatch and can trigger the existing single rewrite.
With refinement off or TypeSafe unavailable, the slider still guides LM Studio
directly. Mood matching is probabilistic, not guaranteed. Settings are session-only.
Test by clearing chat and asking the same question at -100 and +100 with refinement
enabled. The transcript shows the requested mood and Jev's mismatch probability.

## Jev strictness

The **Jev strictness** slider controls how readily the app triggers a rewrite for
stiffness, repetition, relevance, or mood mismatch. It changes the decision
threshold, not Jev's probabilities or the chosen assistant mood:

| Strictness | Rewrite when any issue reaches |
| --- | --- |
| 0 (Light) | 95% |
| 25 (default, original behavior) | 75% |
| 50 | 55% |
| 75 | 35% |
| 100 (Strict) | 15% |

For example, a stiffness score of 46% triggers a rewrite at strictness 75, but
not at 25. Higher strictness can cause unnecessary rewrites; it does not guarantee
better quality. There is still at most one rewrite per message. Keep **Refine
replies with Jev** enabled and provide a TypeSafe key for this slider to take effect.
Zero means very light review; uncheck refinement to turn review off completely.
The setting applies to the next message and is not saved between app sessions.
Python 3.10+ with Tkinter is required. Basic chat and image attachments need no
pip packages. Live narration additionally uses OpenCV, Pillow, and pywin32 on Windows.

## Run on Windows

1. Open LM Studio, load a **chat/instruct model**, and start its local server in
   the Developer tab (normally port 1234).
2. Double-click `start_chatbot.cmd`, or run `python -B chatbot.py` from this folder.
3. Leave the URL as `http://localhost:1234/v1` unless your server uses another address.
4. Your `TYPESAFE_API_KEY` environment variable fills the masked key field.
   You can also paste a key there for this session. Restart the launcher after
   changing Windows environment variables.
5. If LM Studio requires authentication, fill its separate optional key field
   (also reads `LM_STUDIO_API_KEY`).
6. Click **Load models**, select a chat model, type a message, and press **Enter**.
   **Shift+Enter** inserts a newline. **Clear chat** starts a new conversation.

Try “Hello, how are you?” and then “I'm frustrated; I can't get this code working.”
The transcript shows the inferred tone and confidence alongside the local reply.
The confidence is a distribution measure, not a guarantee of correctness. The
0.6 cutoff for applying a tone-specific hint is a demo heuristic, not a calibrated
threshold. The model may not always visibly change its writing style.

## Data and failure behavior

- The latest user message is sent to TypeSafe's cloud API for tone analysis.
  With refinement enabled, a second request sends the current message, draft reply,
  last four conversation messages, and master prompt. Both requests use API quota.
- Up to 10 prior exchanges are sent to the configured LM Studio server.
- Keys and chat are held in memory; the app writes neither to disk.
- Clearing the TypeSafe key skips its API. An unavailable TypeSafe service or
  malformed classification produces a visible note and neutral local-chat style.
- LM Studio errors restore your draft for retry and do not add failed turns to
  conversation context. Requests run in background threads. Closing the window
  exits immediately; it does not guarantee cancellation of server-side work.
- If the review or optional rewrite fails, the original answer is shown with a
  visible note. Only the final displayed reply enters conversation history.
- Replies appear when complete (no token streaming). Timeouts are 20 seconds for
  each TypeSafe call, 15 seconds for model discovery, and 120 seconds for each
  LM Studio generation. Refinement adds one review and at most one generation.
- No NeuralCompanion code or settings are changed.

## Verification

Run `python -B -m unittest -v test_chat_backend` for backend tests.
Manual checks: load models; send two messages and check context; clear chat;
remove the TypeSafe key and check local-only behavior; use an invalid key and
check the fallback note; stop LM Studio and check the error and restored draft;
close the window while waiting for a reply.

API references: [LM Studio chat completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions),
[TypeSafe HTTP API](https://docs.typesafe.ai/api),
[TypeSafe Choice](https://docs.typesafe.ai/primitives/choice).
# Chatterbox speech for live narration

**Project Chatterbox** is the default speech provider. It runs Chatterbox Turbo
directly from this project's `.venv-chatterbox` Python 3.11 environment, without
NC code or NC packages. Its device and optional reference voice settings are in
the Speech tab; NC folder/Python fields apply only to **NC Chatterbox**.
Punctuation-aware chunk playback works in both modes. Model weights use the
existing Hugging Face cache; they are not duplicated inside the project.

To reinstall dependencies, run `powershell -ExecutionPolicy Bypass -File
install_chatterbox.ps1` from this folder (Python 3.11 required). This pins
Chatterbox 0.1.6 and PyTorch/Torchaudio 2.6.0 with CUDA 12.6. The main app still
starts with `python -B chatbot.py`; it launches the dedicated TTS interpreter
automatically. Narration loads cached weights offline.

Open the **Speech** tab and select **NC Chatterbox**. The NC folder is prefilled
with `Q:\NEURALCOMPANION DEV MAIN\NeuralCompanion-dev-dirty`, and its `.venv`
Python is detected automatically. Choose the vision model, then start from
**Live narration**. Restart this small app after updating its files.

This calls NC's existing Chatterbox Turbo service in an isolated process using
its installed packages and cached weights. It does not change NC files, install
packages, or download models. It loads a separate model instance, so allow extra
GPU memory if NC or LM Studio is also using the GPU. `auto` uses CUDA when
available; CPU is selectable. An optional reference audio file selects a voice;
blank uses Chatterbox's default voice, not NC's saved voice settings.

NC speech is generated in sentence/clause chunks: playback can begin as soon as
the first chunk arrives while the worker generates later chunks. Punctuation is
kept for pauses and intonation; common abbreviations and initials do not end a
chunk. Ordinary sentences remain intact, with a 24-word fallback limit for long
unpunctuated passages. Prosody across chunk boundaries can differ from a single
full-text generation. This is phrase streaming, not token-level model streaming.
The optional HTTP server mode still requests a complete WAV.

Video waits for initial voice loading. Chunking reduces synthesis delay, not the
initial model loading time. Stop cancels loading, and Stop/Mute halt
audio playback. Descriptions over 20 seconds old are discarded, including after
speech synthesis. A Chatterbox error is displayed and switches the session to
Windows speech. Its speed control does not affect
Chatterbox. Speech settings apply on the next Start and remain in memory only.

Alternatively, **Chatterbox server** accepts a configurable `/tts` endpoint
(text/output_format WAV) or `/v1/audio/speech` endpoint (OpenAI-style input and
response_format WAV), optional voice/model and bearer key. It requires an already
running compatible server. Playback uses `sounddevice` and `soundfile` in this
demo's Python environment. Server requests time out after 15 seconds.
