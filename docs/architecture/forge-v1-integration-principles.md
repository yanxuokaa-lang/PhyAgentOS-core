# Forge v1.0 Integration Principles

> Status: supplemental project architecture decision, not a replacement for the normative
> [Developer Manual](../en/03-developer-manual.md), [Forge Integration Contract](../forge/README.md),
> or [Integration Guide](../user_development_guide/README_en.md).
>
> 基线：PAOS v1.0.0 `c5740a5` (`origin/main` / `upstream/main`).

## 1. Scope and authority

The official v1.0 manuals define current behavior. This document records how the project will
adapt reusable Hephaestus perception, grasping, evaluation, and self-evolution ideas to PAOS. It
does not add a Runtime contract, Agent tool, Gateway route, or safety authority.

官方 v1.0 手册是当前行为的唯一规范来源。本文件只记录项目如何把 Hephaestus 中可复用的
感知、抓取、评测和自我进化思想适配到 PAOS；不新增 Runtime 契约、Agent tool、Gateway 路由
或安全权威。

## 2. Single execution plane

```text
Agent
  -> ForgeToolClient
  -> Gateway /tools and /invocations
  -> ToolEndpoint
  -> provider / simulator / hardware adapter
```

`AgentTask` aggregates the user goal, immutable `PlanRevision` records, execution facts, evidence,
and verification. It never directly executes a robot. Gateway `ToolResult` and invocation events
are execution authority; `TaskVerificationContract` and the generic verifier own the user-level
verdict; `ExperienceCoordinator` runs only after a terminal task episode is available.

`scene.observe`, `scene.understand`, `grasp.propose`, and `manipulation.prepare` are provider-neutral
Query contracts. `object.acquire` and `object.place` are bounded Action contracts. A Session is
introduced only when an Endpoint owns state or resources that must persist across calls; correlation
alone is not a Session.

## 3. Extension points

Every capability must enter through the smallest existing PAOS extension point:

| Need | v1.0 extension point | Must not become |
|:--|:--|:--|
| synchronous measured data | Query `ToolSpec` + `ToolEndpoint` | a vendor-specific Agent API |
| bounded physical effect | Action `ToolSpec` + Gateway invocation | a direct Agent-to-SDK call |
| owned persistent resource | Session `ToolSpec` with explicit ownership | a cross-Tool lease |
| simulator or hardware differences | Skill Bundle profile + Gateway provider/adapter | PAOS core imports of simulator SDKs |
| task success | `AgentTask.finalize` + `TaskVerificationContract` | a `task_outcome` Tool |
| learning from completed work | `TaskEpisode` + `ExperienceCoordinator` | per-call promotion or execution authority |

RoboTwin, SAPIEN, XPolicyLab, embodiment names, benchmark task names, and evaluator internals
remain adapter/profile metadata. They cannot be required fields of public provider-neutral ToolSpecs.

## 4. Safety and evidence invariants

- Missing calibration, stale observations, invalid frames/units, malformed references, and unknown
  remote outcomes fail closed.
- A prepared candidate is not an IK proof, collision proof, or action admission.
- `capability_outcome_summary_v1` may be projected as `execution_fact_only`; it always carries
  `task_success_authorized=false` and never enters the evidence allowlist by artifact URI alone.
- Evidence is workspace-relative, validated, and provenance-bearing. Best-effort capture is not
  silently upgraded to authoritative evidence.
- Fake and conformance profiles remain no-motion. Hardware or simulator acceptance is conditional
  on independently installed, matching artifacts and explicit operator authorization.

## 5. Historical terminology mapping

The following mapping is for migration readers only; it is not an instruction to port old code:

| Historical preview term | PAOS v1.0 interpretation |
|:--|:--|
| Session-centered Runtime | Forge Tool API execution plane plus Skill Runtime lifecycle |
| Target / rollout target | Gateway provider/adapter selected by a Skill Bundle profile |
| Target session handle | ToolInvocation plus PAOS `ToolExecutionRecord` |
| Runtime observation | Query Tool and, for task evidence, Forge observation capture |
| Session verifier | PAOS generic Verification Service |
| session outcome | AgentTask finalization and `VerificationVerdict` |
| global Lessons file | version-scoped Lessons supplied by `ExperienceCoordinator` |

Do not rename these terms mechanically when a historical object had different ownership. Re-express
the behavior at the v1.0 boundary and keep implementation details inside the adapter that owns them.

## 中文摘要

PAOS v1.0 的核心是“Tool API 执行事实”和“AgentTask 用户级判定”分离。Hephaestus 的任何能力
都必须先落到 ToolEndpoint、ToolSpec、Skill Bundle profile、provider/adapter 或现有
Experience 扩展点；不能把旧 Target、Session、Verifier 类名直接变成新的 PAOS 公共接口。
