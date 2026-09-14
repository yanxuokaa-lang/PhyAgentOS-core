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
`metric_3d_unavailable` ambiguity and emits a reconciliation entry. The raw
semantic ambiguity remains in the record under `reconciled_ambiguities` so the
model output is never rewritten as if it had inferred metric scale.

If any required visual evidence is absent, malformed, stale, or mismatched, the
ambiguity remains and binding fails closed. No simulator pose is used as a
fallback.

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
   scene because one entity has `object_shape_uncertain`.
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
