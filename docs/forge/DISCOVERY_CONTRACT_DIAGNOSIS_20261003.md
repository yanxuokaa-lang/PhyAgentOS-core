# Discovery contract availability diagnosis / 发现阶段契约可用性诊断

## Recorded facts / 日志事实

Task `task_418a83dba6e34093`, revision `revision_7fd78068bb6a46ed`, Skill 2.10.7.
Session: `cli_rgb-benchmark-injected-20261001-5.jsonl` in the deployed workspace sessions directory.
Five distinct `forge_tool_context` requests succeeded before task creation. Discovery then used 37 shell calls, with no `forge_tool_query`, plan or Action. The task had no execution records. JSONL save timestamps do not measure individual tool durations.

五个不同工具的 context 已成功返回，随后却陷入 shell 核查；尚未执行感知、Qwen、抓取或放置，不能归因于这些模块。

## Cause / 原因

`prompt_context._tool_call_names` counts both assistant requests and named tool responses: five actual reads become ten. `visible_tool_names` removes context after this history threshold. Binding projections omit input schemas, activation compaction removes Skill prose, and budget compaction can discard the original contracts. No formal recovery route then remains for context; hiding `read_file` encourages shell substitution.

计数混淆请求和回执，且不区分不同工具。可见性与压缩组合导致“契约从请求消失，但正式读取入口也被隐藏”。这是 control-plane 可用性错误，不是 Runtime admission 错误。

## Evidence bounds / 证据边界

Actual session-prefix replay reproduces five requests counted as ten and context disappearance. Forced token-estimator replay demonstrates contracts can be removed while context stays hidden; it is not an exact replay of an unsaved provider wire request.
History-count hiding originated in v11.9.13; v12.5.13 repairs later planning recovery, and v12.5.14 is deployment. Neither fixes this discovery path.

## Repair / 修复原则

Keep formal context reacquisition and persisted Skill retrieval available. Do not copy full schemas/Skill prose into every request or introduce a second contract authority. Successful distinct context acquisition is useful preparation; repeating it indefinitely is not task progress. Preserve Registry/Coordinator/Gateway admission and provider-neutral discovery.

Implementation uses `forge_task_get(include_skill_instructions=true)` to restore `active_skill_instructions` (falling back to the original primary instructions). Only this opt-in field survives lifecycle receipt compaction. Default task reads stay compact; filesystem reads are not a substitute for the task-owned Skill snapshot.

实现复用现有任务读取工具，按需取回当前任务已保存的约束；不重新激活 Skill、不创建第二个任务、不把后续安装的文件视为旧任务的执行规则。

保留正式获取通道，不把控制面核查写成执行事实；不加入 RGB、相机名或模型专用分支。
