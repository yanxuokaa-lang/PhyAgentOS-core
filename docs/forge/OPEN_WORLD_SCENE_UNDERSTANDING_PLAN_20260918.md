# Open-World Scene Understanding Plan

## 1. User requirement

The current RobotWIN route must recognize more than salient movable objects.
For example, Qwen3-VL may identify three colored blocks and their image-plane
ordering while omitting a visible tabletop and the semantic relation that an
object is supported by it. The fix must remain useful when later benchmark
scenes contain shelves, containers, articulated parts, hooks, obstacles, or no
depth sensor.

The requirement is therefore not a tabletop detector and not a forced model
upgrade. The implementation and acceptance path intentionally remains on the
existing Qwen3-VL-4B vLLM provider; no Qwen3-VL-8B service is part of this
change. It is a task-agnostic open-world scene-understanding path that keeps
semantic facts, sensor geometry, persistent planning facts, and motion
authorization in their existing owners.

## 2. PAOS ownership contract

```text
observation artifacts
        |
        v
VLM adapter: visible semantic entities, relations, ambiguities
        |
        v
Adapter RGB-D composition: optional metric envelopes/artifacts
        |
        v
Coordinator: durable Tool facts, evidence refs, PlanRevision history
        |
        v
PlanGraph: node-local required/produced evidence and readiness
        |
        v
AgentLoop: bounded node projection and evidence-gap recovery
        |
        v
existing binding/readiness/Gateway admission
```

PAOS Core remains provider-neutral. No `tabletop`, `rgb_cube`, task-specific
object field, second task state machine, second execution protocol, new hash,
or extra motion gate is introduced by this feature.

## 3. Semantic provider contract

The VLM receives an open-world prompt. It is asked to enumerate clearly
visible objects and physical structures, including large or low-contrast
structures, and to report relations from general families:

- directional and relative image relations;
- topology, containment, overlap, and occlusion;
- visible contact, support, attachment, and hanging relations;
- visible state such as open, closed, articulated, or blocked.

The VLM must not infer metric depth, world coordinates, plane equations,
simulator truth, IK, task success, or motion authorization. A semantic
support claim is allowed when visually evident; its metric geometry remains
owned by RGB-D composition. Ambiguity remains explicit in the existing
`ambiguities` field.

The public projection remains the existing
`entities`/`relations`/`spatial_envelopes`/`ambiguities` contract. Provider
attributes remain private to the adapter and are not added to PAOS Core.

## 4. AgentLoop and planning contract

The VLM prompt does not receive a closed-world list of task objects. A
PlanNode may still declare the evidence required for its own downstream
operation through the existing `required_evidence` field. Missing evidence
blocks that node; it does not globally require a support surface for every
benchmark.

The node turn receives only the current node, immutable binding identity,
direct-predecessor facts, and bounded ambiguity/evidence references. It does
not receive the complete discovery transcript or task-wide Tool history.
Evidence recovery uses the existing PlanningLoop/LongHorizon continuation
boundary: append a bounded observation revision, request clarification, or
remain blocked. A successful revision handoff yields immediately and does not
execute a successor node in the old model turn.

## 5. Evaluation contract

Evaluation is read-only and no-motion. It stores a unique run directory with
the selected screenshot manifest, provider/model configuration, raw provider
JSON, normalized results, latency/route metadata when available, and summary
metrics. It never calls Gateway, Action, Session, simulator stepping, or
hardware IO.

The initial corpus spans multiple RobotWIN artifact roots and captures rather
than one RGB task. Evaluation checks raw-to-normalized preservation of
entities, structural relations, ambiguities, and provider failures. It does
not require every scene to contain a support surface; it checks that the
generic contract remains stable when a scene does or does not contain one.

## 6. Acceptance dimensions

1. Architecture: semantic provider, Adapter composition, Coordinator,
   PlanGraph, AgentLoop, and Gateway ownership remain separated.
2. Semantic quality: low-salience structures and general relation families
   are permitted without task-specific object lists or metric hallucination.
3. Evidence integrity: any metric envelope/artifact retains observation,
   scene, frame, calibration, and source provenance; insufficient evidence is
   explicit rather than guessed.
4. AgentLoop continuity: node-scoped projection, direct-predecessor payload,
   bounded continuation, and no same-turn successor execution are preserved.
5. Robotics safety: no Action or motion authority is reachable from semantic
   output or the screenshot evaluator.
6. Observability: raw provider output, normalized output, route/failure and
   evaluation metadata make model-vs-adapter loss diagnosable.
7. Cross-benchmark reproducibility: multiple RobotWIN tasks/captures use the
   same contract and unique output roots; old evaluation results are not
   overwritten.
