# LabUtopia R01/BEAKER Process-Feature Blocker (2026-10-29)

## Result

The full Agent run `out/lab-fullchain-truth-20261029-r4/` stopped at the first
`manipulation.process_features` Query. It returned `status=empty`, an empty
candidate list, and `motion_authorized=false`. The task was cancelled before
Preparation or Action. `acceptance.json` records `controller_outcomes: []`.
The user-supplied pour/stir parameters were present in the task PlanGraph, but
were not passed to an atomic action. No robot or object motion occurred.

## Evidence and Cause

The Query and observation shared scene revision
`labutopia-tabletop-rod-rack-v1:e2a855e878104534ab154e51d38ee48f:0` and frame
`tabletop_third_person`. The final USD state artifact in the same capture had:

| Entity | Mesh points | Aggregated boundary edges | Provider result |
|---|---:|---:|---|
| R01 | 1214 | 244 | no rim; boundary vertex degrees 4, 6, and 8 |
| BEAKER | 1698 | 6 | no rim; edge lengths approximately `4.8e-10` to `4.6e-9 m` |

The Adapter already traverses final-composed instance proxies, applies
local-to-world transforms and stage units, and captures same-revision mesh
evidence. The immediate loss is that `_simulator_truth_mesh_evidence()` kept
only coordinate pairs for boundary edges, discarding original Mesh vertex
indices and connected-component identity. Distinct topological loops within a
single Mesh therefore became a coordinate-collapsed graph to the Provider.
The BEAKER edges in this capture are degenerate and cannot support a rim.
Existing provider tests covered separate graph components, but not loss of
vertex-index connectivity at the Adapter boundary.

The saved r4 artifact predates component-separated edge serialization. It
cannot establish whether an individual R01 mesh component contains a valid rim;
that requires a fresh no-motion Isaac observation. A fresh result with no
closed circular component is still a geometry failure, not permission to use
the envelope, configured coordinates, or an inferred vessel shape.

## Architecture Route

- Tier: `C-Safety`.
- Owner: Isaac Adapter owns USD traversal, world transforms, units, and
  component-preserving private state evidence. The simulator-truth perception
  Provider owns numeric geometry candidate derivation.
- Generic PAOS: existing `manipulation.process_features` Query remains
  provider-neutral and exposes only opaque feature references, semantic kind,
  and role. AgentLoop retains candidate selection and DecisionTrace/receipt;
  Preparation verifies selection and current evidence; Gateway/Runtime retain
  Action admission, lifecycle, cancellation, and settlement.
- Public contract impact: none. The added mesh-component field stays inside
  the Adapter-private simulator-truth `state` artifact. No USD paths, SDK
  values, or mesh payloads are projected into AgentLoop.
- Concrete failure scenario: flattening disconnected vertex-index boundary
  components into coordinate pairs can suppress a valid component-level rim;
  treating near-zero boundary edges as a
  real loop can fabricate a process feature. Normal Git/version tracking and
  existing independent-component tests do not preserve or validate this
  runtime topology association. Keep edges per mesh and reject degenerate
  edges; do not add hashes, additional gates, or coordinate fallback.
- Stop behavior: an absent or ambiguous feature candidate continues to fail
  before Preparation/Action. Finding a rim candidate does not by itself
  qualify a bottle pouring lip, beaker interior, or stir-rod working end.

## Implementation and Validation

The Adapter now retains bounded `boundary_edge_components_world_m` arrays,
split by original mesh vertex-index connectivity, alongside the legacy
aggregate boundary field. The Provider rejects zero-length edges and first
tries a top-ring circle fit from the final mesh vertices, requiring a stable
fit and maximum angular gap at most 90 degrees; if that cannot be fit, it
evaluates independent closed boundary components. Older state artifacts
without component arrays use the legacy aggregate path. No authored positions,
AABB extrema, or task-specific coordinates are substituted.

Validation:

- Focused Adapter capture and geometry tests: `12 passed` across the selected
  capture and simulator-truth tests.
- Full Isaac Adapter + pick-place Skill suites: `868 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Fresh no-motion Isaac observation r2:
  `out/lab-process-geometry-no-motion-20261029-r2/`, scene revision
  `labutopia-tabletop-rod-rack-v1:f46fd9b3231040bda7b89f8f6903cb25:0`.
  Offline replay of its exact state artifact returns one R01 rim estimate at
  approximately `[-0.27001, -0.56000, 0.80947] m`, radius `0.01753 m`, and one
  BEAKER rim estimate at approximately `[-0.07854, 0.00000, 0.80147] m`, radius
  `0.03004 m`.
- This live observation tested scene capture only; the new state was replayed
  through the Provider and provider-neutral Query endpoint. The Query returned
  `available`, two opaque rim candidates, and `motion_authorized=false`. It did
  not exercise AgentLoop candidate selection, Coordinator receipts,
  Preparation, or Action. No task, Action, controller outcome, or robot/object
  motion occurred.

## Acceptance Boundary

Contract evidence: unchanged and covered by existing PAOS/Skill tests.
Provider evidence: synthetic component/coverage tests and exact captured-state
replay produce one rim candidate per entity; the provider-neutral Query returns
both candidates under the exact scene/observation identity.
Live scene evidence: r2 proves current USD capture and frame/scene artifact
availability plus offline Query behavior, but not AgentLoop selection or
process readiness. Preparation
must still reject/hold execution until the bottle pouring lip/direction,
BEAKER interior/depth, GLASS_ROD working end, and selected-reference lineage
are qualified against current evidence. No live execution evidence is claimed.

## Git and Task State

No commit or push was made. The shared worktree contains extensive pre-existing
user changes and active modifications in overlapping files; staging or
committing broad snapshots would include unrelated work. The active
`.task/current.md` belongs to a separate user planning task and was not
overwritten; this diagnosis is the local record for this Tier C-Safety slice.
