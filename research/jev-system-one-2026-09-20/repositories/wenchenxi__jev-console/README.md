# Jev Console

A small desktop console and CLI for **Jev**, the [System One model](https://docs.typesafe.ai/concepts/system-one) from [TypeSafe AI](https://typesafe.ai).

Jev does not generate text. You send it a **state** plus a set of **typed questions**, and it answers each one with a typed value and a calibrated probability:

| Question type | What comes back |
| --- | --- |
| **Noul** — *is this true?* | a probability between 0 and 1 |
| **Choice** — *pick one of N options* | the chosen option, the full probability distribution, confidence |
| **Score** — *where on this scale?* | a score (may land between levels), probabilities, confidence |

This repo is the piece I wanted and couldn't find: something that lets a human *use that API by hand*, without writing code for every question. Paste a state, add a few questions, press one button, read the probabilities.

![screenshot](assets/screenshot.png)

*(The UI is in Chinese — it was written for personal use. The labels are: ① give the state, ② ask questions, ③ the model's judgment.)*

## What it is not

- Not a chat client. Jev can't write prose, so neither does this.
- Not a place for arithmetic, counting, or date ordering — TypeSafe's own guidance is to keep those in code.
- Not affiliated with TypeSafe AI. It only calls the documented endpoint `POST https://api.typesafe.ai/v1/systemone`.

## Requirements

- Python 3.10+ with tkinter (`python3-tk` on Debian/Ubuntu; bundled with the Windows/macOS installers)
- A TypeSafe API key — create one at <https://console.typesafe.ai/keys>
- **No third-party packages.** Standard library only (`urllib`), so `typesafe-sdk` is not needed here.

## Setup

```bash
# either an environment variable...
export TYPESAFE_API_KEY=your-key        # Windows: setx TYPESAFE_API_KEY your-key

# ...or a .env file next to this README
echo "TYPESAFE_API_KEY=your-key" > .env
```

The key is looked up in this order: `TYPESAFE_ENV_FILE` → `./.env` (next to the scripts) → `./.env` (cwd) → `~/.hermes/.env`.

## Run

```bash
python jev_gui.py                        # the window

python jev_cli.py --models               # sanity check: list the models your key can call
python jev_cli.py --state "text…" --noul "urgent=Does this message convey urgency?"
python jev_cli.py --state-file s.txt \
    --choice "dept=Which team should handle this|billing:payments;technical:bugs;sales:pricing" \
    --score  "frustration=How frustrated is the customer|calm;annoyed but civil;angry"
python jev_cli.py --state-file s.json --questions q.json --json
python jev_cli.py --state "x" --noul "q=is this true" --dry-run     # print the request body only
```

CLI flags: `--noul` `--choice` `--score` (repeatable), `--state` / `--state-file`, `--questions`, `--model`, `--json`, `--dry-run`, `--models`, `--timeout`.

Both entry points share one request path (`jev_core.py`): a single POST, all questions evaluated in parallel against the same state, with exponential-backoff retry on `429`/`529`.

## Notes from using it

- Questions run **in parallel over the same state**, so adding questions costs input tokens but almost no extra latency — ask everything you might need in one call.
- Accuracy falls as the state fills with irrelevant detail; filter before sending.
- One narrow judgment per question. Put the candidate answers in the criteria, and include a "none of these" option when nothing may fit.
- Jev reads literally: write the exact condition you mean, not the one you have in mind.

## 中文说明

给 TypeSafe 的 **Jev（System One 决策模型）** 做的本地小控制台 + 命令行。

Jev 不生成文字，只回答三种类型化问题（是/否、选一个、打分），返回校准过的概率。这个工具解决的问题是：**让人手工就能用它**——贴一段材料、加几条问题、点一个按钮，直接看到概率分布和置信度，不用为每个问题写代码。

- 窗口：`python jev_gui.py`（三段式：① 给材料 → ② 提问 → ③ 它的判断）
- 命令行：`python jev_cli.py --help`
- 只用标准库，不需要装 `typesafe-sdk`；key 放环境变量或 `.env`
- 与 TypeSafe AI 没有隶属关系，只是调用官方文档里的公开接口

## License

MIT — see [LICENSE](LICENSE).
