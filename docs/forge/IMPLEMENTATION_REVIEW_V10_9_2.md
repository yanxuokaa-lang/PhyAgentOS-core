# v10.9.2 来源选择回归修复 / Source selection regression repair

## 结论 / Outcome

`task_19f02cc0b56d4c2d` 的 `blue_stage_grasp` 失败由 Core source selector
不能组合数组元素引起。本次恢复通用嵌套组装能力，保持 Producer 独立、Agent 选择、
Coordinator 取值/持久化、Consumer schema 校验及 Runtime admission 的既有边界。
The failure was a Core selection expressiveness regression. This repair restores
generic nested assembly without producer-specific joins or a second execution path.

源码与无运动验收通过；真实模型自主调用、新 Runtime 任务及完整视频验收仍待运行。
Source and no-motion acceptance pass; real-model autonomy, Runtime task execution
and complete video acceptance remain unmeasured in this change.

## Fresh review findings and disposition

- Blocker fixed: array internals were inaccessible, and dotted destination names
  became literal top-level keys. Typed source paths and optional `target_path`
  now copy exact values into nested objects/arrays, with collision and sparse-index errors.
- Major fixed: only the first three array identities were visible. Existing
  `forge_plan_ready` now provides paginated, one-level source browsing, scoped by
  NodeContextProvider. AgentLoop rejects browsing another node during a node turn.
- Major fixed during review: older source pages would disappear through generic
  Forge prompt compaction. Already paginated catalogs retain their paths and identities.
- Major fixed: a rejected, receipt-free turn started a second empty-history turn.
  Recent persisted rejection diagnostics are now projected; rejected turns stop
  before automatic continuation. Admitted pending receipts retain bounded continuation.
- Major fixed: Skill graph guidance included target generation although place
  needed a pre-existing destination binding. Guidance now resolves required
  immutable references before materializing the executable segment.
- Observability: `planning_node_blocked` is persisted as a Coordinator event.
  This is a runner checkpoint, not a new task status or a Tool execution fact.

## 既有七维验收 / Established seven dimensions

| Dimension | Result and evidence |
| --- | --- |
| Architecture integration | PASS: existing ready/select, NodeContextProvider, dispatch, receipt and Query wrapper; no Core producer IDs or inferred joins. |
| Recovery and idempotency | PASS: rejection feedback, no empty-history rejection continuation, pending receipt continuation and existing single-execution tests. |
| Robotics safety | PASS, no-motion only: stale/hidden sources and cross-node browse rejected; schema failure creates no selection/execution; no Action, simulator step or hardware call. |
| Context and performance | Functional PASS: paginated catalogs survive compaction; full candidate array still stays out of prompt. No real token/latency reduction claim. |
| Configuration and reproducibility | PASS for source/package: Skill manifest/package 2.3.1; archive validator succeeds. Active deployment unchanged; Node 0.1.16 does not need rebuilding. |
| Maintainability and observability | PASS: explicit typed paths, durable node diagnostics, synchronized workflow/developer docs and source-to-wrapper regression. |
| AgentLoop autonomy | Interface PASS: Agent declares each source/destination and identity match, Coordinator only resolves/copies/validates. Real LLM behavior remains for user acceptance. |

## Validation

- Core: `503 passed in 25.59s`.
- Skill: `335 passed in 7.24s`.
- Changed Python Ruff, compileall and `git diff --check`: PASS.
- New regression covers fifth array entry, reordered envelopes, cross-record
  assembly, exact scalar/vector copying, no mutation, sparse/overlap errors,
  stale/hidden evidence, schema rejection, compact receipt and exact Query execution.
- Real failed task was read from SQLite in read-only mode and cloned into a
  temporary workspace. Its blue entity, envelope and point-cloud artifact were
  selected by 17 explicit mappings; the original frozen schema accepted them and
  the real Coordinator persisted one selection. Executions: 0; Gateway calls: 0.
  Temporary workspace was removed; active task and Runtime were not changed.
- Archive: `/tmp/paos-v10.9.2-release-D4enl6/pick-place-workflow-2.3.1.tar.gz`,
  103674 bytes, existing archive SHA-256
  `4f7efc71151d3f610a842fae839d6c10c109aa9ad58ce6d6c85d129043c20c14`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
python scripts/package_skill.py examples/forge-skills/pick-place-workflow --output-dir /tmp/paos-skill-package
```

本轮未更改 Provider 时延实现或 timeout；先前日志中 headers/first_token unavailable
仍需在真实进程上验证。未把 schema 通过称为抓取可执行，也未把 Fake Gateway 测试称为真实运动成功。
Provider timing and timeout behavior are unchanged; unavailable streaming timing
still needs real-process diagnosis. Schema acceptance does not prove physical feasibility.
