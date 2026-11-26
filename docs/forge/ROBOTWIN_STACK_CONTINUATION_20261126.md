# RoboTwin stack continuation — 2026-11-26

状态 / Status: P2B-2 Adapter preparation composition implemented; production Coordinator evidence resolver and observed support Provider remain outstanding. Motion remains disabled. No simulation or hardware action was started.

## 修复与归属 / Fix and ownership

旧工厂删除 `intent`，真实 `PersistentPreparationProvider` 却首先读取该字段；旧 FakePreparation 没有检验它。现在显式注入 Adapter 私有 `prepare_inputs(request, task_id)`，返回可信完整 `ManipulationIntent`、当前 grasp candidates/candidate_set、capability snapshot、binding/frame/observation/calibration 以及明确的目标几何来源。关系候选与抓取候选不能互换。 / The old factory removed intent even though the real preparation provider requires it. An explicit Adapter-private resolver now supplies trusted intent and current preparation evidence; relation candidates never become grasp candidates.

Coordinator 继续持有任务、意图、修订和结算；AgentLoop 驱动工作流；Grounding 将选中的世界坐标关系目标投影到已有对象/功能点，并注册原 opaque destination；真实 Preparation、selector、PreparedRoutes 继续负责路线准备。校准和 scene/observation/frame 绑定必须一致。 / Coordinator retains task/intent/revision/settlement ownership. Grounding projects the selected world-frame target through current object and functional-point transforms; preparation, selection and persistence keep their existing owners and identity checks.

真实组合还暴露：生产 route request 不含顶层 destination_ref，该字段位于 route_arguments，选中候选另带 placement_target.target_ref。现在按实际结构核对二者；保留全部 route_arguments，补可信 intent.task_id，避免丢掉 worker 需要的 capability/frame/observation/preparation lineage。 / Real integration exposed a second fixture-hidden mismatch: destination lives on route_arguments and candidate placement_target. Validate both and preserve the complete registered arguments, adding trusted task_id for the worker.

## 输入来源与未完成范围 / Provenance and remaining work

Grounding 的 `geometry_source=observation` 描述对象/碰撞几何；关系目标另存 `target_geometry_source` 与 `target_evidence_refs`，经生产 `validate_scene_facts` 保留。当前 stack relation Provider 使用仿真器 actor 几何；不能称全视觉感知成功。公共 relation Query schema 没有来源字段，未来 resolver 必须从现有 evidence artifact 取得来源，当前私有端口仅要求显式声明并保存，尚未自动核验 artifact 内容。 / Object/collision and target provenance remain distinct; the current simulator-derived target is not labelled observed. The future resolver must read existing evidence artifacts; this composition checks explicit provenance fields but does not independently verify artifact contents.

尚待：生产 Coordinator resolver 取得当前查询证据；完整 observed 支撑目标 Provider；生产 host 成对接线；实际控制器 route/contact/stop 验证；同 AgentTask 三块连续堆叠。普通测试不证明实际碰撞、稳定性或停止行为。 / Remaining: production evidence resolution, observed support inference, host wiring, real route/contact/stop qualification, and continuous three-block execution.

## 显式嵌入接线 / Explicit embedding

```python
# resolve_preparation_inputs and resolve_relation_context must be supplied by
# the owning Coordinator integration, using persisted current evidence.
factory = build_stack_relation_execution_provider_factory(
    prepare_inputs=resolve_preparation_inputs,
)
host = build_persistent_host(
    profile,
    relation_execution_provider_factory=factory,
    resolve_relation_context=resolve_relation_context,
)
```

示例只展示注入位置，不提供虚构 resolver。原零参 factory 仍可构造关闭运动的 Provider；直接准备但未配置 resolver 会明确报错。Factory 的 motion_supported 仍恒为 False；停止路径仍由既有 worker/Gateway 所有。 / This illustrates injection only. The zero-argument factory remains constructible with motion disabled; direct preparation without a resolver fails explicitly. Stop ownership remains with the existing worker/Gateway.

## 验证 / Validation

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_route_inputs.py --tb=short
```

集成测试经过真实 Grounding.scene_facts/validate_scene_facts、PersistentPreparationProvider、CompleteRouteSelector 和 PreparedRoutes；外部机器人 snapshot、规划/接触结果用无动作 fixture。验证旋转和非零平移对象的功能点变换、身份过期/漂移、缺失输入、坏目标证据、规划失败、目标漂移与关闭运动。 / Tests run the real composition with substituted external mechanisms, including transformed targets and failure paths. No live physics claim is made.

结果：准备/执行/路线输入四套件 69 passed；Grounding/host/deployment 三套件 128 passed，共 197 passed。主审已对照 HEAD 复现原 12 个 Engine fixture 缺失 `_reserved_execution_actors`，本轮补测试初始化后全绿，未改生产身份检查。外部规划被替换，不是完整 GPU route readiness。 / Results: 69 focused and 128 broader tests pass (197 total). Parent reproduced the 12 original fixture failures against HEAD; test initialization now matches production without weakening checks. External planning is substituted, so this is not full GPU route readiness.
