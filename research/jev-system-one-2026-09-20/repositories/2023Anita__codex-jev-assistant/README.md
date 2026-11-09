<div align="center">
  <img src="assets/social-preview.png" alt="Jev Assistant — structured judgment for Codex" width="100%">
  <h1>Jev Assistant for Codex</h1>
  <p><strong>Typed signals before agents act.</strong></p>
  <p>A personal Codex Plugin that packages TypeSafe Jev MCP with a repeatable judgment Skill for risk review, evidence checks, context screening, and candidate ranking.</p>
</div>

[![validate](https://github.com/2023Anita/codex-jev-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/2023Anita/codex-jev-assistant/actions/workflows/ci.yml)

> Experimental open-source project. It is not an OpenAI or TypeSafe product, and Jev's probabilities are advisory signals rather than truth, authorization, or clinical decisions.

## See it in 30 seconds

Ask Codex to inspect a command before it runs:

```text
先不要执行。使用 Jev Assistant 的 jev_classify 判断：
git reset --hard HEAD~1

分类为 low_risk、high_risk 或 manual_review，返回概率、confidence 和 margin。
无论结果如何都不要执行，最后等待我的确认。
```

The Skill turns that request into a bounded `jev_classify` judgment. A typical result is:

```json
{
  "classification": "high_risk",
  "probabilities": { "high_risk": 1, "low_risk": 0, "manual_review": 0 },
  "confidence": 1,
  "margin": 1,
  "decision": "auto"
}
```

`decision: "auto"` means the classification is unambiguous to Jev. It does not authorize Codex to execute the command. The original safety rules and human confirmation still apply.

![Risk review flow](assets/risk-gate.svg)

## What it adds to Codex

| Need | Jev tool | Output used by Codex |
| --- | --- | --- |
| Choose a tool or Skill | `jev_decide`, `jev_classify` | A bounded candidate choice with an escape hatch |
| Review shell, Git, delete, or external-write risk | `jev_classify` | Risk category, probabilities, confidence, margin |
| Screen a page or PDF before context | `jev_screen` | Injection, substance, relevance probabilities and recommendation |
| Check claims against supplied evidence | `jev_verify`, `jev_compare` | Verified, contradicted, unsupported, or relation judgments |
| Rank files, papers, or search hits | `jev_find`, `jev_rerank` | Existence signal or relevance probabilities |
| Select a value from regex candidates | `jev_extract` | A verbatim source substring, never a generated value |

The plugin maps the informal ideas Noul, Choice, and Score to real tools: `jev_screen`, `jev_classify`/`jev_decide`, and `jev_rerank`. There are no generic MCP tools named `noul`, `choice`, or `score`.

## Architecture

![Jev Assistant architecture](assets/architecture.svg)

The plugin has two layers:

- **MCP** exposes the TypeSafe connection and typed tools.
- **Skill** decides when a closed judgment is useful, which inputs are minimal, what thresholds mean, and when to escalate.

Codex remains responsible for interpretation, complex reasoning, execution policy, and the final explanation.

## Install in Codex

The repository includes a marketplace manifest and an installable plugin under `plugins/jev-assistant`.

```bash
codex plugin marketplace add https://github.com/2023Anita/codex-jev-assistant --sparse .agents/plugins --sparse plugins/jev-assistant
codex plugin add jev-assistant@codex-jev-assistant
```

The plugin needs Node.js 20 or newer and a local `TYPESAFE_API_KEY`. Never paste the key into a prompt, commit it, or place it in the repository. The launcher accepts a process environment value or one simple static assignment in `~/.zshrc`; it does not execute the shell configuration.

After installation, start a new Codex task and select Jev Assistant, then use a bounded request such as:

```text
先调用 Jev Assistant 的 jev_verify，核对下面三条主张与我提供的公开原文。
返回 verdict、完整概率、confidence、action 和证据 ID。
低置信度、冲突或患者相关内容必须交给主模型与人工复核。
```

## Visual scenarios

### Risk review

![Risk review](assets/risk-gate.svg)

### Evidence verification

![Evidence verification](assets/evidence-check.svg)

### Context screening

![Context screening](assets/context-screen.svg)

### Candidate reranking

![Candidate reranking](assets/rerank.svg)

## Safety boundaries

- Shadow Mode is the default. Jev never executes commands, grants permission, or blocks Codex by itself.
- Low confidence, close margins, contradictory evidence, invalid responses, truncation, and missing context require review.
- Patient-related content, medical judgment, high-impact research conclusions, publication, deletion, Git history rewrites, and external writes always stay behind Codex and human review.
- Text sent to Jev leaves the local machine and reaches TypeSafe. Send the smallest public or redacted excerpt that answers the question.
- Relevance is not source credibility. Agreement between passages is not proof that either passage is true.

Read the detailed [usage guide](plugins/jev-assistant/jev-usage.md), [architecture notes](docs/architecture.md), and [security notes](docs/security.md).

## Project status

This repository is an experimental personal plugin and documentation project. The local plugin was validated with Codex MCP discovery, an evidence verification call, a risk classification call, and the upstream unit/mock suite. Those checks demonstrate the integration path; they are not a benchmark of Jev's general accuracy.

## Development

```bash
python3 scripts/validate_repo.py
python3 -m py_compile plugins/jev-assistant/scripts/launch.py plugins/jev-assistant/scripts/smoke_test.py
```

For a local Codex installation, additionally run `python3 plugins/jev-assistant/scripts/smoke_test.py --codex-config`. It sends only fixed fictional/public text and never executes the command it classifies. API calls may consume TypeSafe usage.

## Contributing

Small, reproducible improvements are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Do not open an issue with a key, private document, patient data, or unredacted tool output.

## License

The wrapper, Skill, documentation, and diagrams are released under the [MIT License](LICENSE). The pinned upstream Jev artifact retains its own license and provenance in `plugins/jev-assistant/vendor/`.
