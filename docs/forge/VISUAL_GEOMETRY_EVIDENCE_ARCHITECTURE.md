# Visual Geometry Evidence Architecture

## Purpose

This document defines how PAOS turns a live RGB-D observation into evidence
that is safe to use for grounding and manipulation. It addresses two reports
that are easy to conflate:

* `metric_3d_unavailable`: an RGB semantic model cannot establish metric scale,
  depth, or a world-frame transform from pixels alone.
* `object_shape_uncertain`: an RGB semantic model cannot establish an
  executable object shape or collision envelope from pixels alone.

Neither report is allowed to erase evidence produced by an independent visual
provider. The adapter preserves the raw semantic result and emits an explicit
reconciliation record when visual metric evidence resolves the first report.

## Evidence ownership

| Evidence | Owner | Allowed use |
| --- | --- | --- |
| Entity/category and semantic relations | injected RGB semantic provider | identify candidates and relations |
| Instance mask | adapter segmentation provider | per-entity support in the image |
| Metric localization | adapter depth + calibration + segmentation provider | metric spatial envelope in the observation frame |
| Visual object geometry | adapter geometry provider, derived from the visual point cloud | conservative dimensions/shape for grasp and route qualification |
| Execution identity and current revision | Runtime adapter | map a bound visual entity to an opaque executable entity |
| DAG conditions and evidence references | PAOS planning layer | admission projection only |
| Motion and terminal outcome | Forge Gateway and Runtime | the only source of physical effects |
| User-level success | ForgeTaskVerifier | final claim only |

Simulator actor pose, simulator half-extents, and simulator collision meshes are
Runtime diagnostics, not visual geometry. They must not be copied into a visual
artifact or presented as perception evidence. Until a visual entity is mapped
to an opaque execution handle, no Action may be admitted.

The binding artifact keeps these two matrices separate: `objects[observed_ref]`
contains observation-derived route geometry, while `scene_facts.objects` retains
the captured Runtime actor pose keyed by execution entity and actor identity.
The visual envelope axes may follow the camera and its estimated centre may
differ from the actor origin. Runtime drift checks compare the current actor
only with its captured execution pose, using the existing tolerance. Missing or
ambiguous captured poses reject the binding; visual geometry is never a fallback
for this check. All aliases are published together only after every actor passes.

Binding failures propagate through the existing preparation Query `error`:
`binding_pose_changed` requires fresh observation/binding;
`binding_pose_unavailable` requires repairing the missing binding snapshot.
These are diagnostics, not motion authorization or an automatic retry policy.

### Observation models are not simulator object frames

An axis-aligned envelope in camera coordinates has a legitimate estimated frame:
the calibrated camera axes translated to the measured envelope centre. This does
not assert that a physical object's orientation is known. The persistent adapter
names that frame `observed-envelope/<entity>` and uses its centroid as the model's
functional origin. It never copies a simulator functional-point offset into the
estimated model. A supplied target transform places this model frame.

Readiness and Action preflight compare route artifacts with the bound observation
model. The existing private Runtime drift check compares actor state only with
its captured execution snapshot. Neither comparison overwrites an estimate or
relaxes drift tolerances. Runtime correspondence and drift rejection remain
simulator-specific identity/safety diagnostics, not perception or planner inputs.

All movable collision objects use bound visual envelopes. Incomplete coverage
returns `observed_collision_coverage_incomplete`; hidden actor boxes are not a
fallback. Support comes from the metric cloud named by observed `on` relations.
The horizontal-support provider estimates a dominant world-Z surface by median
consensus, requires spatial coverage and a bounded fitted slope, and adds the
configured uncertainty to the upper inlier height. All out-of-consensus points
remain in local residual collision boxes; high points do not raise the whole
table and are not discarded. Missing, tilted or ambiguous support prevents
readiness. This remains a sensor-derived model, not a simulator tabletop plane.

The optional adapter route-profile `observed_support` configures
`inlier_distance_m` (0.002), `minimum_inlier_fraction` (0.7), `minimum_points` (30),
`residual_cell_m` (0.02), `uncertainty_m` (0.001) and `maximum_slope` (0.02).
These are estimator assumptions, not values to tune against simulator answers.
The persisted support estimate records its policy, counts, height and slope.

Materialized records label this source `observed_envelope`. Attached-object
planning consumes a planner-only view of the estimated pose. Calibrated robot
kinematics and measured joints remain robot state. Legacy explicitly configured
benchmark routes retain separate simulator-geometry provenance and cannot count
as observation-only evidence.

Readiness exposes bounded per-arm diagnostics; selection uses the requested arm,
not another arm's success. Preparation persists the existing ReplanSignal and
returns `readiness_provider_unavailable` for missing capability/infrastructure,
or `no_admissible_route` for evaluated route rejection, with a diagnostic ref.
AgentLoop chooses recovery through its existing Query error path. Unknown contact
dynamics and unavailable stop-control evidence remain unavailable; static path
success alone does not authorize motion.

## Visual pipeline

For one immutable observation, the adapter composes:

```text
RGB semantic entities
  + unique proposal
  + instance mask
  + depth and calibration
  -> object point cloud (observation frame, metres)
  -> metric localization (finite bounds, provenance)
  -> visual object geometry (conservative envelope, provenance)
```

Every derived artifact carries `observation_ref`, `scene_revision`,
`entity_ref`, `frame_id`, `calibration_ref`, `source_refs`, and `provenance`.
The generic PAOS contract validates lineage and frame identity; the adapter
owns the provider implementation and artifact storage.

### Metric reconciliation

The adapter checks each semantic entity for exactly one metric localization with
the same observation, revision, frame, and calibration, a non-empty finite point
cloud, metre units, and a valid confidence. It then removes only the matching
metric ambiguity from the active `ambiguities` list and emits a
`reconciliations` entry containing the original code and evidence references.
The reconciliation record preserves the fact that the semantic provider did not
infer metric scale; adapter-derived evidence is the basis for downstream
admission.

If required metric localization evidence is absent, malformed, stale, or
mismatched, the ambiguity remains and binding fails closed. An optional
`object_geometry` artifact may be absent; in that case binding carries only the
visual metric envelope and later grasp/readiness checks decide whether shape
evidence is sufficient. No simulator pose is used as a fallback.

### Visual shape evidence

Shape is estimated from the same segmented metric point cloud. The default
provider emits a conservative axis-aligned envelope in the observation frame,
with `shape_class`, `dimensions_m`, `orientation_reliable`, confidence, and
estimator metadata. It is evidence for grasp/route qualification, not a claim
of simulator collision truth. A provider may return `shape_uncertain` while
still returning a useful envelope; consumers must evaluate uncertainty per
entity and per candidate.

The provider-neutral derived kind is `object_geometry`. Its schema is additive:
existing artifact kinds and clients remain valid, while clients that do not
understand geometry can ignore the new artifact and continue to require metric
localization.

## Gate layering

1. `scene.observe` establishes a fresh observation and calibration references.
2. `scene.understand` returns semantic entities plus adapter-derived evidence.
   Metric reconciliation is performed here.
3. `scene.bind` requires selected entities to have valid metric localization and
   an unambiguous opaque execution identity. It does **not** reject the whole
   scene because one entity has `object_shape_uncertain`, metric-geometry
   uncertainty, or an ambiguity belonging to another entity. When the optional
   `object_geometry` artifact is absent, binding may carry a conservative extent
   derived from the selected entity's visual metric envelope; grasp/readiness
   remains responsible for rejecting insufficient shape evidence.
4. `grasp.propose` returns no candidate (or an explicit `ambiguous` result) for
   an entity whose geometry is insufficient. It never invents default shape.
5. `manipulation.prepare` validates each candidate's frame, workspace, limits,
   collision model, and route evidence. Shape uncertainty becomes a hard stop
   only when it prevents those checks.
6. Actions execute only through Forge Gateway, wait for a terminal result, and
   require post-change observation. Failure, unknown, or unconfirmed cancel
   leads only to stop, replay, or replan.
7. The verifier reads the newest scene revision and is the sole success oracle.

PlanNode `conditions` remain lowercase symbolic facts such as
`scene_current`, `binding_ready`, `metric_geometry_ready`, and
`placement_verified`. Natural-language requirements belong in `obligation`,
`required_evidence`, or `input_bindings`.

## PAOS and extension boundaries

The PAOS core owns contracts, normalization, lineage validation, and Query
projection. It does not import RoboTwin, SAPIEN, camera SDKs, or model code.
The RoboTwin adapter owns proposal, segmentation, depth back-projection, and
visual geometry estimation behind the existing provider ports. Runtime owns
execution identity and current-state checks. Grounding only composes those
receipts; it does not reinterpret simulator geometry as perception.

The extension is append-only and provider-neutral. No fixed YAML, dedicated
Runner, or Runtime-only shortcut is introduced. Existing providers can omit
`object_geometry`; the absence is handled at grasp/readiness rather than by
silently fabricating geometry.

## EvoPhy boundary

EvoPhy may learn which perception provider, observation refresh, proposal
strategy, or candidate ranking is more reliable from attributable execution
evidence. It may not learn to ignore metric evidence, suppress ambiguity,
change collision or workspace limits, grant motion authority, bypass Gateway,
or alter verifier rules. A useful evolution trace retains the raw semantic
output, derived artifacts, reconciliation decision, readiness result, action
terminal receipt, and verifier result.

## Safety and validation

All perception and geometry work is Query-only and keeps
`motion_authorized=false`. Missing calibration, non-finite points, frame
mismatch, stale observations, and invalid artifact lineage fail closed. Tests
must exercise both reconciliation success and failure, shape uncertainty at
bind, candidate-level rejection, artifact contract validation, and zero Action
invocations. A successful test is not a physical success claim; only a fresh
ForgeTaskVerifier result can establish task completion.
