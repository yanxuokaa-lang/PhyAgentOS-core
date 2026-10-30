# GraspNet Task-Affordance Selection Diagnosis

## Decision

GraspNet remains a grasp-pose proposal mechanism. Its score is not a task-level choice. A task-qualified grasp is established by evaluating a grasp candidate together with the relevant process-feature candidate(s), then explicitly selecting an opaque qualified combination through PAOS AgentLoop and revalidating it in no-motion Preparation.

```text
same observation
  ├─ Grasp Provider: grasp candidates (pose/contact/approach/score)
  └─ Process-feature Provider: opening/axis/end-role candidates
          ↓ same entity + capture identity
  Task-affordance Provider: eligible opaque grasp/feature combinations
          ↓ exact direct-predecessor outputs only
  AgentLoop selection receipt → no-motion Preparation revalidation → Action
```

## Task-specific semantics

For pouring, the task intent is to grasp a supported bottle-body region while preserving access to the opening and allowing the attached bottle to attain the requested pour relation to the destination. The opening/rim candidate is not automatically a pour lip or flow direction; those facts need their own evidence.

For stirring, the grasp should lie on the rod shaft and leave the task-selected working end usable. The two endpoints are process features, not grasp locations. If geometry/task evidence cannot distinguish endpoint roles, the qualification result is ambiguous and no Action is admitted.

These are semantic constraints, not fixed world coordinates. Geometry-dependent qualification belongs in a replaceable Provider/Adapter and must use current observation-bound evidence. Opaque references and stable role semantics cross into PAOS; USD prim paths, SDK objects, raw point arrays and embodiment-specific fields do not.

## Why a new qualification stage is needed

Current GraspNet candidates provide generic pose proposals and score. Current process-feature Query separately publishes opaque feature references. The current task binding can carry a preferred grasp, but that does not establish a relationship between the chosen grasp, bottle opening/rod role, and the requested operation. Selecting highest score or selecting a rim/endpoint independently can yield an unusable, occluding, unstable, unreachable, or semantically reversed grasp.

Therefore qualification must happen before AgentLoop selection, and Preparation must verify the exact selected refs again. This is a domain capability seam only if it composes existing Query, ToolSpec argument-source, PlanGraph predecessor, Provider, and Preparation patterns; it must not create a second lifecycle owner.

## Failure policy

The qualification Query returns no eligible candidates or explicit ambiguous/unavailable status when geometry is occluded, evidence is stale/mismatched, entity joins disagree, the rod ends are unresolved, a bottle opening is not established, or the Provider fails. AgentLoop must select refs only from the successful direct predecessor. Preparation checks the exact query identity and the provider's no-motion geometric qualification. Any non-available status fails the node, keeps Action not-ready, and produces zero Action invocations.

## Acceptance evidence

Contract tests can prove interface substitutability, AgentLoop source lineage, freshness checks, and zero-action failure behavior. They cannot prove the current LabUtopia glass geometry or robot reachability. Those require a fresh no-motion Isaac observation and Adapter/robot kinematic validation; live motion remains a separate explicit authorization boundary.

## Implementation Status (2026-10-30)

The Isaac Adapter now joins grasp and process-feature candidates from the same capture, qualifies bottle-body support and opening clearance from the observed point cloud, and derives the stirring working end as the rod endpoint farther from a shaft grasp. Preparation revalidates the opaque combination and capture identity without moving the robot. This remains geometric candidate qualification, not proof of IK reachability, collision-free execution, vessel interior, or successful liquid flow.

Current final-USD vessel features identify an opening rim only. They do not establish which point is a pour lip or a valid outward flow direction, so pouring remains unavailable until that evidence is produced by a replaceable feature Provider and validated in a fresh no-motion capture. The present simulator-truth rod endpoint ordering is geometric, not user/task semantic; the farther-from-grasp rule is only a working-end heuristic and must remain ambiguous when evidence cannot distinguish the usable end.

The repository tests cover body-vs-opening grasp qualification, same-capture reference revalidation, stale/fabricated Preparation selections, rod endpoint ambiguity, and selection of the endpoint opposite an off-center shaft grasp. These tests do not constitute live Isaac geometry or motion evidence.
