# Current Task: LabUtopia geometric process affordances

- Task ID: `labutopia-process-affordance-provider-20261029`
- Goal: derive bottle-mouth/rim and stirring-rod axis/end affordance candidates from final composed USD mesh evidence in the explicitly configured `simulator_truth` observation path; do not reuse manifest functional coordinates. Vessel-interior geometry is not yet qualified.
- Tier: `C-Safety`
- Risk dimensions: `architecture-sensitive`, `cross-module-contract-sensitive`, `runtime-sensor-sensitive`, `safety-sensitive`, `test-sensitive`
- Owner layer: Isaac Adapter captures final-world mesh evidence; the Isaac perception Provider derives geometric affordance candidates and retains capture lineage; existing PAOS Planner selects task-compatible candidates and Preparation validates the selected frame before any Action.
- Public-interface impact: none intended; reuse the existing private `state` artifact and existing preparation projection. No USD path or mesh data enters AgentLoop or public PAOS claims.
- AgentLoop impact: none; task meaning and action parameters remain caller-owned; planning, lifecycle, cancellation, settlement, and recovery remain PAOS-owned.
- Evidence: same-observation/same-scene-revision final composed USD mesh vertices and topology, plus the existing RGB-D observation. These features are explicitly simulator-ground-truth estimates, not visual/sensor-reconstructed geometry.
- Role separation: Grasp Provider continues to generate grasp candidates from the current point cloud. Process affordance Provider produces operation-feature candidates. Planner binds user task semantics/parameters to compatible candidates; Preparation checks provenance, freshness, transform validity, and ambiguity.
- Failure behavior: absent or non-manifold geometry, insufficient feature support, competing feature candidates, or unresolvable rod working-end role remain explicit unavailable/ambiguous outcomes and cannot enter preparation. No coordinate fallback, guessed feature, automatic retry, or motion is added.
- Concrete failure scenario: valid final AABBs and visible point clouds can coexist with stale manifest `origin_world/tip_world/axis_world/size_m`; using them may target a wrong bottle mouth, beaker opening, or rod end. Existing Git/version tracking and broad tests do not detect incorrect geometric association; focused synthetic topology and preparation rejection tests cover this provider behavior.
- Validation: geometry-provider unit tests for open rim loops, mesh/point-cloud axis candidates, ambiguity, invalid topology and transforms; simulator-truth integration regression; existing adapter perception tests; Ruff, compileall, `git diff --check`. No live motion. A no-motion Isaac scene probe is required before claiming the actual LabUtopia mesh mapping is accepted.

## Architecture Review

- Generic domain: unchanged; consumes bound entities/evidence using existing Query and preparation contracts.
- Adapter: owns USD handles, final-world transforms, mesh capture and private artifact serialization.
- Provider: owns implementation-neutral NumPy geometry estimation and candidate qualification, with explicit simulator-truth provenance.
- Planner: chooses among provider-produced candidates using task role and user-supplied process parameters; it does not invent coordinates.
- Replacement: RGB-D and other simulator adapters remain unaffected; the feature provider consumes a data payload rather than USD SDK objects.
- Evidence freshness: mesh, point-cloud, calibration and scene revision must belong to the same observation before features are persisted.
- Lifecycle owner: existing Runtime/Coordinator/AgentLoop; no duplicate scheduler, state machine or settlement owner.
- Smallest leak test: public `scene.understand` remains unchanged and no process feature is promoted into preparation; the existing simulator-truth state-artifact reference remains the explicit evidence boundary.

## Implementation Plan [完成 / Completed]

1. Extend only simulator-truth private state capture to serialize final-world mesh data for the relevant object prims, while preserving current bounds fields and schema lineage.
2. Add reusable geometry candidate estimation in the Isaac Adapter Provider layer; remove simulator-truth manifest requirements for functional coordinate fields, preserving label/category/prim identity only.
3. Bind feature candidates to current state artifact/capture and preserve them as private evidence. The current PAOS binding has no planner-selected process-feature reference, so do not feed candidates to resolve/held-refresh; preparation remains fail-closed pending that explicit selection seam. Ambiguous rod endpoint roles remain unresolved until task/grasp context can distinguish them.
4. Add no-motion provider, integration, stale/invalid evidence, and preparation fail-closed tests. Do not modify generic PAOS contracts or AgentLoop.
5. Update geometry/acceptance diagnosis and this changelog with exact line ranges, diff, validation and Git outcome.

## Implementation Result

- Adapter state schema `labutopia-simulator-world-geometry/v1` retains final-world bounds and adds bounded final-world mesh vertices plus incidence-one boundary edges. The legacy bounds schema remains readable.
- `load_truth_manifest()` retains label/category/prim identity and discards legacy authored feature coordinates. The Provider produces closed-loop circular rim candidates and symmetric rod-axis endpoint candidates from final mesh evidence. No candidate is selected as process truth, and `process_features` stays unset.
- `resolve()` and held refresh remain unchanged and fail closed. The existing planning/binding route has no stable selected-process-feature reference; adding one requires a separate contract and caller/impact review.
- Vessel interior is not derived. Nested mesh rings remain separate candidates and are not enough to qualify internal volume/depth.
- No public PAOS contract, AgentLoop, task lifecycle, or action executor changed. No Isaac run or robot motion was performed.

## Scope Guard

Do not edit `.task/current.md`, unrelated user-modified files, LabUtopia external files, public PAOS schemas, AgentLoop, task DAG templates, atomic action parameters, or simulator motion code. Do not execute pouring/stirring or robot motion. Do not commit or push files containing unrelated user changes; review Git staging scope before any repository write.

## Follow-up Diagnosis: Planner Selection Handoff (2026-10-29)

- Finding: the generic PAOS planning substrate already supports task-bound `PlanNode.input_bindings`, AgentLoop selection from authorized bounded evidence, Coordinator-owned declared ToolSpec projection, frozen consumer-schema validation, and durable DecisionTrace/selection receipts. No new generic AgentLoop selection mechanism is indicated.
- Missing route: LabUtopia process-feature candidates are currently serialized only in Adapter-private observed-geometry artifacts. They are not emitted by a PAOS Query with a Coordinator-owned ToolExecutionRecord/evidence ref, and the existing composite subtask action has no preceding AgentLoop node that can select a process-feature candidate. Consequently an `input_bindings` field alone cannot select a runtime-generated opaque candidate ref.
- Contract boundary: if introduced, the domain value should be an opaque, observation/scene-bound `process_feature_ref` (or an explicit set of role-bound refs) plus operation semantics. It must not carry USD prim paths, simulator handles, mesh vertices, or authored coordinates. Provider metadata owns candidate kind/role and transform payload; the adapter validates current observation, scene revision, frame, task operation, and ambiguity during no-motion preparation.
- Selection semantics: preserve separation from grasp candidates. Grasp Provider supplies grasp candidates; process-feature Provider supplies operation geometry. A planner-visible Query must expose both candidate identities and bounded semantic descriptions. The AgentLoop node must select exact refs from that result and freeze them into the relevant PlanNode/selection receipt before the preparation Query. Missing, stale, cross-entity, incompatible, or ambiguous refs remain explicit failures.
- Geometry limitation: current mesh candidates identify closed circular rim loops and symmetric stir-rod endpoints. They do not establish a vessel interior, bottle pouring lip direction, or which symmetric rod end is the working tip. The last item requires additional observation/context or a qualified provider method; no endpoint may be silently chosen.
- Tier/risk: Tier C-Safety; architecture-sensitive, public-contract-sensitive, lifecycle-sensitive, sensor/provenance-sensitive, motion-boundary-sensitive. Expected owner path: provider-neutral PAOS ToolSpec/PlanNode composition and AgentLoop evidence selection; Skill workflow owns process semantics; Adapter/Provider owns geometric mechanisms and no-motion validation; Runtime/Gateway retains Action admission and lifecycle.
- Blocker before end-to-end implementation: current LabUtopia semantic task builder creates a composite `manipulation.execute_subtask` obligation, while feature candidates only exist inside its private perception records. A complete implementation therefore requires a route change that inserts a candidate-discovery Query and explicit AgentLoop selection receipt before composite execution, then carries only the selected opaque refs and operation parameters into preparation. Updating the generic contract without this route would create a public field that cannot be populated from authorized evidence; auto-selecting in Provider would bypass Planner intent.
- Required implementation tests: selected ref comes from the same task/revision/observation evidence; valid replacement Provider works without Isaac details; omitted/duplicate/stale/cross-entity/incompatible refs reject before Action admission; existing generic pick/place and AgentLoop selection tests remain unchanged. Tests must assert zero Action/scene-motion calls on every preparation failure.
- Local documentation constraint: the routing skill's prescribed `docs/AGENT_WORKFLOW.md`, `docs/IMPLEMENTATION_PRINCIPLES.md`, `docs/MODULE_MAP.md`, `docs/EXTENSION_CONTRACT.md`, `docs/TESTING.md`, and `docs/LOGGING_POLICY.md` do not exist in this checkout. This routing record uses the checked-in Chinese developer manual, `PLANNING_MODULE_DESIGN.md`, `AGENT_TOOL_INPUT_SELECTION_DESIGN.md`, and LabUtopia subtask review instead; repository owners should restore/identify the authoritative routing documents before a cross-module public-contract expansion.

## Follow-up Implementation Plan [计划 / Planned] - v16.1.7

1. Keep current geometric candidates private and preparation fail-closed until a planner-visible Query and task-bound selection route exist.
2. Design the smallest provider-neutral candidate Query contract and compose it into the LabUtopia PAOS task graph without adding lifecycle ownership to AgentLoop or embedding simulator fields in PAOS.
3. Persist the planner's opaque candidate selection through the existing node selection/DecisionTrace mechanism and pass it to preparation via declared evidence projection.
4. Add substitutability, lineage, ambiguity, invalid-selection, stale-evidence, and no-motion tests before wiring an Adapter implementation.
5. Only after contract/route tests pass, connect Isaac's current private geometry candidates to the new Query and perform an Isaac no-motion scene probe. Do not claim pouring/stirring readiness or execute motion until feature qualification (including vessel interior and rod working end) is established.

### Concrete failure scenario / anti-overdefense assessment

If a provider privately auto-selects one of the symmetric rod endpoints or an Agent supplies a fabricated/stale reference, preparation may target the wrong work end or stale frame. Git/versioning cannot detect semantic evidence association; ordinary schema validation cannot prove the ref came from the current authorized Query result. The existing Coordinator record and typed provenance can address this once the candidate Query/selection path exists; do not add hashes, baselines, or a parallel gate. Omission of the route must continue to stop before motion.

## Follow-up Implementation Plan [计划 / Planned] - v16.1.8

- Tier: `C-Safety`; risks: provider-neutral ToolSpec/public contract, AgentLoop PlanGraph composition, evidence lineage, sensor freshness, motion admission.
- Owner split: PAOS Skill owns the provider-neutral `manipulation.process_features` Query contract and no-motion preparation input; semantic task builder adds the Query predecessor; existing AgentLoop/Coordinator owns candidate selection, receipt and DecisionTrace; Isaac Provider maps selected opaque refs to private same-capture geometry; Gateway remains the only Action lifecycle owner.
- Public caller impact: add one opt-in Query ToolSpec and one optional/required-for-pour-stir selection field on `manipulation.execute_subtask`; require PlanNode dependency order to make the candidate Query a direct predecessor. Preserve existing generic pick/place and legacy subtask input behavior for `relocate`.
- Evidence contract: Query receipt binds candidate refs to observation_ref, scene_revision, frame_id, calibration_ref and entity_ref. Subtask Action must select only refs exposed by its direct predecessor (through existing `argument_sources`) and pass them unchanged to no-motion preparation. Adapter/provider resolves refs against its current capture and rejects stale, unknown, cross-entity, role-incompatible or ambiguous selections.
- Tests before live wiring: replacement fake Provider query; plan graph predecessor/dependency checks; exact AgentLoop source projection; missing/fabricated/duplicate/stale/cross-entity ref rejection; no Action start on all preparation failures; legacy relocate compatibility. No new digest, hash, baseline or parallel lifecycle state.
- Physical limitation: candidate Query integration does not qualify the current vessel interior or rod working end. Until Provider evidence supports those features and a no-motion Isaac stage probe confirms frames, preparation must report unavailable/ambiguous and the composite Action must stop before actuator admission.
- Validation: focused Skill tests, PAOS AgentLoop selection/argument projection tests, Isaac Adapter geometry tests, full affected suites, Ruff, compileall, `git diff --check`. No motion, no EULA/bootstrap, no commit/push of unrelated worktree changes.

## Implementation Result - v16.1.8 (2026-10-29)

- Added `argument_source_requirements` to the provider-neutral ToolSpec planning projection. AgentLoop PlanSelect accepts required refs only from a successful direct predecessor's declared output path; literals, discovery evidence, wrong tools/paths, and non-predecessors are rejected. PlanReady surfaces active required source keys.
- Added the process-feature Query and no-motion preparation Tools and connected the LabUtopia process route. Query results remain candidates; the existing AgentLoop selection and Coordinator receipt path records the chosen opaque refs. Preparation validates current capture identity and feature evidence; pour/stir Action arguments are projected from successful preparation, preserving the checked refs.
- Ambiguous Query settlement now fails and does not ready a dependent Action. Fake Gateway discovery and Skill/package metadata were synchronized. The persistent-host node artifact was rebuilt as `1.0.17` with SHA `7a65345bafba94a76dc6bde232a0f97c5bd447333dbbbc050c69bcce881c87cc`.
- Validation: `859 passed` across Skill + Isaac Adapter tests; focused artifact lock tests `2 passed`; Ruff, compileall and `git diff --check` passed.
- Tests exercise replacement Provider behavior, source provenance, stale/ambiguous/cross-entity rejection and zero Action admission on failures. No Isaac Kit stage probe or robot motion was run. Bottle lip, beaker interior and rod working-end qualification remain required before enabling pour/stir execution.
- No commit or push: the shared worktree includes extensive pre-existing user changes and the relevant files cannot be safely isolated into a commit.

## Follow-up Implementation Result - v16.1.9 (2026-10-29)

- Failure reproduced from the full Agent run: scene state had valid final-world AABBs but empty mesh arrays because `_simulator_truth_state()` traversed only the default `Usd.PrimRange` and omitted instance proxies in referenced LabUtopia assets.
- Isaac Adapter now traverses `Usd.PrimRange(prim, Usd.TraverseInstanceProxies())`; mesh evidence extraction remains Adapter-private and preserves local-to-world transforms, stage-unit conversion, boundary incidence, and the existing 4096-point bound. No PAOS schema, AgentLoop, planning policy, lifecycle, or motion route changed.
- Added a focused instance-proxy traversal test that checks transformed world points, stage unit conversion, and boundary edge output. Full Skill + Isaac Adapter suite: `860 passed`; focused rerun: `1 passed`; Ruff, compileall and `git diff --check` passed.
- Fresh no-motion `agent_host` observation at `out/lab-geometry-no-motion-20261029-r1/`: no task/action/session, no controller outcomes. Final state contains R01 `1214` vertices/`244` boundary edges, BEAKER `1698`/`6`, and GLASS_ROD `66`/`0`. The geometry records contain two rod endpoint candidates; bottle and beaker opening candidates remain unavailable because captured topology is non-manifold/open or insufficient. This closes the missing-mesh-capture diagnosis, not process-feature qualification.
- No robot, object, pouring or stirring motion was executed. No commit/push due to the shared worktree's unrelated pre-existing changes.

## Follow-up Diagnosis and Implementation - v16.1.10 (2026-10-29)

- Diagnosis: `process_feature_candidates()` previously rejected a vessel's entire boundary graph if any connected component contained a vertex whose degree was not two. A separate open/non-manifold decorative or secondary mesh component could therefore suppress an independent valid closed rim. The prior tests covered only globally open boundaries and did not exercise mixed-validity components.
- Implementation owner remains the Isaac simulator-truth geometry Provider. Boundary components are now evaluated independently; only degree-two components with enough vertices proceed to the existing top-plane/circularity checks. Edge multiplicity is preserved in vertex degree, so duplicate coincident edges remain non-manifold rather than being hidden by a set.
- PAOS Query semantics, AgentLoop candidate selection/receipt, preparation, public contracts, lifecycle, and Action admission are unchanged. No fallback coordinates or weaker rim-fit criteria were introduced. Preparation still fails closed for unqualified vessel geometry and unresolved rod working-end role.
- Regression coverage: a valid closed circle remains discoverable alongside a disconnected branching boundary; the open-only and duplicate-edge non-manifold cases remain rejected. This establishes candidate extraction behavior only, not motion qualification.
- Replayed the captured final USD state from `out/lab-geometry-no-motion-20261029-r1/` without starting Isaac: R01 and BEAKER still have no qualifying rim candidates; GLASS_ROD still has two symmetric endpoints. The component fix does not change that observation. The next geometry investigation must inspect the source meshes/components and determine whether the authored geometry supports a rim/interior estimate at all; repeating an identical capture is not evidence that resolves these limitations.
- Topology detail from that replay: R01's 244 boundary edges form one component with vertex degrees 4, 6, and 8 (not a simple rim loop). BEAKER's six captured boundary edges collapse to one vertex at the Provider's 1e-5 m key resolution, so they cannot support a rim. These measurements point to source topology/degenerate-edge inspection, not a more permissive rim fit.
- No Action/Session/task creation, simulator stepping, or object/robot motion occurred.
