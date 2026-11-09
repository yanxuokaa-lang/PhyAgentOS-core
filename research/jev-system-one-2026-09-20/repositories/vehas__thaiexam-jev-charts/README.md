# Jev on ThaiExam — charts

Static chart pages from evaluating [TypeSafe](https://typesafe.ai)'s **Jev** (`jev-1.13.0`), a System One
model, on Thai standardized exams alongside 110 other language models.

**→ [View the charts](https://vehas.github.io/thaiexam-jev-charts/)**

| Page | What it shows |
| --- | --- |
| [Cost and speed vs accuracy](https://vehas.github.io/thaiexam-jev-charts/cost-speed-vs-accuracy.html) | 111 models scored on the same 375 questions, with thinking models highlighted |
| [Confidence calibration](https://vehas.github.io/thaiexam-jev-charts/calibration.html) | Whether Jev's stated confidence predicts correctness, over 567 questions |

Both pages have an English / ไทย toggle. Each is a single self-contained HTML file — data inlined,
Chart.js from a CDN, no build step.

## Headline numbers

Jev answered 567 ThaiExam questions at **70.7%** accuracy, **0.35 s** and **$0.000029** per question —
the fastest and second-cheapest model in the comparison, and mid-pack on accuracy. Its stated confidence
tracks observed accuracy closely (expected calibration error **7.5 pp**), which makes it a useful routing
signal even where its raw score does not lead.

## Credits

- Original data and results: [ai-vs-thai-exams.pages.dev](https://ai-vs-thai-exams.pages.dev/)
- Benchmark harness: [dtinth/thaiexamjs](https://github.com/dtinth/thaiexamjs)
- Exam questions: [ThaiExam dataset](https://huggingface.co/datasets/scb10x/thai_exam) (SCB 10X) and the
  [OpenThaiGPT evaluation dataset](https://huggingface.co/datasets/openthaigpt/openthaigpt_eval)
