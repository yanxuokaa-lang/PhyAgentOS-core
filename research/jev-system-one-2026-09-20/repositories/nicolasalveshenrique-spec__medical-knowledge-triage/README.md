# medical-knowledge-triage

> **Status: pre-access architecture prototype.**
>
> - Jev has **not been run** in this project yet.
> - The gold cases currently validate **only the deterministic policy**, using hand-written mock
>   answers.
> - This is **not clinical decision support**. It routes *study knowledge* (what to keep, merge,
>   or turn into a flashcard). It makes no decisions about patients, diagnoses, or treatment.

**Can a System One model make the triage decisions in a real medical student's study workflow,
and where does it fall short?**

I am a medical student. Every lecture, group tutorial, and article produces candidate pieces of
knowledge. Each one needs a decision before any studying or flashcard writing happens: is this
knowledge, do I already have it, can I rebuild it, is it worth keeping, and in what form?

This repository specifies that decision as a set of narrow, typed questions for
[Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), plus a deterministic policy
that turns the answers into an action.

## The principle

> **Jev interprets. Code applies the policy.**

```text
candidate knowledge + the few existing items retrieved as relevant
        │
        ▼
   Jev — ONE call, seven questions
   ├─ is_study_atom                    Noul
   ├─ knowledge_status                 Choice
   ├─ derivable_from_known_knowledge   Noul
   ├─ requires_independent_recall      Noul
   ├─ has_long_term_learning_value     Noul
   ├─ is_volatile                      Noul
   └─ representation                   Choice
        │
        ▼
   policy (deterministic code, provisional thresholds)
        │
        ▼
   IGNORE · MERGE · REVIEW · ANKI · KNOWLEDGE_BASE
```

Jev never answers "what should happen to this?". It answers seven small questions, and the
policy composes them. The reasoning is in
[`docs/ADR-001-routing-policy.md`](docs/ADR-001-routing-policy.md).

All seven questions are sent together. Some answers are speculative and are ignored when they do
not apply. In particular, `representation` is read **only** when the policy has authorized
retention; otherwise its answer is discarded.

## Decisions I want to automate

| Decision | How it is asked |
|---|---|
| Is this study content at all, or logistics and noise? | `is_study_atom` (Noul) |
| Is it already covered, a reformulation, a partial overlap, a new fact, or a new link between known items? | `knowledge_status` (Choice) |
| Can it be safely rebuilt from what is already known? | `derivable_from_known_knowledge` (Noul) |
| Does it justify retention: direct recall needed, and value beyond this exam? | two Nouls |
| Does it depend on doses, guidelines, or anything revised over time? | `is_volatile` (Noul) |
| If kept: flashcard, image occlusion, or a relation in the knowledge map? | `representation` (Choice) |

## Provisional policy thresholds

The two answer types carry different signals:

- **Noul** returns `noul`, the probability that the answer is yes. It has no separate confidence.
- **Choice** returns `confidence`, a summary of how peaked the distribution over options is.

The policy compares Noul probabilities and Choice confidences against thresholds scaled to the
cost of a wrong decision:

- **Creating nothing** (discard, covered, merge, derivable) requires **0.90**: Choice confidence
  ≥ 0.90, Noul probability ≥ 0.90 for yes or ≤ 0.10 for no. The costly error here is silent
  loss: a gap wrongly marked "covered" never comes back.
- **Creating an item** requires **0.75** Choice confidence, and a Noul probability of at least
  0.80 for yes or at most 0.20 for no. A redundant card is cheap and gets noticed.
- **Volatile content** goes to review when the `is_volatile` probability is **≥ 0.50**. Missing
  it is the costly error.
- Anything in between goes to **REVIEW**, meaning me.

**0.90, 0.75 and 0.50 are initial heuristics and have not been validated.** They will be
calibrated against the gold cases once there is Jev access.

## Where I expect Jev to fall short

These are the cases I most want to measure:

1. **Volatile clinical content.** "Denosumab is given every six months" can be classified
   perfectly as a new, card-worthy fact and still be outdated by the next guideline. The policy
   never lets a volatile claim through automatically. The question is whether `is_volatile`
   catches it reliably.
2. **Subtle semantic duplication.** Is "cathepsin K degrades type I collagen" a new facet of an
   existing card about "proteases resorb matrix", or the same card? I expect a flat distribution,
   and a flat distribution is the right answer. The failure would be a *confident* wrong call.
3. **Missing context.** `knowledge_status` can only compare against what is in the state. If
   retrieval misses the relevant existing card, a confident `new_fact` will be wrong. This is a
   limit of the pipeline more than of the model, but it is where I expect most real errors.

## Gold cases

[`examples/gold-cases.json`](examples/gold-cases.json) contains the exact seven questions and ten
cases from bone-remodeling physiology. Each case has an `input_state`, hand-written mock
`model_answers` in the documented answer shape, and the `expected_policy_decision`. Every outcome is covered, including two
deliberate failure modes (cases 09 and 10).

- **Now:** they test the policy only. Given these answers, the policy must produce these outcomes.
- **With Jev access:** the same states go to Jev, and the observed answers are compared with the
  gold labels. The cases then become the first evaluation set, and the thresholds get calibrated.

The mock numbers were written by hand. They are not Jev output.

## What is intentionally not here

- **Running code or an API client.** The contract comes first.
- **Integrations with Anki, Obsidian, cloud storage, or any LLM.** They exist in my workflow and
  are out of scope for this decision.
- **Real study material.** No lecture transcripts, book quotations, names, or personal data.
  Examples use general physiology only.
- **Routing between language models.** The output is an action for software, not a model choice.
- **Anything about patient care.** See the status note at the top.

## Glossary

The workflow was designed in Portuguese:

| Here | In the study method |
|---|---|
| candidate | item candidato (conceito ou elo do fluxo) |
| covered | coberto |
| reformulation → merge | reformulação → funde |
| derivable | derivável |
| discarded | descartado |
| review | incerto |
| new_card | novo cartão |
| new_image_occlusion | nova oclusão |
| new_relation | nova relação |
| volatile | `vol::alta` |

## Repository

```text
README.md                            why, and what is automated
docs/ADR-001-routing-policy.md       the rules and the reasons
schema/routing-decision.schema.json  internal contract: input_state, model_answers, policy_decision
examples/gold-cases.json             questions + 10 gold cases
LICENSE                              MIT
```

---

<sub>Drafting and consistency checks were done with AI assistance. The design decisions and the
study method are my own.</sub>
