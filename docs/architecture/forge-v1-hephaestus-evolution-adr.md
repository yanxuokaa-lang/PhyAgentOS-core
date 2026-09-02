# Forge v1.0 Hephaestus Evolution Boundary

> Status: supplemental ADR. Normative contracts remain in the v1.0 Forge and Experience manuals.
>
> 决策：PAOS 是控制面和学习面；Hephaestus 只提供可验证的能力实现、失败归因和经验来源。

## Decision

PAOS owns the immutable execution and learning lineage:

```text
ToolExecutionRecord
  -> AgentTask / PlanRevision
  -> VerificationVerdict
  -> redacted TaskEpisode
  -> ExperienceCoordinator
  -> LessonCluster / SkillCandidate
  -> scoped Skill activation
```

Hephaestus-derived perception, grasp proposal, preparation, planning, and backend evaluation are
implemented behind Gateway ToolEndpoints or Skill Bundle providers. PAOS core does not duplicate
their physical truth, policy state, receipts, or Runtime state.

## Ownership rules

| Concern | Owner | Evolution implication |
|:--|:--|:--|
| physical state and effect | Gateway provider/adapter | only terminal Tool facts enter PAOS |
| caller/task correlation | PAOS `AgentTaskCoordinator` | binding, revision, invocation, and attempt remain distinct |
| user-level success | generic verifier | capability facts cannot satisfy criteria by themselves |
| evidence validity | Forge evidence collector and policy | opaque artifact references are not automatic evidence |
| failure attribution | Experience attribution guard | unknown/cancelled/stopped facts block promotion |
| reusable workflow | Skill candidate/evolution manager | requires complete, attributable, independently evaluated episodes |

## Promotion boundary

An Action success is not a reusable Skill. A terminal episode may support a candidate only after the
generic verifier has produced a valid task verdict and the episode passes redaction, workflow-scope,
independent-support, and abstraction checks. A simulator-only result remains profile-scoped until
matched, held-out, hazard, and (when claiming transfer) hardware evidence are available.

Lessons are advisory. They may suggest a verification checkpoint, but cannot establish a criterion,
replace execution facts, authorize motion, or bypass a fresh binding/context check. A single Tool
record, capability projection, benchmark score, or evaluator string cannot directly promote a Skill.

## Failure and recovery

`unknown`, `cancelled`, `stopped`, malformed capability summaries, and projection errors remain
diagnostic or attribution-blocking facts. They do not become successful experience and do not cause
automatic retries. Recovery appends a `PlanRevision` to the same `AgentTask`; prior failures remain
visible in the episode lineage.

## Migration rule

When a historical Hephaestus component is useful, migrate its semantic responsibility, not its class
hierarchy:

- perception → provider-neutral Query and evidence-bearing observation;
- grasp proposal → candidate Query with provenance and no motion authority;
- planner/readiness → bounded preparation Query;
- physical grasp/place → bounded Action with Gateway-owned invocation lifecycle;
- evaluator → backend fact plus generic PAOS verification input;
- self-evolution → existing `TaskEpisode`, `LessonCluster`, and `SkillCandidate` stores.

No second Skill registry, receipt store, verifier, promotion service, or execution protocol is added.

## 中文结论

自我进化的学习对象是“经过验证的工作流如何改变未来 Skill-use”，不是某个孤立工具调用的
输出。Hephaestus 的能力可以成为 Bundle/provider 的实现来源，但 PAOS 继续独占 AgentTask、
Verification、TaskEpisode、Lesson 和 Skill promotion 的生命周期与边界。
