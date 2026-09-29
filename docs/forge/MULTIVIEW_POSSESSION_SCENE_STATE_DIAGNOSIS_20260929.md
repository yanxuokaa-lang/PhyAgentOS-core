# PAOS Multi-View, Possession, and Scene-State Diagnosis

Date: 2026-09-29. Scope is architecture, source inspection, and no-motion implementation guidance. The triggering evidence came from a RoboTwin pick/place run, but every diagnosis and proposed contract below is provider-neutral and task-neutral.

## 1. Executive diagnosis

Two independent defects combine after a successful world-changing acquisition:

1. **Observation and semantic inference are single-view.** RoboTwin obtains a camera bundle from one simulator observation, but the current Runtime persists one selected camera and Qwen vLLM consumes the first resolvable image. Arm/gripper occlusion can therefore remove every free object from the semantic input except the held object.
2. **Scene revision and binding are too coarse.** A successful Action correctly advances the global scene revision, but the current recovery path invalidates all earlier scene evidence and requires a full fresh bind. The binding path also couples read-only entity grounding to an idle action-driven execution scene, so it becomes unavailable while the Runtime is legitimately holding an object.

The first defect cannot be fixed by a model fallback: a second model cannot recover objects absent from the image. The second defect cannot be fixed by a second camera alone: a valid multi-view understanding result can still be rejected by the idle-scene grounding gate.

## 2. Confirmed current behavior

### 2.1 Single-view observation path

- The public scene.observe ToolSpec requires one sensor_ref.
- The persistent observation source forwards that request to one Runtime observe operation.
- The RoboTwin engine indexes arguments.sensor_ref and returns one camera snapshot.
- The simulator backend calls get_obs(), which contains multiple camera entries, but persists only the requested camera.
- The Qwen vLLM adapter iterates artifact references and stops at the first resolvable image.

This is a real contract limitation, not Qwen instability.

### 2.2 Post-Action refresh behavior

Re-observation after an Action is required. Acquisition changes possession and support state, object pose relative to the gripper, robot joint and end-effector state, occupied and collision space, camera occlusion, and the next Action's start state and admission inputs.

The defect is not that the loop refreshes. The defect is that all prior entities are treated as equally stale even when Runtime evidence can prove that only a bounded effect set changed.

### 2.3 Binding while holding

The observed failure grounding_unavailable: grounding requires the current idle action-driven scene shows that current binding mixes read-only semantic grounding with execution actor activation and pose integrity.

PAOS Query semantics require read-only grounding to remain available without authorizing motion. Execution actor resolution belongs at manipulation.prepare and Action admission, where possession, workspace, collision, IK, and current Runtime identity are checked.

## 3. Required architecture

### 3.1 Synchronized MultiViewObservationSet

Extend the existing scene.observe Query instead of adding a task-specific or multiview Tool. The input remains backward compatible and accepts either one sensor_ref or an ordered sensor_refs list plus max_age_ms and max_capture_skew_ms.

The Runtime must call the sensor backend once, persist each requested view from the same captured simulator observation, and return one global scene revision, ordered views, per-view sensor/frame/calibration/timestamp/artifacts, measured capture skew, and a backward-compatible primary view in existing top-level fields.

Mixed revisions, missing calibration, duplicate sensors, unavailable views, or excessive skew fail closed. A Query never moves a camera or robot. Active viewpoint motion requires a separately admitted Action or Session.

### 3.2 Multi-image semantic inference

The provider-neutral scene.understand request carries ordered views. Qwen vLLM receives every RGB view in one multimodal request and returns one semantic graph.

Cross-view identity must be explicit and uncertainty-preserving. One physical entity uses one local identity only when visual evidence supports correspondence. Each entity reports contributing view identifiers. Uncertain correspondence creates separate entities plus a canonical ambiguity. Projected PAOS provenance contains only the RGB artifacts supporting the claim.

The semantic provider cannot emit metric pose, collision geometry, simulator identity, task success, or motion authorization. Adapter-side depth and calibration composition remains the geometry owner.

### 3.3 Possession-aware read-only binding

scene.bind must create evidence while the Runtime is empty or holding. Binding entries use these lifecycle states:

| State | Meaning | Admissible source |
|---|---|---|
| observed_current | Directly measured in the current revision | current observation, understanding, and geometry |
| held_current | Current possession is known | terminal acquire settlement plus Runtime holding state |
| carried_forward | Inherited into the new revision | prior binding plus Runtime-owned unaffected evidence |
| uncertain | Not safely bindable | missing or contradictory evidence |

The Query returns motion_authorized=false. Execution actor lookup and pose equality checks remain in preparation and admission. No held or inherited semantic binding can directly start motion.

### 3.4 Entity-scoped world-change effects

The global scene revision still advances after every known world-changing Action. It remains the ordering and replay boundary. Selective reuse is represented as Coordinator and Runtime-owned evidence, not by keeping the old revision current.

Action terminal results need a typed effect summary containing source and new revisions, changed entities and resources, Runtime-proven unaffected entities, and effect evidence refs.

Unaffected entities are accepted only when Runtime evidence proves execution did not contact or disturb them. Intent alone is insufficient. Missing or unknown effect evidence means no carry-forward. The Coordinator creates carry-forward lineage into the new revision; the Agent cannot author opaque refs or claim an entity unchanged.

## 4. Correct AgentLoop behavior

After a successful acquisition:

    terminal Action reconciliation
      -> synchronized scene.observe
      -> scene.understand
      -> manipulation.capabilities
      -> scene.bind
           observed current entities
           + held entity from possession evidence
           + Runtime-proven unaffected carry-forward entities
      -> ready/select
      -> manipulation.prepare(place)
      -> object.place

The loop must not replay grasp.propose, acquire preparation, or object.acquire after terminal success. It must not skip post-Action observation because robot state and collision space changed. If a required entity is neither freshly observed nor validly carried forward, planning stops fail-closed or requests another configured passive view.

## 5. Ownership boundaries

| Owner | Responsibility | Must not do |
|---|---|---|
| Runtime | synchronized capture, physical holding state, Action effect evidence | infer task completion or Agent policy |
| Adapter/provider | artifact resolution, multi-image inference, deterministic projection | authorize motion or expose simulator truth as visual evidence |
| PAOS Core Tool endpoint | public schemas, validation, freshness, provenance | import RoboTwin or Qwen-specific code |
| Coordinator | task, revision, event authority and carry-forward lineage | fabricate Runtime effects or replay Actions |
| AgentLoop | choose legal next Query or node using ready/select semantics | handcraft opaque refs or assume unchanged entities |
| Prepare and Action admission | actor identity, possession, workspace, collision, IK, authorization | trust semantic binding as motion permission |

## 6. Anti-OverDefense disposition

This change needs no new content hash or duplicate state store. Existing scene revisions, record identities, typed schemas, Coordinator events, and artifact references are sufficient. New validation is limited to concrete failures: mixed camera revisions, excessive timestamp skew, missing calibration, unproven carry-forward, and read-only binding coupled to idle execution state.

No gate is added for task labels, RGB order, provider-specific object categories, or ordinary formatting.

## 7. Acceptance plan

Implementation is accepted only after:

1. single-view public compatibility remains green;
2. synchronized multi-view conformance rejects mixed revision, skew, and calibration failures;
3. Qwen vLLM sends all RGB views and preserves claim-level provenance;
4. holding-state bind is read-only and does not activate motion;
5. carry-forward succeeds only with Runtime-owned unaffected evidence;
6. unknown effects remain stale and fail-closed;
7. the established seven-dimension review reports no open Blocker or Major findings.

No live motion is required for code acceptance. A later fresh AgentTask and controlled Runtime test remain separate deployment acceptance.
