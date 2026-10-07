# Capability-Bound Admission Diagnosis / Capability 限位准入诊断

## Scope / 范围

This diagnosis records the provider-neutral numerical admission failure observed in
`task_e3949a368fad4e3d`. It concerns the ownership boundary between no-motion route
readiness and Runtime command admission. It is not specific to RGB ordering, a
color, an entity, a candidate index, a camera, or an arm.

本文记录 `task_e3949a368fad4e3d` 暴露的通用数值准入故障，范围是无运动路线准备与
Runtime 命令准入之间的所有权边界；不绑定 RGB 排列、颜色、实体、候选编号、相机或机械臂。

## Authoritative Event Chain / 权威事件链

- `grasp.propose` completed and produced candidates.
- `manipulation.prepare` completed and selected `candidate://e1/27` for the left arm.
- `object.acquire` started as `invocation://object-acquire/d707ac058ab24306`.
- The Runtime executed 602 simulator steps and reached the `contact` phase.
- The controller rejected one command with `joint position exceeds capability bounds`.
- Stop was confirmed, but world change had started and the physical outcome remained unknown.

The rejected command was contact segment sample 204, global command sample 582:

```text
panda_joint5 command = 2.8973000049591064 rad
capability upper     = 2.8973 rad
difference           = 4.959106458812812e-09 rad
```

## Root Cause / 根因

CuRobo supplied a float32 representation of the physical upper bound. Readiness
validated it against CuRobo limits using a separate `1e-5` comparison. The Runtime
controller validated the serialized command against the MotionCapability decimal
using strict comparison. Two individually reasonable implementations therefore
disagreed on the exact persisted command.

CuRobo 输出了同一物理上限的 float32 表示；Readiness 用独立的 `1e-5` 比较验证
CuRobo limits，Runtime controller 则把序列化命令与 MotionCapability 十进制上限严格比较。
两个局部实现各自可运行，但对同一持久化命令给出相反结论。

Git, version identifiers, primary keys, transactions, types, and the previous unit
tests cannot establish cross-stage numerical equivalence. The missing mechanism is
one shared pure admission rule at the existing irreversible command boundary, plus
a no-motion call to that rule before a plan is persisted.

## PAOS Ownership Resolution / PAOS 所有权修复

1. `robotwin_capability_controller` owns the only capability-bound canonicalization rule.
2. The rule accepts exact bounds and canonicalizes only float32 round-trip error to the declared bound.
3. Any larger violation remains rejected; declared limits are never expanded.
4. Route readiness applies the controller rule to the selected arm's MotionCapability before persisting an execution plan.
5. Persistent Action applies the same rule while loading the exact prepared plan, before any simulator step.
6. The live controller applies the same rule immediately before the provider write.

This keeps planning, readiness, admission, and execution separate while making their
numerical contract identical. The Agent still selects tools and evidence; the
Coordinator and Runtime do not choose a replacement candidate, arm, route, target,
or Action.

## Safety Boundary / 安全边界

- No broad epsilon or percentage expansion is introduced.
- Only the representational difference produced by round-tripping a declared bound through float32 is canonicalized.
- Non-finite, wrong-length, invalid-bound, and materially out-of-range commands fail closed.
- A legacy prepared plan with a material violation is rejected before motion with `prepared_execution_capability_mismatch`.
- This diagnosis and its tests execute no Gateway Action, simulator step, or hardware motion.

## Required Regression / 必需回归

- Exact lower and upper bounds pass.
- The observed `2.8973000049591064` representation is canonicalized to `2.8973`.
- A material violation such as `2.89731` fails before provider write.
- Readiness, prepared-plan admission, and controller write receive the same normalized command.
- Existing planner-native failure and controller stop/fault behavior remain fail-closed.
