# 发明 RLHF 的人，这次做了个不会说话的模型

**两千多万人围观的 Jev，我用中文测了 50 条。**

52 页 PDF，10 张图，143 条能回溯到出处的数字。免费，随便转。

[**下载 PDF**](发明RLHF的人这次做了个不会说话的模型.pdf) · [章节源文件](draft/) · [数据表](data/数据表.json) · [50 条中文实测](data/中文实测/)

<p align="center"><img src="assets/封面.png" width="420" alt="封面"></p>

## 它是什么

Jev 是 TypeSafe 在 2026 年 9 月 15 日发布的模型。创始人 Diogo Almeida 是 RLHF 的共同发明人之一。

这个模型不生成文字。你给它一段材料和一道题（选哪个、打几分、是不是），它返回选项和概率。输入价每百万 token 0.042 美元，输出免费。主页写它比前沿模型快 193.6 倍、便宜 444.6 倍。

Hacker News 上的发布帖拿了 1,831 分、480 条评论，一半在吵。

这本书干的事只有一件：查这些数字是谁量的、怎么量的，再自己拿中文测一遍。

## 三个现在就能拿走的东西

**1. 给你的智能体的一页。** 把 [这一页](assets/附录三-发给智能体.png) 整页复制发给 Claude Code 或 Codex，它会自己装技能、让你去申请 key、跑一条冒烟，然后在你的项目里找出三个能交给 Jev 的判断点。key 不要贴进对话框，那页上写了原因。

**2. 五个不需要专业知识的问题。** 任何人拿一个"很准很快很便宜"的模型来找你，问这五句就够：

- 它说九成把握的时候，你数过实际对了几成吗？
- 这个数字的分母是谁的答案？
- 这个倍数是和谁比、比的是哪一段？
- 你的任务能不能拆成要不要、选哪个、打几分？
- 它不会做的那八件事里，你的任务碰到几件？

每一句背后的数字在第 10 章。

**3. 一页速查。** [全书关键数字](assets/数据速查页.png)，每格一个数、一句口径、一行来源。截图就能发。

## 书里查出了什么

**厂商的 444.6 倍是峰值。** 四份独立测试量到的提速是 5 到 25 倍，最保守的一家给的成本优势是 1.6 倍。倍数能不能用，取决于和谁比、比哪一段。

**"零幻觉"说的是零类型错误。** 它不会给出选项之外的答案，不等于不会选错。Every 的测试里它漏掉了 7 处毛病里的 1 处。

**67.8% 那个总分的分母不是人。** 标准答案是 GPT-6 Astra 与 Claude Fable 5.1 的平均。换一批批卷子的老师，分数就会变。

**中文 50 条实测：90 个判断对了 86 个，95.6%。** 校准误差 ECE 0.070。70 个 Noul 与 Choice 判断按胜出概率 0.80 划线：66 个自动放行，放行部分 100% 正确；转人工的 4 个里包住了这 70 个判断的全部 3 个错判。样本是单人标注、素材自编，能证明的只有"这 50 条中文样本上它表现如何"，再往外推一步都不成立。

**它到底是新架构还是精调过的编码器换了个壳？** 现有公开证据分不出来。书里把两个假说和能分辨它们的三样东西都列了，三样目前都没有。

## 报告结构

| 幕 | 章 | 一句话 |
|---|---|---|
| 序章 | | 2026 年 9 月 16 日，Every 的评测负责人把 37 篇文章丢给一个模型，0.7 秒 777 个判断，不到半美分 |
| **第 1 幕 建立** | 1 起源 · 2 关键区分 | 发明 RLHF 的人问了四年"聊天超人了，自动化在哪"；咖啡师不抄你的句子，只在杯子上打勾 |
| **第 2 幕 推翻** | 3 谁去查的 · 4 第一个坏消息 · 5 更难的那个 | 厂商拿两个前沿模型的共识当标准答案；峰值和实测差一个数量级；新架构还是换壳，证据分不出来 |
| **第 3 幕 剩下什么** | 6 真正有证据的五件事 · 7 十四个人已经拿它干了什么 · 8 你自己的处境 · 9 正在发生的事 · 10 工具箱 | 重排、技能路由、门卫、引文核对、特征抽取；十四个开源仓库六种玩法；分人群的接入建议；五个问题、红旗清单、一周接入日程 |
| 尾声 · 附录 | 词汇表 · 文献 · 给智能体的一页 · 速查页 | |

尾声那句话：拿它反复做"要不要、选哪个、打几分、下一步干什么"；真正需要生成代码、写文章和复杂推理时，再交给传统大模型。

## 复现 50 条中文实测

样本、脚本、每一次调用的原始返回都在 [`data/中文实测/`](data/中文实测/)。

```bash
cd data/中文实测
export TYPESAFE_API_KEY=你自己申请的key    # https://console.typesafe.ai/settings/keys
python3 run.py        # 50 条 × 4 次 = 200 次调用，约 4 分钟，花费约 $0.005
python3 analyze.py    # 写出 summary.md 与 metrics.json
```

`samples.json` 里的标准答案在测试开始前已锁定，文件的 sha256 记在 `summary.md` 里。你换成自己的样本，跑出来的数字才是你的。

这次测量的出口 IP 在马尼拉，延迟数字不代表中国大陆直连。

## 数字怎么核

正文里每个数字后面有一个上标编号，对应 [`data/数据表.json`](data/数据表.json) 的一条记录：

```json
{"id": "T1", "value": "95.6%（86/90）",
 "basis": "50 条中文样本、90 个判断里判对的比例；gold 由单人标注，测试前锁定",
 "tier": "本报告实测", "verified": true}
```

`tier` 分六档：厂商文档、厂商评测、独立测试、社区、本报告实测、公开新闻。`verified` 为 `true` 只有一种情况：填表的人在本机原料里亲眼读到了这个数。转引未回源的一律 `false`，正文用"据 X 转述"标出。

厂商评测页的原始解析和对账在 [`data/evals_核对说明.md`](data/evals_核对说明.md)。网上流传的"Jev 76.0%"是从四个不同工作流里各挑一个数拼出来的，对账过程在那份文件里。

## 重建 PDF

```bash
uv venv --python 3.12 .venv && uv pip install playwright && .venv/bin/python -m playwright install chromium
STRICT_FIGS=1 .venv/bin/python render.py build.py 报告.html 报告.pdf
```

需要 poppler（`pdftoppm`、`pdftotext`）做自检。`build.py` 只认 [`BRIEF.md`](BRIEF.md) 第五节的 markdown 方言，图的数据全部从 `data/` 绑定，手打的数字过不了构建。

## 许可

代码 MIT，报告文本与数据 CC BY-NC-SA 4.0。详见 [NOTICE.md](NOTICE.md)。

作者与 TypeSafe 无任何关系。50 条实测自费，总花费 $0.0046。

## 致谢

排版规范与渲染脚本来自 [alchaincyf/huashu-report](https://github.com/alchaincyf/huashu-report)。独立测试的数据来自 Every、Near Here、Good Start Labs 与 DSPy 社区分支。十四个案例仓库的作者在发布后三天内就把东西做出来了，书里每一个都有名字。

---

## English

**An independent, Chinese-language report on Jev, the non-generating "System One" model from TypeSafe AI.** 52 pages, 10 charts, 143 traceable data points, plus a reproducible 50-sample Chinese evaluation.

What it checks: who measured the vendor's 193.6× / 444.6× claims and how (independent tests land at 5–25× speed, 1.6× cost at the conservative end); what "zero hallucination" actually means (zero type errors, not zero mistakes); why the 67.8% headline score has two frontier models as its denominator instead of humans; and how the model behaves on 50 Chinese judgment tasks (86/90 correct, ECE 0.070, and a 0.80 confidence gate on the 70 Noul/Choice judgments that auto-passes 66 with 100% precision and routes all 3 of their errors into the 4 sent to a human).

Everything is in Chinese. The data files are language-agnostic: [`data/数据表.json`](data/数据表.json) holds every number with its source and verification status, [`data/中文实测/`](data/中文实测/) holds the raw API responses.
