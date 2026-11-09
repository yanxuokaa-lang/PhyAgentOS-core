# Omarchy issue classifier

Classify the [Omarchy](https://github.com/omacom/omarchy) issue backlog with
[Jev](https://typesafe.ai), TypeSafe AI's System One model. Ten questions per issue, answered
in one request, for roughly a hundredth of a cent each.

The questions are written for Omarchy specifically: its components, its kinds of bugs, its
severity language. That is the point rather than a limitation. The option list is where the
domain knowledge lives, and a generic one would be useless to everybody.

Jev does not write text. You give it something to look at and questions with fixed sets of
answers, and it returns the answers with calibrated probabilities. That makes it a good fit
for triage, where the answers are known in advance and the volume is high.

```
$ ruby classify.rb --limit 200
Fetching open issues from omacom/omarchy...
Classifying 200 issues with 10 questions each (2000 answers), 8 at a time...
Classified 200 of 200 issues in 5.8s
2000 answers, 419073 input tokens, $0.0176 at $0.042/MTok
Wrote triage.csv

By component:
  shell_menu           39
  power_sleep          23
  input                21
  apps                 20
  graphics_drivers     19
  ...
```

## Setup

You need Ruby 3.x, the [`gh` CLI](https://cli.github.com) already authenticated, and a
TypeSafe API key from [the console](https://console.typesafe.ai/settings/keys).

```bash
export TYPESAFE_API_KEY=apikey_...
gh auth status          # should already be logged in
ruby classify.rb --limit 20
```

No gems. Standard library only.

## Usage

```bash
ruby classify.rb                            # every open issue in omacom/omarchy
ruby classify.rb --repo owner/name          # another repo (rewrite questions.json first)
ruby classify.rb --limit 50                 # try it cheaply first
ruby classify.rb --out triage.csv           # where the CSV goes
ruby classify.rb --concurrency 16           # requests in flight
ruby classify.rb --state closed             # open, closed or all
```

| Flag | Default | What it does |
|---|---|---|
| `--repo` | `omacom/omarchy` | Repository to classify. Other repos need new questions |
| `--limit` | all | Only the N most recent issues |
| `--out` | `triage.csv` | Output file |
| `--concurrency` | 8 | Requests in flight |
| `--questions` | `questions.json` | Question definitions |
| `--state` | `open` | `open`, `closed` or `all` |

## What it asks

The questions live in `questions.json` so you can change them without touching Ruby. Editing
that file for your own project is the first thing you should do.

> **Using this on your own project?** Rewrite the `component` options before anything else.
> Pointed at `rails/rails` unchanged, all eight issues came back `other`, which is the correct
> answer: none of them are about Hyprland or suspend. The model can only choose from the options
> you give it. Rewriting that list for your domain is the actual work, and it is most of the
> value here.

| Question | Type | Returns |
|---|---|---|
| `type` | choice | bug, feature request, support question, documentation, packaging, discussion |
| `component` | choice | one of fourteen subsystems |
| `severity` | score | a position on a four-level scale |
| `names_hardware` | yes/no | does it name specific hardware |
| `hardware_dependent` | yes/no | would it only happen on that hardware |
| `has_repro` | yes/no | are there steps, commands or logs |
| `actionable` | yes/no | enough to start work without asking for more |
| `defect_upstream` | yes/no | does the faulty code live upstream |
| `fix_in_omarchy` | yes/no | could this project fix it anyway |
| `regression` | yes/no | did it break after an update |

All ten are answered in a single request. Adding an eleventh costs almost nothing, because
the model answers them in parallel rather than one after another. Ask everything you might
want to know and let your spreadsheet decide what matters.

## What you get

One row per issue. Choices and scores come with a confidence value, and yes/no questions come
back as probabilities rather than true and false, so you can pick your own threshold later
without re-running anything.

```csv
number,title,url,created_at,existing_labels,type,type_confidence,component,component_confidence,severity,severity_confidence,names_hardware,hardware_dependent,has_repro,actionable,defect_upstream,fix_in_omarchy,regression
12411,Codex usage collector rereads GB of history,https://...,2026-09-18T15:06:27Z,,bug,1.0,shell_menu,0.76,1.94,0.88,0.97,0.07,0.98,0.86,0.31,0.6,0.13
```

`severity` is a position on the scale, not an index, so 1.94 means "essentially level 2, with
a little pull toward level 1".

## Reading confidence

Confidence is the most useful column and the easiest to ignore. It tells you how peaked the
model's probability distribution was, so a low number means the options genuinely overlapped
for that issue.

A reasonable pattern is to act on the confident answers and put the rest in front of a person:

```ruby
CSV.foreach("triage.csv", headers: true) do |row|
  if row["component_confidence"].to_f >= 0.8
    apply_label(row["number"], row["component"])
  else
    queue_for_human(row["number"])
  end
end
```

Confidence does not mean correctness. It means the model was not torn between options.

## Editing the questions

Three question types:

- **choice**: pick one of up to 255 options. `criteria` is a map of option name to description.
- **score**: place the issue on an ordered scale. `criteria` is a list of level descriptions.
- **noul**: a yes/no question. Returns the probability that the answer is yes.

The option *names* are never shown to the model, so all the meaning has to live in the
descriptions. `{"shell_menu": ""}` tells it nothing.

Ask one thing per question. If a question contains the word "and", it is probably two
questions, and you will get muddled answers. We learned that the hard way: a single
`hardware_specific` question was quietly asking both "does it mention hardware" and "does it
depend on hardware", and those have different answers for most issues.

## A note on untrusted text

Issue bodies are written by strangers. Text inside the input can influence the answer, so the
issue goes into its own named field and every question refers to it by path, like
``Does `issue.body` mention...``. Do not splice issue text into an instruction. This matters
more if you point this at something adversarial, such as security reports.

## Cost and speed

Measured on the Omarchy backlog, 2,093 open issues:

| | |
|---|---|
| Wall clock | about a minute |
| Cost | under 20 cents |
| Rate | roughly 35 issues per second |

Input runs $0.042 per million tokens and output is free. Most of the cost is the question
text, which is re-sent with every request, so trimming questions you do not use saves more
than trimming issue bodies.

## Limits worth knowing

- A choice question takes at most **255 options**.
- The whole request, issue text plus questions, has a budget of about **32,000 tokens**.
  Bodies are truncated at 6,000 characters to stay well inside it.
- Jev is **text only** and does not read screenshots, which is a real gap for issues whose
  substance is a picture.
- Answers are **not deterministic**. Running twice can move a probability slightly and flip a
  borderline call.

## Licence

MIT.
