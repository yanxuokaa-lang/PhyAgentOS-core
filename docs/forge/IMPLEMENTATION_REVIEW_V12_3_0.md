# PAOS v12.3.0 Multi-View and Possession-Aware Scene-State Implementation Review

Date: 2026-09-29

Branch: `feature/planning-loop`

Scope: synchronized multi-camera observation, joint semantic understanding, Runtime-proven entity carry-forward, and read-only grounding/preparation while holding an object.

## 1. Findings first

### Blocker — fixed: flattened multi-camera artifacts broke primary RGB-D composition

- Location: `examples/forge-adapters/robotwin20/src/robotwin20_adapter/single_view_perception.py:L451-L792`.
- Failure: flattening all RGB/depth artifacts made the existing primary-view metric pipeline see multiple RGB/depth candidates and reject composition before semantic fusion.
- Fix: the observation set remains multi-view for semantic inference, while the established RGB-D proposal, segmentation, and localization path consumes the declared primary view only. Secondary-only semantic entities remain visible claims but receive no fabricated metric geometry.
- Regression: `examples/forge-adapters/robotwin20/tests/test_single_view_perception.py:L294-L378`.

### Major — fixed: Agent could inject internal carry-forward evidence

- Location: `PhyAgentOS/agent/tools/forge_tool_api.py:L259-L267, L342-L350, L782-L869`.
- Failure: accepting model-authored `carried_entities` would let an Agent claim that an occluded entity was unchanged without a terminal Runtime result.
- Fix: direct Agent input is rejected. The Coordinator derives carry-forward only from a successful task-owned Action settlement whose `scene_effects` are complete and explicitly authorize carry-forward.
- Regression: `tests/test_forge_tool_api.py:L463-L589`.

### Major — fixed: carry-forward could inherit unselected entities

- Location: `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L303-L397`.
- Failure: inheriting every eligible entity from the old grounding artifact could expand a new binding beyond the Agent's current selection.
- Fix: grounding intersects Coordinator-provided carry-forward candidates with the entity refs explicitly selected for the new binding.
- Regression: `examples/forge-adapters/robotwin20/tests/test_grounding.py:L108-L178`.

### Major — fixed: carried geometry lacked execution-identity and pose revalidation

- Location: `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L333-L397` and `PhyAgentOS/agent/tools/forge_tool_api.py:L823-L869`.
- Failure: a stale artifact could preserve semantic identity while the execution object or its pose had drifted.
- Fix: grounding reopens the previous binding artifact, verifies the stored execution entity identity, verifies the Runtime effect evidence, and requires the current exact pose to match before inheriting metric geometry. Drift fails closed.
- Regression: `examples/forge-adapters/robotwin20/tests/test_grounding.py:L108-L178`.

### Major — fixed: Action success fixture omitted mandatory place terminal evidence

- Location: `examples/forge-adapters/robotwin20/tests/test_persistent_agent_loop.py:L105-L122`.
- Failure: a test fixture treated placement as successful without release, retreat, clear-of-target, and post-action observation readiness.
- Fix: the fixture now supplies the same terminal evidence required by the production Action contract.

No unresolved Blocker or Major finding remains in the reviewed change. Existing combined-suite failures are reproduced by clean `HEAD`; the modified tree has one fewer failure.

## 2. Seven-dimension review

### 2.1 Architecture integration

- `scene.observe` owns observation-set validation in `PhyAgentOS/forge/capability_runtime/observation.py:L41-L354`.
- RoboTwin owns synchronized simulator capture in `robotwin_backend.py:L195-L223, L432-L493` and returns one scene revision with per-camera frame, calibration, timestamp, and artifact identity.
- `scene.understand` owns provider-neutral multi-view and carry-forward validation in `PhyAgentOS/forge/capability_runtime/understanding.py:L141-L938`.
- Qwen vLLM, legacy Qwen, OpenAI Responses, and Chat Completions consume the same ordered RGB views; providers do not own Coordinator settlement semantics.
- Carry-forward ownership remains split correctly: Runtime reports effects, Coordinator authorizes task-owned projection, and grounding validates execution identity and pose.
- The implementation is task-neutral and contains no RGB-arrangement-specific rule.

Result: pass.

### 2.2 Recovery and idempotency

- Action effects are read only from terminal-success task records; admitted, running, unknown, failed, and incomplete outcomes cannot authorize carry-forward.
- The feature does not create a replacement invocation, retry a successful Action, or infer effects from the requested Action intent.
- Post-Action global scene revision still advances. Only explicitly proven unaffected entities can be inherited; changed or unknown entities require fresh metric evidence.
- Holding-state changes during preparation or route building invalidate the result instead of silently completing against a stale state.

Result: pass.

### 2.3 Robotics safety

- All implementation and validation in this change are no-motion. No simulator Runtime or physical Action was started.
- Freshness, calibration, capture skew, workspace, collision, IK, motion authorization, planning admission, Gateway, Coordinator, and terminal-result gates remain intact.
- Read-only binding while `holding` does not authorize motion and continues to report `motion_authorized=false`.
- Secondary-only semantic entities carry `primary_view_metric_evidence_unavailable`; the system does not invent depth, pose, collision geometry, or a grasp target.
- Unknown effects and pose drift fail closed.

Result: pass for code/no-motion acceptance. Live simulator and hardware behavior remain outside this review.

### 2.4 Configuration and reproducibility

- Legacy `sensor_ref` remains supported; ordered `sensor_refs` is the opt-in multi-view path.
- `max_capture_skew_ms` is an explicit Tool argument with a default, not a hard-coded robot-task rule.
- Python ToolSpecs and Skill YAML contracts are synchronized.
- Reproducible combined command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests
```

Result: pass.

### 2.5 Maintainability

- Existing provider seams and primary-view metric workers are reused; no parallel demo pipeline was introduced.
- Observation-set and carry-forward validation use explicit typed dictionaries and existing artifact refs rather than new hashes or frozen contracts.
- No new TODO, placeholder, `pass`, or fake-success path is present in the production diff.
- The primary-view metric boundary is documented rather than hidden: multi-view improves semantics, not uncalibrated multi-view geometry.

Result: pass.

### 2.6 Observability

- Observation results expose ordered `views` and measured `capture_skew_ms`.
- Semantic entities and relations expose exact per-view artifact provenance derived from `source_view_indexes`.
- Terminal Action results expose `scene_effects`, changed/unaffected entity refs, evidence refs, completeness, and carry-forward authorization.
- Rejections distinguish invalid sensor sets, capture skew, invalid views, invalid carry-forward, identity mismatch, and pose drift.

Result: pass.

### 2.7 AgentLoop autonomy

- The Agent can request a multi-view observation and continue the standard discovery chain without manually constructing internal refs.
- The Coordinator, not the model, projects valid unchanged-entity evidence into the next `scene.understand` call.
- A held object no longer blocks read-only grounding, preparation, or route construction solely because the Runtime is not idle; Action admission still decides whether motion is legal.
- The loop can reobserve after a world-changing Action while retaining only Runtime-proven unaffected entities, which solves the general occlusion problem without skipping post-Action freshness.

Result: pass.

## 3. Validation evidence

- Focused contract and legacy Qwen: `53 passed`.
- Observation/provider/effect tests: `54 passed`.
- Carry-forward and holding-state binding: `117 passed`.
- Multi-view composition: `59 passed`.
- Related Core/Adapter/Skill/AgentLoop set: `304 passed`.
- Combined modified workspace: `1745 passed, 1 skipped, 25 failed`.
- Combined clean `HEAD`: `1695 passed, 1 skipped, 26 failed`.
- The 25 remaining failures in the modified workspace are clean-HEAD baseline failures. The change adds 50 passing tests and removes one obsolete single-sensor assertion failure.
- Ruff, compileall, and `git diff --check` are required again after documentation closure.

## 4. Acceptance conclusion and remaining risk

The implementation satisfies the saved diagnosis at the code and no-motion test levels: synchronized multi-view semantics, possession-aware read-only binding, and Runtime-proven entity-scoped carry-forward are integrated into the existing PAOS ownership boundaries. It does not weaken Action safety or special-case the RGB arrangement task.

Remaining risk is operational rather than hidden by the implementation: real camera synchronization quality, calibration quality, Qwen multi-view stability, attached-object collision behavior, and live acquire/place terminal evidence still require a separately authorized simulator acceptance run. Until that run succeeds, this review does not claim physical-task completion.
