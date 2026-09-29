# Changelog
## Archive
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.2.3 (2026-09-29 21:14) - codex

### 实际修改 / Implemented changes [完成]
- [eval] [fix] 中文：经用户授权，通过 Coordinator 取消 Runtime binding 已失效的旧任务 `task_f07d89c196bb45e2`，并创建绑定当前 Runtime `runtime_5dbc5429884b4698` 的恢复任务 `task_aec44953a71343ce`；未复用旧任务证据。 (local)
- [Eval] [Fix] English: With user authorization, cancel stale-bound task `task_f07d89c196bb45e2` through the Coordinator and create recovery task `task_aec44953a71343ce` bound to current Runtime `runtime_5dbc5429884b4698`; no old-task evidence was reused. (local)
- [sense] [exp] 中文：新任务唯一一次 `scene.observe` 与由其派生的唯一一次 `scene.understand` 均成功并落盘；返回 4 entities、6 relations、4 spatial envelopes，provider 为 `available`。 (local)
- [Sense] [Exp] English: The new task's single `scene.observe` and single derived `scene.understand` both succeeded and were persisted; the result contains 4 entities, 6 relations, 4 spatial envelopes, with provider `available`. (local)

### 验证结果 / Validation
- 旧任务状态：`cancelled`；新任务：`task_aec44953a71343ce`，当前保留用于后续显式授权的验收阶段。
- Observation record：`tool_6d7b32a7b7d14a51`。
- Understanding record：`tool_72b181752e044c4d`。
- Scene revision：`a948db781dcd4539bf2802ecbf47eb9f-1`。
- Runtime 与 Qwen user service 均为 `active`；Qwen 推理结束后 `is_sleeping=true`。
- Session Tool call 清单确认未调用 `scene.bind`、`task.goal`、GraspNet、`manipulation.prepare`、Action、Session 或 simulator step。

### 文件变更详情 / File changes
- [修改] `changelog/2026-09_part20.md:L3-L39`：记录任务迁移、只读实测记录和无运动边界。
- [修改] `CHANGELOG.md:L5-L41`：同步最近版本 v12.2.3 的完整记录。

### 关键 Diff / Key diff
**修改前 / Before:**
```text
旧 AgentTask 冻结的 Runtime binding 已失效，scene.understand 被 Coordinator 拒绝。
```

**修改后 / After:**
```text
旧任务经 Coordinator 取消；新任务绑定当前 Runtime，并以全新 observation 完成唯一一次 scene.observe → scene.understand 无运动验收。
```
+
### Git 提交 / Git commit
- Commit: `c6b6d1d`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-09-29 21:21



## v12.2.2 (2026-09-29 20:19) - codex

### 变更摘要
- [sense] [fix] 中文：修复模型所有权混用；PAOS 主 Agent 继续使用 `custom/gpt-5.6-sol`（shuaiapi），RobotWin `scene.understand` 独立使用本地 `qwen3_vl_vllm`，不再把主模型 fallback 或 secret 传入 Dora。 (local)
- [Sense] [Fix] English: Fix model-ownership mixing; keep the PAOS main Agent on `custom/gpt-5.6-sol` (shuaiapi), while RobotWin `scene.understand` independently uses local `qwen3_vl_vllm` without forwarding the main-model fallback or secret into Dora. (local)
- [env] [chore] 中文：发布并安装 `pick-place-workflow 2.8.8` / `robotwin20_persistent_host 0.8.7`，经用户授权强制停止带非终态绑定的旧 Runtime，并使用相同 `robotwin-blocks-ranking-graspnet` profile 恢复。 (local)
- [Env] [Chore] English: Publish and install `pick-place-workflow 2.8.8` / `robotwin20_persistent_host 0.8.7`, force-stop the old Runtime with non-terminal bindings under user authorization, and restore the same `robotwin-blocks-ranking-graspnet` profile. (local)
- [eval] [exp] 中文：完成 discovery/readiness 和一次用户要求的只读 `scene.observe → scene.understand` 实测；未创建 AgentTask，未调用 Action/Session，未执行仿真或硬件运动。 (local)
- [Eval] [Exp] English: Complete discovery/readiness and one user-requested read-only `scene.observe → scene.understand` run; create no AgentTask, invoke no Action/Session, and perform no simulation or hardware motion. (local)

### 发布产物
- Node: `/home/yanxu/paos-release/nodes/robotwin20_persistent_host-0.8.7-linux-x86_64.tar.gz`
- Node SHA-256: `cb5f6c09b07f86d8f91f2bcfa9a186c351ed4b2de879527d84eed1d295ef1781`
- Node size: `386938` bytes
- Skill: `/home/yanxu/paos-release/skills/pick-place-workflow-2.8.8.tar.gz`
- Skill SHA-256: `b6eeefac4f5f5f573cb64ca4deaba145748d8eb62c117e94791ea6339466a7bd`
- Skill size: `114479` bytes

### 验证结果
- Adapter/Skill 聚焦测试：`201 passed in 3.58s`。
- Artifact lock / install discovery 回归：`100 passed in 3.29s`。
- Ruff：`All checks passed!`；`git diff --check` 通过。
- 隔离安装：独立 HOME 成功安装 `pick-place-workflow 2.8.8`。
- Live Runtime：Skill `2.8.8`、Node `0.8.7`，Gateway ready，10/10 Tool context ready。
- 模型分层：PAOS main Agent 为 `custom/gpt-5.6-sol`；`scene.understand` context 为本地 Qwen provider，`ready=true`、`motion_authorized=false`。
- 实际只读查询：`scene.observe` 与 `scene.understand` 均 HTTP 200 / available；4 entities、6 relations、4 spatial envelopes、16 derived artifacts、1 ambiguity，未执行运动。
- Qwen service：MainPID `1403439`，`active/running`，`NRestarts=0`；推理前为 sleep，按需唤醒后 lifecycle 自动回到 `is_sleeping=true`。
- Secret 分离：当前 Dora session 未包含 `ROBOTWIN20_MODEL_API_BASE`、`ROBOTWIN20_MODEL_API_KEY`、`ROBOTWIN20_MODEL` 或 `ROBOTWIN20_REASONING_EFFORT`。

### 残留安全事项
- 修复前的历史失败启动日志曾展开 fallback 环境变量，应视为凭据日志；2.8.8 已阻止新日志继续携带该 secret。历史日志清理与 provider key 轮换需另行明确授权。

### 文件变更详情

#### [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L698-L709

**修改前：**
```text
        if (any(depth_artifact.get(key) != binding[key] for key in IDENTITY_KEYS)
                or depth_artifact.get("frame_id") != binding["frame_id"]):
                "observed_support_unavailable", "scene depth lineage differs from binding"
```

**修改后：**
```text
        observed_frame = observed.get("frame")
        if (
            any(observed.get(key) != binding[key] for key in IDENTITY_KEYS)
            or not isinstance(observed_frame, Mapping)
            or observed_frame.get("frame_id") != binding["frame_id"]
        ):
                "observed_support_unavailable", "scene observation lineage differs from binding"
```

**修改说明**：保留 observed-depth lineage 修复。

---

#### [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/openai_scene_understanding.py` L510-L516, L525-L530, L534-L541

**修改前：**
```text
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                max_completion_tokens=self.config.max_output_tokens,
                response_format={
            )
```

**修改后：**
```text
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": [
                "max_completion_tokens": self.config.max_output_tokens,
                "response_format": {
            }
            if self.config.reasoning_effort is not None:
```

**修改说明**：保留 2.8.7 已验证的 Chat Completions 兼容实现。

---

#### [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py` L118-L122, L456-L517

**修改前：**
```text
    if model_provider == "qwen3_vl_vllm_fallback":
```

**修改后：**
```text
    if model_provider in {"qwen3_vl_vllm", "qwen3_vl_vllm_fallback"}:
        elif provider == "qwen3_vl_vllm":
            required = {
                "provider", "api_base", "model", "api_key_env",
                "timeout_seconds", "max_output_tokens", "lifecycle",
            }
            if set(model) != required:
```

**修改说明**：新增纯 qwen3_vl_vllm provider，并让纯 Qwen 与兼容 fallback 模式共享 operator_recovery context 语义。

---

#### [修改] `examples/forge-adapters/robotwin20/tests/test_grounding.py` L948-L952, L975-L979, L986-L993, L996-L1001

**修改前：**
```text
    observed["artifacts"] = [{
        "kind": "depth", "ref": depth_ref,
        **{key: request[key] for key in ("observation_ref", "scene_revision", "calibration_ref")},
        "frame_id": "camera",
    }]
@pytest.mark.parametrize("defect", ["missing_mask", "stale_mask", "missing_depth"])
    else:
```

**修改后：**
```text
    observed["artifacts"] = [{"kind": "depth", "ref": depth_ref, "media_type": "application/x-npy"}]
@pytest.mark.parametrize("defect", ["missing_mask", "stale_mask", "missing_depth", "stale_observation"])
    elif defect == "missing_depth":
    else:
        observed["scene_revision"] = "old-scene"
    expected_message = "scene observation lineage differs from binding" if defect == "stale_observation" else None
    with pytest.raises(PreparationProviderError, match=expected_message):
```

**修改说明**：同步发布实现、测试或版本元数据。

---

#### [修改] `examples/forge-adapters/robotwin20/tests/test_openai_scene_understanding.py` L150-L154

**修改前：**
```text
（无删除行；新增内容）
```

**修改后：**
```text
    assert payload["reasoning_effort"] == "high"
```

**修改说明**：同步发布实现、测试或版本元数据。

---

#### [修改] `examples/forge-adapters/robotwin20/tests/test_persistent_host.py` L220-L229, L242-L246, L289-L308, L328-L336

**修改前：**
```text
def test_qwen_provider_context_exposes_operator_owned_recovery_without_side_effects():
        model_provider="qwen3_vl_vllm_fallback",
```

**修改后：**
```text
@pytest.mark.parametrize(
    "model_provider", ["qwen3_vl_vllm", "qwen3_vl_vllm_fallback"]
)
def test_qwen_provider_context_exposes_operator_owned_recovery_without_side_effects(
    model_provider,
):
        model_provider=model_provider,
```

**修改说明**：覆盖纯 Qwen provider 构建与两种 Qwen 模式的 operator_recovery。

---

#### [修改] `examples/forge-skills/pick-place-workflow/CHANGELOG.md` L1-L28

**修改前：**
```text
（无删除行；新增内容）
```

**修改后：**
```text
## v2.8.8 (2026-09-29)

- 中文：将 RobotWin 场景理解切换为纯本地 Qwen vLLM provider，移除 shuaiapi fallback 及 Dora 环境中的主模型 secret；PAOS 主 Agent provider 保持独立。
- English: Move RobotWin scene understanding to a local-Qwen-only vLLM provider, remove the shuaiapi fallback and main-model secret from Dora, and keep the PAOS main-Agent provider independent.

## v2.8.7 (2026-09-29)

```

**修改说明**：同步发布实现、测试或版本元数据。

---

#### [修改] `examples/forge-skills/pick-place-workflow/profiles/robotwin-persistent/dataflow-graspgen.yaml` L10-L13

**修改前：**
```text
      ROBOTWIN20_MODEL_API_BASE: ${ROBOTWIN20_MODEL_API_BASE}
      ROBOTWIN20_MODEL_API_KEY: ${ROBOTWIN20_MODEL_API_KEY}
      ROBOTWIN20_MODEL: ${ROBOTWIN20_MODEL}
      ROBOTWIN20_REASONING_EFFORT: ${ROBOTWIN20_REASONING_EFFORT}
```

**修改后：**
```text
（无新增行；删除内容）
```

**修改说明**：从 GraspGen Dora 环境移除主模型与 secret 变量。

---

#### [修改] `examples/forge-skills/pick-place-workflow/profiles/robotwin-persistent/dataflow.yaml` L12-L15

**修改前：**
```text
      ROBOTWIN20_MODEL_API_BASE: ${ROBOTWIN20_MODEL_API_BASE}
      ROBOTWIN20_MODEL_API_KEY: ${ROBOTWIN20_MODEL_API_KEY}
      ROBOTWIN20_MODEL: ${ROBOTWIN20_MODEL}
      ROBOTWIN20_REASONING_EFFORT: ${ROBOTWIN20_REASONING_EFFORT}
```

**修改后：**
```text
（无新增行；删除内容）
```

**修改说明**：从 Dora 环境移除主模型 endpoint/model/key/reasoning 变量。

---

#### [修改] `examples/forge-skills/pick-place-workflow/profiles/robotwin-persistent/persistent-host-graspgen.yaml` L16-L31

**修改前：**
```text
  provider: qwen3_vl_vllm_fallback
  primary:
    api_base: http://127.0.0.1:8012/v1
    model: qwen3-vl-4b-awq
    api_key_env: ""
    timeout_seconds: 30
    max_output_tokens: 768
```

**修改后：**
```text
  provider: qwen3_vl_vllm
  api_base: http://127.0.0.1:8012/v1
  model: qwen3-vl-4b-awq
  api_key_env: ""
  timeout_seconds: 30
  max_output_tokens: 768
  lifecycle:
```

**修改说明**：GraspGen profile 同步采用纯本地 Qwen provider。

---

#### [修改] `examples/forge-skills/pick-place-workflow/profiles/robotwin-persistent/persistent-host.yaml` L16-L31

**修改前：**
```text
  provider: qwen3_vl_vllm_fallback
  primary:
    api_base: http://127.0.0.1:8012/v1
    model: qwen3-vl-4b-awq
    api_key_env: ""
    timeout_seconds: 30
    max_output_tokens: 768
```

**修改后：**
```text
  provider: qwen3_vl_vllm
  api_base: http://127.0.0.1:8012/v1
  model: qwen3-vl-4b-awq
  api_key_env: ""
  timeout_seconds: 30
  max_output_tokens: 768
  lifecycle:
```

**修改说明**：当前 GraspNet 场景理解只使用本地 Qwen vLLM，不再定义 shuaiapi fallback。

---

#### [修改] `examples/forge-skills/pick-place-workflow/profiles/robotwin-persistent/runtime.env.example` L11-L14, L33-L37

**修改前：**
```text
ROBOTWIN20_MODEL_API_BASE=
ROBOTWIN20_MODEL=gpt-5.6-sol
ROBOTWIN20_REASONING_EFFORT=high
# Supply ROBOTWIN20_MODEL_API_KEY through the operator secret environment. Do
# not store the credential in this template, the Skill Bundle, logs, or traces.
```

**修改后：**
```text
# Scene understanding is profile-owned and uses the local Qwen vLLM endpoint.
# PAOS main-Agent provider credentials remain in the PAOS provider configuration
# and must not be forwarded through this Runtime environment.
```

**修改说明**：说明 PAOS 主 Agent provider 与 Runtime 场景 provider 独立。

---

#### [修改] `examples/forge-skills/pick-place-workflow/pyproject.toml` L1-L5

**修改前：**
```text
version = "2.8.4"
```

**修改后：**
```text
version = "2.8.8"
```

**修改说明**：同步发布实现、测试或版本元数据。

---

#### [修改] `examples/forge-skills/pick-place-workflow/skill.yaml` L1-L5, L35-L38, L74-L77, L113-L116, L152-L155, L191-L194, L220-L228

**修改前：**
```text
version: "2.8.4"
      - ROBOTWIN20_MODEL_API_BASE
      - ROBOTWIN20_MODEL_API_KEY
      - ROBOTWIN20_MODEL
      - ROBOTWIN20_REASONING_EFFORT
      - ROBOTWIN20_MODEL_API_BASE
      - ROBOTWIN20_MODEL_API_KEY
```

**修改后：**
```text
version: "2.8.8"
      artifact_id: robotwin20_persistent_host-0.8.7-linux-x86_64
      version: "0.8.7"
      sha256: cb5f6c09b07f86d8f91f2bcfa9a186c351ed4b2de879527d84eed1d295ef1781
```

**修改说明**：发布 Skill 2.8.8 / Node 0.8.7，移除 Runtime 对主模型变量的 required_environment。

---

#### [修改] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py` L267-L271

**修改前：**
```text
    assert bundle_manifest["version"] == "2.8.4"
```

**修改后：**
```text
    assert bundle_manifest["version"] == "2.8.8"
```

**修改说明**：同步发布实现、测试或版本元数据。

---

#### [修改] `examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py` L78-L82, L93-L110, L160-L164

**修改前：**
```text
def test_robotwin_dataflow_forwards_profile_owned_route_geometry_source():
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_MODEL"] == "${ROBOTWIN20_MODEL}"
    assert dataflow["nodes"][0]["env"]["ROBOTWIN20_REASONING_EFFORT"] == (
        "${ROBOTWIN20_REASONING_EFFORT}"
    assert template_names == set(profile.required_environment) - {
        "ROBOTWIN20_MODEL_API_KEY",
        *profile.environment,
```

**修改后：**
```text
def test_robotwin_dataflow_keeps_scene_model_profile_owned():
    assert {
        "ROBOTWIN20_MODEL_API_BASE",
        "ROBOTWIN20_MODEL_API_KEY",
        "ROBOTWIN20_MODEL",
        "ROBOTWIN20_REASONING_EFFORT",
    }.isdisjoint(dataflow["nodes"][0]["env"])
```

**修改说明**：验证 Qwen 配置由 profile 所有且主模型 secret 不进入 Dora。

### Git 提交
- Commit: `3061288`
- Branch: `feature/planning-loop`
- 时间: 2026-09-29 20:19

## v12.2.1 (2026-09-29 18:46) - codex

### 实际修改 / Implemented changes [完成]
- [env] [fix] 部署 operator-owned `paos-qwen3vl-vllm.service`，使用已验收的本地 AWQ/vLLM 0.11.2/sleep-mode 参数并仅监听 `127.0.0.1:8012`；PAOS 保持 provider consumer，不拥有模型进程。(local)
- [Env] [Fix] Deploy the operator-owned `paos-qwen3vl-vllm.service` with the accepted local AWQ, vLLM 0.11.2, and sleep-mode parameters on loopback-only `127.0.0.1:8012`; PAOS remains a provider consumer and does not own the model process.(local)
- [env] [fix] 根分区 100% 导致通用 unit verifier 无法创建工作目录；服务使用 `/home/yanxu/tmp/paos-qwen3vl-vllm` 专用 `TMPDIR`，未删除用户数据。(local)
- [Env] [Fix] The full root filesystem prevented the generic unit verifier from creating a working directory; the service uses dedicated `/home/yanxu/tmp/paos-qwen3vl-vllm` temporary storage, and no user data was deleted.(local)
- [eval] [exp] 服务 active/enabled 且无重启；模型 API、sleep/wake、7.01 秒 RGB structured-output smoke 与全部 PAOS Tool context 通过，无 AgentTask、PAOS Query/Action/Session 或运动。(local)
- [Eval] [Exp] The service is active/enabled with no restart; model API, sleep/wake, a 7.01-second RGB structured-output smoke, and every PAOS Tool context passed, with no AgentTask, PAOS Query/Action/Session, or motion.(local)
- [docs] [docs] 保存 Qwen provider outage 的 connection-refused 根因、systemd 恢复、sleep API、`TMPDIR` 磁盘分叉与 no-motion 运维边界。(local)
- [Docs] [Docs] Preserve the connection-refused root cause, systemd recovery, sleep API, `TMPDIR` storage branch, and no-motion operations boundary for Qwen provider outages.(local)
- [sense] [fix] `scene.understand` ToolSpec 发布通用恢复语义，Qwen deployment context 发布 operator-owned 诊断/恢复命令；Tool 不隐式启动 provider，不刷新未变化场景，不在 readiness 改变前重试。(local)
- [Sense] [Fix] The `scene.understand` ToolSpec publishes generic recovery semantics while the Qwen deployment context publishes operator-owned diagnosis/recovery commands; the Tool does not implicitly start providers, refresh an unchanged scene, or retry before readiness changes.(local)
- [eval] [test] ToolSpec、Qwen/non-Qwen context 与 contract 测试 `36 passed`，Ruff、compileall、diff check 通过；未调用 Query/Action/Session 或运动。(local)
- [Eval] [Test] ToolSpec, Qwen/non-Qwen context, and contract tests passed `36`, with Ruff, compileall, and diff check passing; no Query, Action, Session, or motion was invoked.(local)

### 影响文件 / Affected files
- `/home/yanxu/.config/systemd/user/paos-qwen3vl-vllm.service:L1-L20`
- `PhyAgentOS/forge/capability_runtime/understanding.py:L140-L154`
- `examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml:L9-L21`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py:L62-L122,L651-L657`
- `examples/forge-adapters/robotwin20/README.md:L208-L253`
- `examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py:L95-L115`
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py:L222-L279`
- `changelog/2026-09_part20.md:L3-L59`
- `CHANGELOG.md:L5-L49`

### 关键 Diff / Key diff
```diff
- 127.0.0.1:8012: connection refused
+ user service: active + enabled, model API healthy
+ level-1 sleeping=true, GPU memory=276 MiB
+ PAOS scene.understand context=ready
+ ToolSpec: bounded provider recovery, unchanged-observation reuse, no implicit start
+ Qwen context: operator diagnosis/start/verification commands, motion_authorized=false
```

### 验证 / Verification
- Focused ToolSpec/context/contract suite: `36 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Existing Runtime PID `1235822` and worker `1235873` were not restarted.

### Git 提交
- Commit: `2b40c13`
- Branch: `feature/planning-loop`

## v12.2.0 (2026-09-29 18:10) - codex

### 实际修改 / Implemented changes [完成]
- [sense] [fix] operator-owned Qwen vLLM readiness 只读 `/is_sleeping`；双 provider 失败后 `scene.understand` 动态 context fail closed，并返回不可重试 provider error。(local)
- [Sense] [Fix] Operator-owned Qwen vLLM readiness reads only `/is_sleeping`; after both providers fail, the dynamic `scene.understand` context fails closed and returns a non-retryable provider error.(local)
- [agent] [fix] AgentLoop 持久化精确 provider failure 后立即交还控制权，不重复模型请求、不刷新 observation，并延迟同批剩余 Tool；非 provider 请求错误保持可修正。(local)
- [Agent] [Fix] AgentLoop immediately returns control after persisting the exact provider failure, without another model request or observation refresh, and defers remaining Tools in the same response; non-provider request errors remain correctable.(local)
- [eval] [test] adapter/provider/Skill `66 passed`，AgentLoop/prompt 聚焦 `5 passed`；Ruff、compileall、diff check 通过，全程 Query-only 且 `motion_authorized=false`。(local)
- [Eval] [Test] Adapter/provider/Skill tests passed `66`, focused AgentLoop/prompt tests passed `5`, and Ruff, compileall, and diff check passed; execution remained Query-only with `motion_authorized=false`.(local)

### 影响文件 / Affected files
- `qwen3_vl_vllm_lifecycle.py:L76-L100,L274-L276`；`scene_understanding_fallback.py:L83-L137,L196-L203`；`understanding.py:L102-L119`；`persistent_host.py:L588-L614`。
- `PhyAgentOS/agent/loop.py:L1118-L1150,L1269-L1302`；`PhyAgentOS/agent/prompt_context.py:L726-L732,L1032-L1035`；`PhyAgentOS/forge/capability_runtime/understanding.py:L342-L350`。
- `test_qwen3_vl_vllm_lifecycle.py:L76-L100`；`test_scene_understanding_fallback.py:L65-L141`；`test_persistent_host.py:L246-L269,L319-L325`；`test_scene_understand_provider.py:L121-L138`；`tests/test_agent_foundation.py:L27-L36,L534-L620`；`tests/test_prompt_context.py:L521-L528,L640-L661`。

### 关键 Diff / Key diff
```diff
- retryable provider outage -> repeated model/discovery attempts
+ read-only provider readiness -> dynamic Tool not-ready
+ exact non-retryable provider failure -> persisted handoff, no observation refresh
```

### Git 提交
- Commit: `2be84db`
- Branch: `feature/planning-loop`


## v12.0.1 (2026-09-29 16:17) - codex

### 实际修改 / Implemented changes
- [env] [fix] [完成] 本地安装并验证 `pick-place-workflow 2.8.6`，包含 `robotwin-blocks-ranking-graspnet` profile 与 Node `0.8.5`；目标 Runtime 启动因未配置 `ROBOTWIN20_MODEL_API_KEY` 在进程启动前 fail closed。(local)
- [Env] [Fix] [Completed] Locally installed and verified `pick-place-workflow 2.8.6` with the `robotwin-blocks-ranking-graspnet` profile and Node `0.8.5`; target Runtime failed closed before process launch because `ROBOTWIN20_MODEL_API_KEY` was not configured.(local)
- [eval] [exp] Bundle archive validation、`paos skill install/inspect/list` 通过；未创建 AgentTask，未调用 Query/Action/Session，未产生运动或视频 manifest。(local)
- [Eval] [Exp] Bundle archive validation and `paos skill install/inspect/list` passed; no AgentTask, Query/Action/Session, motion, or video manifest was created.(local)

### 影响文件 / Affected files
- `changelog/2026-09_part20.md:L3-L20`
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L12,L238-L248` (source read/packaged, not modified in this turn)

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.12 (2026-09-29 07:10) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/planning_loop.py:L944-L951` 增加 projection join identity 逐字匹配和旧 continuation 别名拒绝提示。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/planning_loop.py:L944-L951` adds exact projection join-identity matching and rejects reuse of aliases from old continuations.(local)
- [eval] [test] [完成] projection prompt 回归 `2 passed`，Ruff、compileall、diff check 通过。(local)
- [Eval] [Test] [Completed] Projection prompt regression passed `2`, with Ruff, compileall, and diff check passing.(local)

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.11 (2026-09-29 06:55) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/planning_loop.py:L938-L949` 按 projection 声明字段选择 source：`grasp.propose` 使用当前 understanding，`manipulation.prepare` 使用直接前驱 `grasp.propose` 的 `candidate_set_ref/candidates`。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/planning_loop.py:L938-L949` selects projection sources by declared fields: `grasp.propose` uses current understanding, while `manipulation.prepare` uses the direct predecessor `grasp.propose` `candidate_set_ref/candidates`.(local)
- [runtime] [fix] [完成] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L65-L78` 对齐 core ToolSpec 与 Bundle YAML 的 `top_level_fields: []`。(local)
- [Runtime] [Fix] [Completed] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L65-L78` aligns the core ToolSpec and Bundle YAML `top_level_fields: []` declaration.(local)
- [eval] [test] [完成] projection/Agent/Runtime 回归共 `263 passed`，Ruff、compileall、diff check 通过。(local)
- [Eval] [Test] [Completed] Projection/Agent/Runtime regressions passed `263`, with Ruff, compileall, and diff check passing.(local)

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.10 (2026-09-29 05:35) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/planning/projection.py:L155-L190` 对声明字段先读同一成功 record 的 response data，缺失时读取同一 record 的 request arguments；`grasp.propose` 的 freshness/max-age 不再被误报缺失。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/planning/projection.py:L155-L190` reads declared fields from the same successful record's response data first, then request arguments when absent; `grasp.propose` freshness/max-age are no longer falsely reported missing.(local)
- [skill] [fix] [完成] Skill `2.8.4` 生成新的 binding，避免 blocked task 复用旧 ToolSpec digest。(local)
- [Skill] [Fix] [Completed] Skill `2.8.4` creates a fresh binding so the blocked task cannot reuse the old ToolSpec digest.(local)
- [eval] [test] [完成] 聚焦 projection/Agent/Runtime 测试 `120 passed`，Ruff、compileall、diff check 通过。(local)
- [Eval] [Test] [Completed] Focused projection/Agent/Runtime tests passed `120`, with Ruff, compileall, and diff check passing.(local)

### Git 提交
- Commit: `a39ae98`
- Branch: `feature/planning-loop`

## v11.10.9 (2026-09-29 05:10) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L52-L78` 将 `candidate_set_for_entity_v1` 注册到 Gateway 实际返回的 core ToolSpec，避免只改 Bundle YAML 而运行时仍无 projection。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L52-L78` registers `candidate_set_for_entity_v1` in the core ToolSpec actually returned by Gateway, avoiding a YAML-only change that leaves the runtime without the projection.(local)
- [eval] [test] [完成] runtime composition 回归与规划/Agent 聚焦测试通过 `22`；重启的 `2.8.3` GraspNet Runtime `/tools/manipulation.prepare` 已返回 projection。(local)
- [Eval] [Test] [Completed] Runtime composition and focused planning/Agent tests passed `22`; the restarted `2.8.3` GraspNet Runtime `/tools/manipulation.prepare` returned the projection.(local)

### Git 提交
- Commit: `b71321c`
- Branch: `feature/planning-loop`

## v11.10.8 (2026-09-29 04:43) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/planning/contracts.py:L61-L113`、`PhyAgentOS/planning/projection.py:L140-L214` 增加通用 direct-field/filtered-collection projection；Coordinator 从授权 `grasp.propose` record 生成 `manipulation.prepare` 完整参数并按节点实体过滤候选，不把大数组交给模型。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/planning/contracts.py:L61-L113` and `PhyAgentOS/planning/projection.py:L140-L214` add generic direct-field/filtered-collection projection; the Coordinator builds complete `manipulation.prepare` arguments from an authorized `grasp.propose` record and filters by node entity without sending the large array to the model.(local)
- [skill] [fix] [完成] `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml:L6-L24` 声明 `candidate_set_for_entity_v1`；Skill `2.8.3` 生成新的冻结 ToolSpec digest，旧任务不复用新契约。(local)
- [Skill] [Fix] [Completed] `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml:L6-L24` declares `candidate_set_for_entity_v1`; Skill `2.8.3` produces a fresh frozen ToolSpec digest and existing tasks do not reuse the new contract.(local)
- [eval] [test] [完成] 规划 projection 3 passed，Forge Tool API 21 passed，AgentLoop/基础 101 passed，pick-place planning/runtime/discovery 31 passed；Ruff、compileall、diff check 通过。(local)
- [Eval] [Test] [Completed] Planning projection passed 3, Forge Tool API passed 21, AgentLoop/foundation passed 101, pick-place planning/runtime/discovery passed 31; Ruff, compileall, and diff check passed.(local)

### Git 提交
- Commit: `28a6e32`
- Branch: `feature/planning-loop`

## v11.10.7 (2026-09-29 16:35) - codex

### 实际修改 / Implemented changes
- [docs] [chore] [完成] `changelog/2026-09_part19.md:L61-L63`、`CHANGELOG.md:L24-L26` 回填 `v11.10.6` 的真实提交 `3683d7c`。(local)
- [Docs] [Chore] [Completed] `changelog/2026-09_part19.md:L61-L63` and `CHANGELOG.md:L24-L26` fill in the real `v11.10.6` commit `3683d7c`.(local)

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.6 (2026-09-29 16:20) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/tools/forge_tool_api.py:L121-L196,L595-L608` 将 `forge_task_*`/`forge_plan_*` lifecycle context 请求留在本地 ToolRegistry；未注册时 fail closed，不再向 Gateway 查询本地名。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/tools/forge_tool_api.py:L121-L196,L595-L608` keeps `forge_task_*`/`forge_plan_*` lifecycle context requests in the local ToolRegistry; unregistered names fail closed instead of querying the Gateway.(local)
- [agent] [fix] [完成] `PhyAgentOS/agent/loop.py:L375-L380` 注入 Registry lookup，使 `awaiting_replan` 恢复回合可直接发现 `forge_task_begin_revision`。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/loop.py:L375-L380` injects the Registry lookup so `awaiting_replan` recovery turns can directly discover `forge_task_begin_revision`.(local)
- [eval] [test] [完成] `tests/test_forge_tool_api.py:L9-L56` 覆盖本地恢复 context 无 Gateway 调用；Forge Tool API `21 passed`，AgentLoop `77 passed`。(local)
- [Eval] [Test] [Completed] `tests/test_forge_tool_api.py:L9-L56` covers local recovery context with no Gateway call; Forge Tool API passed `21` and AgentLoop passed `77`.(local)

### 关键 Diff / Key Diff
```diff
+ if tool_id.startswith(("forge_task_", "forge_plan_")):
+     return local_registry_schema_or_local_tool_unavailable(tool_id)
  return await gateway_tool_spec_and_context(tool_id)
```

### 验证 / Verification
- `tests/test_forge_tool_api.py` -> `21 passed`。
- `tests/test_agent_foundation.py` -> `77 passed`。
- `compileall` and `git diff --check` -> passed.

### Git 提交
- Commit: `3683d7c`
- Branch: `feature/planning-loop`

## v11.10.5 (2026-09-29 02:35) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/plan_proposal.py:L351-L358,L387-L395` 将任务 verification contract 的 `goal/success_criteria` 由 Coordinator 继承到 manipulation 节点，避免模型重复组装导致 intent 缺字段。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/plan_proposal.py:L351-L358,L387-L395` lets the Coordinator inherit verification `goal/success_criteria` into manipulation nodes, avoiding missing intent fields caused by repeated model assembly.(local)
- [eval] [test] [完成] `tests/test_plan_proposal_bindings.py:L203-L214` 新增继承回归；planning selection/intent focused suite `26 passed`，compileall 和 diff check 通过。(local)
- [Eval] [Test] [Completed] `tests/test_plan_proposal_bindings.py:L203-L214` adds inheritance regression; planning selection/intent focused suite passed `26`, with compileall and diff check passing.(local)

### 关键 Diff / Key Diff
```diff
+ Coordinator adds task.verification.goal and success_criteria to manipulation node bindings
+ before trusted ManipulationIntent validation
```

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.4 (2026-09-29 01:20) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/loop.py:L148-L162,L1770-L1795` 在任务已经由 Coordinator 持久化为 `awaiting_replan` 时保留恢复状态，不再被 model timeout 二次终结；普通执行中失败仍 fail closed。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/loop.py:L148-L162,L1770-L1795` preserves a Coordinator-persisted `awaiting_replan` state instead of terminalizing it after a model timeout; ordinary executing failures remain fail closed.(local)
- [eval] [test] [完成] `tests/test_agent_foundation.py:L82-L91` 覆盖两种状态分支；聚焦 `10 passed`，compileall 和 diff check 通过。(local)
- [Eval] [Test] [Completed] `tests/test_agent_foundation.py:L82-L91` covers both task-state branches; focused tests passed `10`, with compileall and diff check passing.(local)

### 关键 Diff / Key Diff
```diff
- fail_task(task_id, reason)
+ if task.status != awaiting_replan:
+     fail_task(task_id, reason)
+ else:
+     preserve Coordinator recovery checkpoint
```

### 验证 / Verification
- AgentLoop focused tests: `10 passed, 67 deselected`。
- `compileall` and `git diff --check` passed.

### Git 提交
- Commit: 待提交
- Branch: `feature/planning-loop`

## v11.10.3 (2026-09-28 23:10) - codex

### 实际修改 / Implemented changes
- [sense] [fix] [完成] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/observed_support.py:L62-L126` 从校准深度图估计水平支撑面，排除当前所有非空实例 mask，并保留 depth/mask 来源；保留既有点数、平面一致性和坡度限制。(local)
- [Sense] [Fix] [Completed] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/observed_support.py:L62-L126` estimates horizontal support from calibrated depth, excludes every current non-empty instance mask, and preserves depth/mask provenance while retaining existing point-count, plane-consensus, and slope limits.(local)
- [sense] [fix] [完成] `grounding.py:L25-L40,L663-L751` 保持显式 `on/is_on` 支撑点云优先；缺少语义关系时只接受当前 scene identity 的 depth 和每实体 mask，lineage、frame、尺寸及稀疏证据错误均 fail closed。(local)
- [Sense] [Fix] [Completed] `grounding.py:L25-L40,L663-L751` preserves explicit `on/is_on` support clouds as the preferred source; when absent, it accepts only depth and per-entity masks from the current scene identity and fails closed on lineage, frame, shape, or sparse-evidence errors.(local)
- [sense] [fix] [完成] `persistent_host.py:L499-L501,L558-L562` 将 perception profile 的 depth scale 传递至 `persistent_deployment.py:L151-L193` 和 Grounding，统一 perception/planning 单位。(local)
- [Sense] [Fix] [Completed] `persistent_host.py:L499-L501,L558-L562` passes the perception profile depth scale through `persistent_deployment.py:L151-L193` into Grounding, keeping perception and planning units aligned.(local)
- [eval] [test] [完成] `test_observed_support.py:L29-L73`、`test_grounding.py:L965-L993`、deployment/host 测试覆盖反投影、mask 排除、provenance、fail-closed 和配置传递；adapter 全套 `708 passed, 1 skipped`，AgentLoop 聚焦 `8 passed`。(local)
- [Eval] [Test] [Completed] Support and Grounding tests cover projection, mask exclusion, provenance, fail-closed behavior, and configuration propagation; the full adapter suite passed `708` with `1` skipped, and focused AgentLoop tests passed `8`.(local)

### 关键 Diff / Key Diff
```diff
- if not refs:
-     return None
+ if not refs:
+     return self._observed_support_from_depth(binding, understanding)
...
+ depth scale comes from the perception profile
+ depth is projected through the bound calibration outside current masks
+ estimated support records depth and mask artifact refs
```

### 验证 / Verification
- Robotwin adapter: `708 passed, 1 skipped`。
- AgentLoop: `8 passed, 67 deselected`。
- `compileall` and `git diff --check` passed.

### Git 提交
- Commit: `246a6c3`
- Branch: `feature/planning-loop`

## v11.10.2 (2026-09-28 19:30) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/loop.py:L133-L146,L840-L924` 对 task-scoped task_creation/discovery/planning_execution 的空 `finish_reason=stop` 响应执行一次有界重试，只在无内容且无 Tool call 时生效；不重放已返回的 Tool call、Action 或 node turn。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/loop.py:L133-L146,L840-L924` retries an empty `finish_reason=stop` response once in task-scoped task_creation/discovery/planning_execution, only when there is no content or Tool call; returned Tool calls, Actions, and node turns are never replayed.(local)
- [eval] [test] [完成] `tests/test_agent_foundation.py:L88-L124` 覆盖空响应重试与非空 stop 不重试；`8 passed`，compileall 和 diff check 通过。(local)
- [Eval] [Test] [Completed] `tests/test_agent_foundation.py:L88-L124` covers retrying empty responses and not retrying non-empty stops; `8 passed`, with compileall and diff check passing.(local)

### 关键 Diff / Key Diff
```diff
- for model_attempt in range(2 if retry_timeout else 1):
+ retry_empty = self._retry_empty_model_response(...)
+ for model_attempt in range(2 if (retry_timeout or retry_empty) else 1):
...
+ if empty stop response has no tool calls or content:
+     retry the identical model request once
```

### Git 提交
- Commit: `23dd15e`
- Branch: `feature/planning-loop`

## v11.10.1 (2026-09-28 17:03) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/prompt_context.py:L1232-L1240` 将 `replan` 纳入 16,000 token 早期压缩，保留 Coordinator task projection，避免恢复 turn 在 `forge_task_begin_revision` 前 provider timeout。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/prompt_context.py:L1232-L1240` includes `replan` in the 16,000-token early compaction while retaining the Coordinator task projection, preventing provider timeout before `forge_task_begin_revision`.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L1051-L1095` 新增 replan 回归；聚焦测试 `121 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L1051-L1095` adds replan regression; focused tests passed `121`, with `compileall` and `git diff --check` passing.(local)

## v11.10.0 (2026-09-28 16:28) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/long_horizon.py:L16-L22,L197-L216,L232-L250,L346-L366` 捕获 stale scene context 并通过 Coordinator 持久化 `awaiting_replan`，不重发已成功 Action；重复恢复请求幂等，持久化失败才返回 blocked。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/long_horizon.py:L16-L22,L197-L216,L232-L250,L346-L366` catches stale scene context and persists `awaiting_replan` through the Coordinator without replaying successful Actions; repeated recovery is idempotent and persistence failure remains blocked.(local)
- [eval] [test] [完成] `tests/test_long_horizon_controller.py:L10-L14,L126-L156` 增加 stale-to-replan 回归；相关套件 `192 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_long_horizon_controller.py:L10-L14,L126-L156` adds stale-to-replan regression coverage; related suites passed `192`, with `compileall` and `git diff --check` passing.(local)

### 失败场景依据 / Failure scenario
`object.acquire` terminal succeeded 后推进 scene revision，旧 continuation 携带旧 discovery evidence 被正确拒绝；控制器此前只返回 blocked，任务保持 executing，下一 turn 无法看到 `forge_task_begin_revision`。/ After terminal-successful `object.acquire` advanced the scene revision, the old continuation correctly failed stale-evidence validation; the controller previously returned only blocked, leaving the task executing and hiding `forge_task_begin_revision` from the next turn.

### 关键 Diff / Key diff
~~~diff
+ except StaleNodeContextError as exc:
+     return self._request_replan(task_id, str(exc))
+ self.coordinator.request_replan(task_id, reason=f"stale_node_context:{reason.strip()}")
~~~

## v11.9.19 (2026-09-28 23:00) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/tools/forge_task.py:L430-L477` continuation 物化前拒绝刷新 Query 携带旧 scene evidence；`PhyAgentOS/agent/prompt_context.py:L1020-L1028` 明确 world-changing Action 后只能通过 dependency 等待 fresh Query。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/tools/forge_task.py:L430-L477` rejects stale evidence on refresh Queries before continuation materialization; `PhyAgentOS/agent/prompt_context.py:L1020-L1028` requires dependencies and fresh Queries after world-changing Actions.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L520-L527` continuation guidance 回归；聚焦 Agent foundation/prompt/timeout `120 passed`。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L520-L527` adds continuation guidance regression; focused Agent foundation/prompt/timeout suite passed `120`.(local)

## v11.9.18 (2026-09-28 22:00) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/planning_loop.py:L191-L198` 允许 continuation 显式授权的 discovery refs 进入 consumer context，同时保留 scene freshness 校验；`PhyAgentOS/forge/task.py:L1705-L1712` 继承并去重 refs。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/planning_loop.py:L191-L198` admits explicitly authorized continuation discovery refs into consumer context while retaining scene freshness checks; `PhyAgentOS/forge/task.py:L1705-L1712` inherits and deduplicates refs.(local)
- [eval] [test] [完成] 聚焦 Agent foundation/prompt/timeout `119 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] Focused Agent foundation/prompt/timeout tests passed `119`, with `compileall` and `git diff --check` passing.(local)

## v11.9.17 (2026-09-28 19:00) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/tools/forge_tool_api.py:L102-L117,L223-L229,L702-L755` 将 `scene.bind` 错误字段、缺失选择和歧义实体转换为结构化可恢复错误；`PhyAgentOS/agent/prompt_context.py:L394-L437,L802-L804` 投影候选实体及来源。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/tools/forge_tool_api.py:L102-L117,L223-L229,L702-L755` turns `scene.bind` alias, missing-selection, and ambiguous-entity errors into structured recoverable responses; `PhyAgentOS/agent/prompt_context.py:L394-L437,L802-L804` projects candidate entities and provenance.(local)
- [eval] [test] [完成] alias/ambiguity regressions added; focused Agent foundation/prompt/timeout suite passed `119`。(local)
- [Eval] [Test] [Completed] Added alias and ambiguity regressions; focused Agent foundation/prompt/timeout suite passed `119`.(local)

## v11.9.12 (2026-09-28 10:00) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/prompt_context.py:L1051-L1185` 为 discovery 请求增加默认 16,000 token 压缩阈值；压缩重复历史 Forge 查询和模型叙述，同时保留 Coordinator 当前 AgentTask projection 与最近完整 turn。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/prompt_context.py:L1051-L1185` adds a default 16,000-token discovery compaction threshold; repeated historical Forge results and narration are compacted while the Coordinator's current AgentTask projection and recent complete turns remain.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L901-L955` 增加 discovery 回归，确认全局阈值触发前已压缩历史结果且保留当前 observation/task projection。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L901-L955` adds a discovery regression proving historical results compact before the global threshold while the current observation and task projection remain.(local)
- [eval] [test] [完成] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_prompt_context.py tests/test_agent_foundation.py tests/test_turn_timeouts.py`：`114 passed`；`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] Focused prompt-context, agent-foundation, and timeout tests passed `114`; `compileall` and `git diff --check` passed.(local)

### 失败场景依据 / Failure scenario
第二次 GraspNet RGB 验收在 discovery 第 12 次请求约 31k prompt tokens 时达到 240 秒 provider timeout，重试请求仍 timeout；全局 258k 压缩阈值未触发，导致历史 discovery 交互持续进入后续请求。/ The second GraspNet RGB acceptance reached a 240-second provider timeout on discovery iteration 12 at roughly 31k prompt tokens and timed out again on retry; the global 258k compaction threshold never activated, so historical discovery interaction kept flowing into later requests.

### 文件变更详情 / Exact changes
- `PhyAgentOS/agent/prompt_context.py`
- `tests/test_prompt_context.py`

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L1051-L1067,L1121-L1147,L1149-L1172`
**修改前 / Before:** discovery 使用与普通阶段相同的全局 `compaction_trigger_tokens`，在约 31k token 的历史 discovery 请求中不会提前压缩。

**修改后 / After:** `AgentPromptContextManager` 提供 `DEFAULT_DISCOVERY_COMPACTION_TRIGGER_TOKENS = 16_000` 和可配置构造参数；`build()` 按 discovery phase 取更低阈值，触发既有 aggressive Forge 结果压缩，并重新注入当前 Coordinator projection。

**修改说明 / Rationale:** 失败场景是 discovery 查询结果逐轮累积，Provider 在动作前 timeout；持久化 task projection 已是权威事实来源，因此可以压缩重复 transcript 而不丢失当前绑定事实。/ The failure was discovery transcript growth causing provider timeout before actions; the persisted task projection is authoritative, so repeated transcript can be compacted without losing current bindings.

#### [新增 / Added] `tests/test_prompt_context.py:L901-L955`
**新增代码 / Added:** 构造四轮大型 `forge_tool_query` 历史，断言 phase 为 discovery、发生压缩、旧 debug 消失而 `observation://current` 与 `read_only_projection_from_AgentTaskCoordinator` 保留。/ Builds four large historical `forge_tool_query` turns and asserts discovery compaction, removal of old debug text, and preservation of the current observation and Coordinator projection.

## v11.9.13 (2026-09-28 11:30) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/prompt_context.py:L261-L345,L1157-L1158` 让已创建 AgentTask 的 discovery 阶段隐藏重复 `activate_skill`/`forge_task_get`；在重复读取 ToolSpec 达到有界次数后隐藏 `forge_tool_context`，保留 `forge_tool_query` 作为唯一前进入口。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/prompt_context.py:L261-L345,L1157-L1158` hides repeated `activate_skill`/`forge_task_get` after AgentTask creation; after bounded repeated ToolSpec reads it hides `forge_tool_context` while retaining `forge_tool_query` as the progress path.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L363-L460` 增加 reassembly 可见性回归；`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_prompt_context.py tests/test_agent_foundation.py tests/test_turn_timeouts.py`：`115 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L363-L460` adds the reassembly visibility regression; focused prompt-context, agent-foundation, and timeout tests passed `115`, with `compileall` and `git diff --check` passing.(local)

### 失败场景依据 / Failure scenario
`rgb-graspnet-v11-9-12-r1-20260928` 创建 `task_109513a10fef4d8e` 后 40 次迭代调用了 14 次 `activate_skill`、18 次 `forge_tool_context`、7 次 `forge_task_get`，但没有一次 `forge_tool_query`；任务保持 executing、无 Gateway Action。/ After creating `task_109513a10fef4d8e`, `rgb-graspnet-v11-9-12-r1-20260928` spent all 40 iterations on 14 `activate_skill`, 18 `forge_tool_context`, and 7 `forge_task_get` calls with zero `forge_tool_query` calls; the task stayed executing and no Gateway Action occurred.

### 文件变更详情 / Exact changes
- `PhyAgentOS/agent/prompt_context.py`
- `tests/test_prompt_context.py`
- `PhyAgentOS/agent/loop.py` 未修改；AgentLoop 继续使用 PromptContextManager 的 phase-scoped visible tool projection。/ unchanged; AgentLoop continues to consume the phase-scoped visible tool projection from PromptContextManager.

#### [新增 / Added] `PhyAgentOS/agent/prompt_context.py:L261-L275`
**新增代码 / Added:** `_tool_call_names` 从当前 turn 读取已请求的 tool 名称，供 discovery 可见性边界判断重组次数。/ Reads tool names requested in the current turn for the discovery visibility boundary.

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L278-L345,L1157-L1158`
**修改前 / Before:** task-scoped discovery 保持 `activate_skill`、`forge_task_get` 和 `forge_tool_context` 一直可见，模型可以反复重建控制面上下文并耗尽迭代。

**修改后 / After:** non-creation task turns remove `activate_skill`; graph-less discovery removes `forge_task_get`; after `max(5, 2 * missing_preplan_queries)` context reads, `forge_tool_context` is hidden and `forge_tool_query` remains visible.

**修改说明 / Rationale:** 该边界只改变模型可见性，不执行 Query、不生成参数、不授权动作；Coordinator 仍验证所有 task-bound Query、opaque refs 和 PlanGraph admission。/ This boundary changes only model visibility; it does not execute Queries, generate arguments, or authorize Actions, and Coordinator still validates task-bound Queries, opaque refs, and PlanGraph admission.

#### [新增 / Added] `tests/test_prompt_context.py:L425-L460`
**新增代码 / Added:** 模拟任务创建后一次 Skill/task 组装和十次 context 读取，确认 reassembly 工具隐藏而 `forge_tool_query` 保留。/ Simulates post-creation Skill/task assembly and ten context reads, proving reassembly tools are hidden while `forge_tool_query` remains.

## v11.9.14 (2026-09-28 12:10) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/prompt_context.py:L290-L296` 将 `activate_skill` 从 task-scoped generic 工具中移除，而在 `task is None` 的 task_creation 阶段保留；避免重复激活同时保留初始 Skill activation。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/prompt_context.py:L290-L296` removes `activate_skill` only from task-scoped generic tools while retaining it for task creation; this prevents repeated activation without blocking initial Skill activation.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L352-L360` 增加 task_creation 必须暴露 `activate_skill` 的断言；聚焦回归 `115 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L352-L360` asserts `activate_skill` remains visible during task creation; focused regression passed `115`, with `compileall` and `git diff --check` passing.(local)

### 失败场景依据 / Failure scenario
`rgb-graspnet-v11-9-13-r2-20260928` 在第一个模型请求后无法看到 `activate_skill`，因此 fail-closed 停止；没有创建 AgentTask、没有 Gateway Query/Action。/ After the first model request, `rgb-graspnet-v11-9-13-r2-20260928` could not see `activate_skill` and stopped fail-closed; no AgentTask, Gateway Query, or Action was created.

### 文件变更详情 / Exact changes
- `PhyAgentOS/agent/prompt_context.py`
- `tests/test_prompt_context.py`

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L290-L296`
**修改前 / Before:** `activate_skill` was removed while building the generic set for every phase, including task creation.

**修改后 / After:** the task-creation branch returns before the task-scoped `generic.discard("activate_skill")`, so initial Skill activation remains model-visible; only existing-task phases hide it.

**修改说明 / Rationale:** the failed acceptance stopped before AgentTask creation because activation was not visible; no Runtime or Action state was changed. / The failed acceptance stopped before AgentTask creation because activation was hidden; no Runtime or Action state changed.

#### [修改 / Modified] `tests/test_prompt_context.py:L352-L360`
**修改后 / After:** task-creation visibility now explicitly requires `activate_skill`, while discovery continues to expose `forge_tool_query` and no execution Action tools.

## v11.9.15 (2026-09-28 16:20) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/prompt_context.py:L624-L638` 在缺少 `scene.bind` 的 discovery projection 中明确消费者字段：顶层 `entity_refs`，以及来自同一 observe record 的 `observation_ref`、`scene_revision`、`calibration_ref` `argument_sources`；禁止使用 `entities` 别名。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/prompt_context.py:L624-L638` explicitly documents the `scene.bind` consumer fields in discovery projection: top-level `entity_refs` plus `observation_ref`, `scene_revision`, and `calibration_ref` `argument_sources` from the same observe record; the `entities` alias is prohibited.(local)
- [eval] [test] [完成] `tests/test_prompt_context.py:L463-L485` 增加 projection 参数传递回归；聚焦套件 `116 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_prompt_context.py:L463-L485` adds the projection parameter-passing regression; focused suite passed `116`, with `compileall` and `git diff --check` passing.(local)

### 失败场景依据 / Failure scenario
Recovery session `cli:rgb-graspnet-v11-9-12-r1-20260928` had successful current observe/understand/capabilities records, but its `scene.bind` payload used `entities` and only mapped calibration/scene fields incompletely; Runtime returned `grounding_unavailable` and no binding, GraspNet, or Action was admitted. / The recovery session had valid current perception facts, but the consumer payload used the wrong field name and incomplete identity mapping, so Runtime correctly failed closed before GraspNet or Action.

### 文件变更详情 / Exact changes
- `PhyAgentOS/agent/prompt_context.py`
- `tests/test_prompt_context.py`

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L624-L638`
**修改前 / Before:** the discovery next-step text only said to run missing Queries from live ToolSpecs and did not call out the `scene.bind` schema's exact field names or source mapping.

**修改后 / After:** when `scene.bind` is missing, the projection states to use top-level `entity_refs` (not `entities`) and to source all three identity fields from the same current observation record.

**修改说明 / Rationale:** the live Runtime rejected valid perception records because the Agent sent the wrong consumer field and incomplete identity binding; this is a prompt-level ownership correction, not a Runtime bypass. / The live Runtime rejected valid perception records because the Agent sent the wrong consumer field and incomplete identity binding; this is a prompt-level ownership correction, not a Runtime bypass.

#### [新增 / Added] `tests/test_prompt_context.py:L463-L485`
**新增代码 / Added:** binds a fixture `scene.bind` prerequisite and asserts the projection contains the exact consumer field and identity-source guidance. / Binds a fixture prerequisite and asserts exact consumer field and identity-source guidance.

## v11.9.16 (2026-09-28 18:00) - codex

### 实际修改 / Implemented changes
- [agent] [fix] [完成] `PhyAgentOS/agent/tools/forge_tool_api.py:L35-L57,L150-L170,L651-L688` 将 `scene.bind` 加入 observation-bound Query 归一化；Coordinator 自动复制当前成功 observe 的 `observation_ref`、`scene_revision`、`calibration_ref`，模型只提供 `entity_refs`。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/tools/forge_tool_api.py:L35-L57,L150-L170,L651-L688` adds `scene.bind` to observation-bound Query normalization; Coordinator copies `observation_ref`, `scene_revision`, and `calibration_ref` from the current successful observation while the model supplies only `entity_refs`.(local)
- [eval] [test] [完成] `tests/test_agent_foundation.py:L1403-L1425` 增加归一化回归；聚焦套件 `117 passed`，`compileall` 与 `git diff --check` 通过。(local)
- [Eval] [Test] [Completed] `tests/test_agent_foundation.py:L1403-L1425` adds normalization coverage; focused suite passed `117`, with `compileall` and `git diff --check` passing.(local)

### 失败场景依据 / Failure scenario
The recovery task repeatedly reached `scene.bind`, but Coordinator rejected payloads with `arguments cannot be both literal and sourced` or `argument source is not visible to this consumer`; no binding or Action was created. The consumer identity is already determined by the current task's successful observation, so requiring the model to resend it creates an avoidable merge failure.

### 文件变更详情 / Exact changes
- `PhyAgentOS/agent/tools/forge_tool_api.py`
- `tests/test_agent_foundation.py`

#### [修改 / Modified] `PhyAgentOS/agent/tools/forge_tool_api.py:L35-L57,L150-L170,L651-L688`
**修改前 / Before:** `scene.bind` was not part of the observation-bound query path, so the model had to resend identity fields and could submit the same field both literally and through `argument_sources`.

**修改后 / After:** `scene.bind` identity fields are coordinator-projected from the latest successful observation; literal `entity_refs` remain intact and any duplicate identity source is ignored by the bound-field filter.

**修改说明 / Rationale:** the concrete failure was a local `arguments cannot be both literal and sourced` rejection followed by Runtime grounding failures before any binding; normalization removes only duplicate transport assembly and preserves all Runtime validation. / The concrete failure was a local merge rejection followed by Runtime grounding failures before binding; normalization removes duplicate transport assembly while preserving Runtime validation.

#### [新增 / Added] `tests/test_agent_foundation.py:L1403-L1425`
**新增代码 / Added:** verifies `scene.bind` receives the exact current observation identity while retaining the selected entity list. / Verifies exact current observation identity projection while retaining selected entities.

## v11.8.1 (2026-09-25 22:19) - codex

### 预期修改 / Planned changes
- [env] [fix] [完成] 最终包一致性回归发现 skill.yaml=2.7.13 与 pyproject.toml=2.7.12 不匹配。统一下一 Skill 包为 2.7.14，保留 Node 0.8.0 内容；当前第四轮绑定 2.7.13 正在感知，不中途替换运行中 Runtime。(local)
- [Env] [Fix] [Completed] Final packaging regression found manifest 2.7.13 versus Python package 2.7.12. Align the next Skill bundle to 2.7.14 and retain Node 0.8.0 content; do not replace the live trial4 Runtime mid-task. (local)
- [eval] [exp] [完成] 修复版本断言并重跑完整回归；算法修改前述 1069 通过，打包后为 1068 通过、1 失败、1 跳过，失败仅为包版本不一致。记录 source commit 6faf4c6 与后续部署来源。(local)
- [Eval] [Exp] [Completed] Rerun integrated tests after metadata repair; initial algorithm suite passed 1069, while the final packaging pass had 1068 passed, one version-mismatch failure and one skip. Record source commit 6faf4c6 and deployment provenance. (local)

### 验证 / Validation
- [eval] [exp] 完整测试恢复为 1069 passed, 1 skipped；当前运行没有部署中断。(local)
- [Eval] [Exp] Integrated regression restored to 1069 passed, 1 skipped; the active run was not interrupted. (local)

### 文件变更详情 / Exact changes
#### [修改 / Modified] examples/forge-skills/pick-place-workflow/skill.yaml L2-L4
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index f0c819c..1dfef5e 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -2,3 +2,3 @@ manifest_version: 2
 name: pick-place-workflow
-version: "2.7.13"
+version: "2.7.14"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/pyproject.toml L2-L4
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index 01134b6..16bfc67 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -2,3 +2,3 @@
 name = "paos-pick-place-workflow"
-version = "2.7.12"
+version = "2.7.14"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py L268-L270
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
index 7895957..611bb51 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
@@ -268,3 +268,3 @@ def test_bundle_and_package_versions_match_the_feature_revision():

-    assert bundle_manifest["version"] == "2.7.13"
+    assert bundle_manifest["version"] == "2.7.14"
     assert tomllib.loads(package_text)["project"]["version"] == bundle_manifest["version"]
~~~

### Git 提交 / Git Commit
- Algorithm source: 6faf4c6; pushed to origin/feature/planning-loop.
- Current trial4 uses installed Skill 2.7.13 / Node 0.8.0; next installation uses metadata-aligned Skill 2.7.14.

## v11.8.0 (2026-09-25 22:04) - codex

### 预期修改 / Planned changes
- [policy] [fix] [完成：实现与回归；真实验收进行中] 修复 manipulation.prepare 已校验请求的失败响应丢失场景、观察和候选集身份；第三轮响应 scene_revision=unknown 导致可信上下文排除失败记录，恢复节点 required_evidence 永不 ready。保持 Coordinator/AgentLoop 现有权限和恢复路径。(local)
- [Policy] [Fix] [Implemented and regression-tested; live acceptance active] Preserve validated scene, observation and candidate-set identity on preparation provider failures; trial 3 emitted unknown scene identity, so trusted context excluded the failure needed by its recovery node. Retain Coordinator ownership and existing admission. (local)
- [model] [exp] [完成：实现与回归；真实验收进行中] 基于第三轮原始点云与 Panda 原生碰撞网格，测量 GraspNet 候选分布、真实支撑穿透与可用候选覆盖；仅在实测支持时调整 provider 的候选选择，24 个真实候选进入 Adapter 后再筛选至最多 10 个，禁止模板或放宽碰撞。(local)
- [Model] [Exp] [Implemented and regression-tested; live acceptance active] Measure GraspNet proposal coverage using trial 3 observed cloud and native Panda meshes; change provider selection only if measured evidence supports it, preserving 24 real proposals before Adapter screening to at most 10, with no templates or relaxed collision checks. (local)
- [eval] [exp] [完成：实现与回归；真实验收进行中] 增加失败响应至恢复 ready 的回归，完成七维审查，按新版本部署后继续独立 RGB 验收；本轮此前三次均未完成任何动作，不计成功。(local)
- [Eval] [Exp] [Implemented and regression-tested; live acceptance active] Add unavailable-response-to-recovery-readiness regressions, complete seven-dimension review and redeploy for independent RGB acceptance; none of the first three trials completed an Action. (local)

### 验证 / Validation
- [eval] [exp] 77 项失败响应/上下文回归通过；完整 Adapter/Skill/context 测试 1069 passed, 1 skipped。原生 URDF 无运动测量证实几何拒绝；1024 原生候选中 402 支撑有效、57 接触有效，按分数前 24 全拒绝。新配置 24→10 中保留 1 个接触有效候选；IK 与全路线仍需 Runtime 验证。(local)
- [Eval] [Exp] 77 focused and 1069 integrated tests passed, with one existing Pillow-related skip. Native no-step geometry reproduces rejection; 402/1024 support-valid and 57 contact-valid versus zero in score-top-24. New 24-to-10 sampling retains one contact-valid pose; IK/full-route and final task outcome remain to verify. (local)
- Command: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests tests/test_planning_context.py -q
- Review: docs/forge/IMPLEMENTATION_REVIEW_V11_8_0.md
- Acceptance root: /home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260925T211115/run4

### 文件变更详情 / Exact changes
#### [修改 / Modified] PhyAgentOS/forge/capability_runtime/manipulation_prepare.py L452-L467, L496-L531, L534-L540
~~~diff
diff --git a/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py b/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
index 24195f5..cb3c82f 100644
--- a/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
+++ b/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
@@ -452,4 +452,16 @@ class ManipulationPreparationEndpoint:
                 observation_ref=observation_ref,
             )
+        # A failed Query still belongs to its validated request scene. Dropping
+        # that identity makes recovery evidence look stale to Coordinator.
+        def bound_error(code: str, message: str) -> dict[str, Any]:
+            return {
+                **_error(code, message, observation_ref=observation_ref),
+                "preparation_ref": preparation_ref,
+                "candidate_set_ref": arguments["candidate_set_ref"],
+                "scene_revision": arguments["scene_revision"],
+                "frame": {"frame_id": arguments["frame_id"], "unit": "m"},
+                "calibration_ref": arguments["calibration_ref"],
+            }
+
         if arguments["freshness_ms"] > arguments["max_age_ms"]:
             return {
@@ -484,42 +496,36 @@ class ManipulationPreparationEndpoint:
             snapshot = self.provider.prepare(deepcopy(arguments))
         except PreparationProviderError as exc:
-            return _error(exc.code, str(exc), observation_ref=observation_ref)
+            return bound_error(exc.code, str(exc))
         except TimeoutError:
-            return _error(
+            return bound_error(
                 "preparation_timeout",
                 "manipulation preparation exceeded its total time budget",
-                observation_ref=observation_ref,
             )
         except Exception:
             # Provider failures are unavailable, never an implicit Gateway 500 or success.
-            return _error(
+            return bound_error(
                 "preparation_provider_error",
                 "manipulation preparation provider failed",
-                observation_ref=observation_ref,
             )
         if snapshot is None:
-            return _error(
+            return bound_error(
                 "preparation_unavailable",
                 "manipulation preparation provider is unavailable",
-                observation_ref=observation_ref,
             )
         snapshot = normalize_snapshot(snapshot)
         if snapshot is None:
-            return _error(
+            return bound_error(
                 "invalid_snapshot",
                 "manipulation preparation provider returned an invalid snapshot",
-                observation_ref=observation_ref,
             )
         if not isinstance(snapshot.provider_available, bool):
-            return _error(
+            return bound_error(
                 "invalid_snapshot",
                 "manipulation preparation provider returned an invalid availability flag",
-                observation_ref=observation_ref,
             )
         if not snapshot.provider_available:
-            return _error(
+            return bound_error(
                 "preparation_unavailable",
                 "manipulation preparation provider is unavailable",
-                observation_ref=observation_ref,
             )
         candidate_entities = {
@@ -528,8 +534,7 @@ class ManipulationPreparationEndpoint:
         snapshot_error = validate_snapshot(snapshot, candidate_entities=candidate_entities)
         if snapshot_error:
-            return _error(
+            return bound_error(
                 snapshot_error,
                 "manipulation preparation result failed contract validation",
-                observation_ref=observation_ref,
             )
         prepared = [dict(item) for item in snapshot.prepared_candidates]
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/README.md L267-L279
~~~diff
diff --git a/examples/forge-adapters/robotwin20/README.md b/examples/forge-adapters/robotwin20/README.md
index ca88101..035d36a 100644
--- a/examples/forge-adapters/robotwin20/README.md
+++ b/examples/forge-adapters/robotwin20/README.md
@@ -267,5 +267,13 @@ point-cloud path and returns 4x4 matrices plus scores; the adapter validates the
 homogeneous transform, converts it to a normalized quaternion and approach
 vector, applies deterministic confidence-ordered SE(3) NMS, and projects the
-candidate funnel. GraspGen/Torch/checkpoint settings remain in the external
+candidate funnel. The shipped GraspNet profile samples 24 unchanged native
+poses with orientation coverage (native X approach and symmetric Y closing),
+starting from the highest score and maximizing distance from selected directions.
+NMS still removes duplicates using native scores; provider order then retains
+at most 10 survivors. Native scores and geometry are never rewritten. This avoids
+spending the entire proposal budget on one colliding orientation family. It is
+advisory sampling only: manipulation.prepare still owns contact/IK/complete-route
+qualification. Set worker --sampling-policy=score and selection_order=score for
+the original score-only policy. GraspGen/Torch/checkpoint settings remain in the external
 worker profile. GraspGen remains available only through the explicit
 `graspgen.yaml` and `persistent-materializer-graspgen.yaml` closure; its depth
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml L5-L10, L31-L34
~~~diff
diff --git a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
index 6db4ffb..fa0461e 100644
--- a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
+++ b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
@@ -5,4 +5,6 @@ artifact_root: ${ROBOTWIN20_ARTIFACT_ROOT}
 max_candidates: 10
 sample_count: 24
+# Preserve native pose coverage; score-only truncation loses feasible families.
+selection_order: provider
 score_threshold: 0.02
 apply_nms: true
@@ -29,2 +31,4 @@ worker:
     - --device
     - ${GRASPNET_DEVICE}
+    - --sampling-policy
+    - orientation_diverse
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/graspnet_worker.py L24-L55, L156-L162, L173-L177
~~~diff
diff --git a/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py b/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
index 2a23aad..4494f74 100644
--- a/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
+++ b/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
@@ -24,4 +24,32 @@ _MODEL: tuple[Any, Any, Any] | None = None


+def _sample_candidates(candidates, limit, policy):
+    """Select unchanged native poses; diversity is advisory, never admission.
+
+    GraspNet decodes many spatial seeds with the same preferred orientation.
+    Score-only truncation can spend the entire budget on one colliding family.
+    Start with its best score, then cover approach/closing directions. Parallel
+    jaw closing-axis sign is symmetric; ties keep native score order.
+    """
+    import numpy as np
+
+    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
+    if policy == "score" or not ranked:
+        return ranked[:limit]
+    if policy != "orientation_diverse":
+        raise WorkerUnavailableError("unsupported GraspNet sampling policy")
+    rotations = np.asarray([item["matrix"] for item in ranked])[:, :3, :3]
+    selected = [0]
+    nearest = np.full(len(ranked), np.inf)
+    while len(selected) < min(limit, len(ranked)):
+        index = selected[-1]
+        distances = (1 - np.clip(rotations[:, :, 0] @ rotations[index, :, 0], -1, 1)
+                     + 1 - np.abs(np.clip(rotations[:, :, 1] @ rotations[index, :, 1], -1, 1)))
+        nearest = np.minimum(nearest, distances)
+        nearest[selected] = -1
+        selected.append(int(np.argmax(nearest)))
+    return [ranked[index] for index in selected]
+
+
 def _load() -> None:
     global _MODEL
@@ -128,6 +156,7 @@ def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
         )
     canonical_count = len(candidates)
-    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
-    candidates = candidates[:max_candidates]
+    candidates = _sample_candidates(
+        candidates, max_candidates, getattr(_OPTIONS, "sampling_policy", "score")
+    )[:max_candidates]
     return {
         "request_id": request["request_id"],
@@ -144,4 +173,5 @@ def _parser() -> argparse.ArgumentParser:
     parser.add_argument("--source-root")
     parser.add_argument("--device", default="cuda:0")
+    parser.add_argument("--sampling-policy", choices=("score", "orientation_diverse"), default="score")
     return parser

~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py L85-L89
~~~diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
index ff162dd..27a026e 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
@@ -85,4 +85,5 @@ def build_grasp_provider(
             nms_closing_angle_deg=profile["nms_closing_angle_deg"],
             apply_model_collision=profile["apply_model_collision"],
+            selection_order=profile.get("selection_order", "score"),
             model_variant=model_variant,
         )
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py L86-L90, L113-L118, L133-L137, L180-L187
~~~diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
index 5175861..3d2b57f 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
@@ -86,4 +86,5 @@ class GraspProposalProvider:
         nms_closing_angle_deg: float = 10.0,
         apply_model_collision: bool = False,
+        selection_order: str = "score",
         provider_id: str = "graspgen",
         model_variant: str = "ptv3",
@@ -112,4 +113,6 @@ class GraspProposalProvider:
         if not isinstance(apply_nms, bool) or not isinstance(apply_model_collision, bool):
             raise TypeError("grasp filtering flags must be booleans")
+        if selection_order not in {"score", "provider"}:
+            raise ValueError("selection_order must be score or provider")
         if not isinstance(provider_id, str) or not provider_id or not provider_id.isidentifier():
             raise ValueError("provider_id must be a non-empty identifier")
@@ -130,4 +133,5 @@ class GraspProposalProvider:
         self.nms_closing_angle_deg = float(nms_closing_angle_deg)
         self.apply_model_collision = apply_model_collision
+        self.selection_order = selection_order
         self.provider_id = provider_id
         self.model_variant = model_variant
@@ -176,4 +180,8 @@ class GraspProposalProvider:
                     )
                 funnel["deduplicated"] += len(canonical)
+                if self.selection_order == "provider":
+                    # Keep provider sampling coverage after normal NMS. Scores
+                    # stay unchanged; only preparation can qualify a contact.
+                    canonical.sort(key=lambda item: item[2])
                 for matrix, score, index in canonical[: self.max_candidates]:
                     grasp_geometry = raw_candidates[index].get("grasp_geometry")
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py L94-L119
~~~diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
index 7e1a86a..967e75b 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
@@ -94,4 +94,26 @@ def test_graspgen_provider_maps_bound_geometry_to_neutral_candidates(tmp_path):
     assert worker.requests[0]["provider"] == "graspgen"
     assert worker.requests[0]["point_units"] == "m"
+
+
+def test_provider_sampling_order_survives_nms_and_ten_candidate_cap(tmp_path):
+    class SampledWorker(Worker):
+        def request(self, payload):
+            reply = super().request(payload)
+            reply["candidates"] = []
+            for index in range(24):
+                matrix = np.eye(4)
+                matrix[0, 3] = index * .01
+                reply["candidates"].append({"matrix": matrix.tolist(), "score": .1 + index * .03})
+            reply["funnel"] = {"decoded": 1024, "canonicalized": 1024, "deduplicated": 1024, "retained": 24}
+            return reply
+
+    worker = SampledWorker()
+    provider = GraspNetProposalProvider(worker, artifact_store=_store(tmp_path),
+        max_candidates=10, sample_count=24, apply_nms=True, selection_order="provider")
+    result = provider.propose(REQUEST)
+    assert worker.requests[0]["max_candidates"] == 24
+    assert result["funnel"] == {"decoded": 1024, "canonicalized": 24, "deduplicated": 24, "retained": 10}
+    assert [c["grasp_frame"]["position_m"][0] for c in result["candidates"]] == pytest.approx([i * .01 for i in range(10)])
+    assert [c["score"] for c in result["candidates"]] == pytest.approx([.1 + i * .03 for i in range(10)])
     assert worker.released is True

~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py L54-L82
~~~diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py b/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py
index 3fcf28f..edbd17a 100644
--- a/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py
+++ b/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py
@@ -54,2 +54,29 @@ def test_graspnet_ranks_before_limit_and_reports_full_threshold_funnel(tmp_path,
         "decoded": 5, "canonicalized": 4, "deduplicated": 4, "retained": 2,
     }
+
+
+def test_orientation_sampling_covers_native_poses_without_rewriting_scores_or_geometry():
+    module = _module("graspnet_worker")
+    candidates = []
+    for index in range(30):
+        matrix = np.eye(4)
+        matrix[0, 3] = index * .001
+        candidates.append({"matrix": matrix.tolist(), "score": 1 - index * .001})
+    matrix = np.diag([-1., -1., 1., 1.])
+    distinct = {"matrix": matrix.tolist(), "score": .2}
+    candidates.append(distinct)
+    sampled = module._sample_candidates(candidates, 24, "orientation_diverse")
+    assert len(sampled) == 24
+    assert sampled[0] is candidates[0]
+    assert sampled[1] is distinct
+    assert len({id(item) for item in sampled}) == 24
+    assert all(any(item is source for source in candidates) for item in sampled)
+    assert module._sample_candidates(candidates[:3], 24, "orientation_diverse") == candidates[:3]
+
+
+def test_sampling_treats_parallel_jaw_closing_sign_as_equivalent():
+    module = _module("graspnet_worker")
+    same = {"matrix": np.eye(4).tolist(), "score": .9}
+    mirrored = {"matrix": np.diag([1., -1., -1., 1.]).tolist(), "score": .8}
+    different = {"matrix": np.diag([-1., -1., 1., 1.]).tolist(), "score": .1}
+    assert module._sample_candidates([same, mirrored, different], 2, "orientation_diverse") == [same, different]
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/skill.yaml L1-L5, L240-L248
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index 63d7751..f0c819c 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,5 +1,5 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.12"
+version: "2.7.13"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
@@ -240,9 +240,9 @@ artifacts:
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.15-linux-x86_64
-      version: "0.7.15"
+      artifact_id: robotwin20_persistent_host-0.8.0-linux-x86_64
+      version: "0.8.0"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: d63e4cce65e037511bf2156db471e5b9ed1d117cac69816912070c5371d9a15a
+      sha256: 2d6970374e5f5541ac9e7080326788d32598e383173e92df9c872c6ca8642e5b
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py L267-L271
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
index 3bf5544..7895957 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
@@ -267,5 +267,5 @@ def test_bundle_and_package_versions_match_the_feature_revision():
     import tomllib

-    assert bundle_manifest["version"] == "2.7.12"
+    assert bundle_manifest["version"] == "2.7.13"
     assert tomllib.loads(package_text)["project"]["version"] == bundle_manifest["version"]

~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py L148-L203
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py b/examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py
index eb98018..200278e 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py
@@ -148,4 +148,56 @@ class TimeoutProvider:


+@pytest.mark.parametrize("failure", ["declared", "timeout", "exception", "none", "invalid", "unavailable"])
+def test_provider_failure_preserves_scene_and_unlocks_recovery_observation(failure):
+    from types import SimpleNamespace
+
+    from PhyAgentOS.agent.planning_context import context_from_task
+    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError
+    from PhyAgentOS.planning import PlanGraph, PlanNode, derive_ready_nodes, plan_graph_digest
+
+    class FailingProvider:
+        def prepare(self, request):
+            if failure == "declared":
+                raise PreparationProviderError("no_qualified_contacts", "All contacts rejected")
+            if failure == "timeout":
+                raise TimeoutError("budget")
+            if failure == "exception":
+                raise RuntimeError("private backend detail")
+            if failure == "none":
+                return None
+            if failure == "invalid":
+                return {"bad_snapshot": True}
+            return PreparationSnapshot(provider_available=False)
+
+    arguments = request_payload()
+    result = ManipulationPreparationEndpoint(FailingProvider()).invoke(arguments)
+    assert result["status"] in {"invalid", "unavailable"}
+    for name in ("observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref"):
+        assert result[name] == arguments[name]
+    assert result["prepared_candidates"] == []
+    assert result["motion_authorized"] is False
+    assert set(result["checks"].values()) == {"unknown"}
+    observe = SimpleNamespace(terminal=True, tool_id="scene.observe", semantics="query",
+        status="succeeded", arguments={}, response={"scene_revision": "scene-7"},
+        evidence_refs=("tool:observe",))
+    prepare = SimpleNamespace(terminal=True, tool_id="manipulation.prepare", semantics="query",
+        status="succeeded", arguments=arguments, response={"ok": True, "data": result},
+        evidence_refs=("tool:prepare-failed",))
+    task = SimpleNamespace(execution_records=[observe, prepare], tool_bindings=(),
+        primary_skill_binding=None, active_revision=SimpleNamespace(node_settlements=(),
+        discovery_evidence_refs=()))
+    context = context_from_task(task, allow_refresh=True)
+    node = PlanNode(node_id="refresh-observation", obligation_id="refresh",
+        capability="scene.observe", required_evidence=("tool:prepare-failed",))
+    payload = dict(schema_version="paos-plan-graph/v1", task_id="task-recovery",
+        revision_id="revision-recovery", graph_digest="0" * 64,
+        planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64,
+        nodes=[node.model_dump(mode="json")])
+    payload["graph_digest"] = plan_graph_digest(payload)
+    graph = PlanGraph.model_validate(payload)
+    assert context.scene_revision == "scene-7"
+    assert derive_ready_nodes(graph, {}, context.evidence_refs, {}) == ("refresh-observation",)
+
+
 def _observation_stub():
     return type("Observation", (), {"observe": lambda self, sensor_ref: None})()
~~~

#### [新增 / Added] docs/forge/IMPLEMENTATION_REVIEW_V11_8_0.md L1-L58
~~~diff
+# v11.8.0 GraspNet coverage and recovery evidence review
+
+Date: 2026-09-25. Acceptance remains active.
+
+## Findings and dispositions
+
+1. **Blocker: preparation failure loses the request scene.** The public endpoint
+   returned scene_revision=unknown after a validated request failed in its provider.
+   Task task_803ae1a6cae1449d then built a recovery observation depending on the
+   failed prepare record. The trusted scene projector correctly excluded the
+   conflicting response, leaving no ready node. Preserve validated request identity
+   in all provider-failure responses. No successful checks or motion authority are
+   fabricated. Six failure variants now test endpoint-to-context-to-ready recovery.
+2. **Major: early score truncation discards useful orientation families.** Offline
+   analysis uses the exact run3 observed red cloud and unmodified native Panda
+   meshes. A fresh GraspNet inference decoded 1024 real poses: 402 pass support
+   clearance and 57 pass observed swept contact checks. All score-top-24 collide;
+   the first contact-valid native pose ranks 389. These are no-motion diagnostics,
+   not IK/route success, and inference is stochastic.
+   GraspNet now offers orientation-diverse budget sampling, selected in its profile:
+   keep the highest native score, then maximize approach/closing angular coverage.
+   All matrices, scores and dimensions remain original model outputs. Closing-axis
+   sign is symmetric. The Adapter keeps normal NMS, then preserves provider order
+   while retaining at most ten of the 24 actual proposals. The captured diagnostic
+   retains one contact-valid pose after the exact shipped two-stage selection.
+3. **Ruled out: a new collision frame or scale defect.** Independent SAPIEN URDF
+   loading without simulator steps reproduces the run3 support penetrations.
+   Component get_pose equals get_entity_pose here; native mesh scale is one.
+   Palm and finger collisions are physical candidate rejections, not a reason to
+   alter the robot mesh, support height, margins, or permitted contacts.
+
+## Seven dimensions
+
+| Dimension | Result and scope |
+|---|---|
+| Architecture integration | Public prepare owns response identity; isolated provider owns sampling; Adapter owns NMS/retention. Coordinator, readiness and Gateway retain their authorities. |
+| Recovery/idempotency | Existing recovery sees failed Query evidence with the correct scene. No old receipts edited; no Action reissued. Trial 3 was cancelled through Coordinator after confirming no Actions. |
+| Robotics safety | No motion in offline diagnostics. No collision, IK, complete-route, stop or unknown-outcome check relaxed. Sampling is advisory. |
+| Configuration/reproducibility | GraspNet-only sampling-policy CLI and profile selection_order; default score order unchanged for other providers. Unique run4 artifacts, source diff, installed versions, same checkpoint and observed inputs retained. |
+| Maintainability | Small helper reuses native candidate objects; generic provider order has two explicit choices. No new service, schema, frozen contract or hash mechanism. |
+| Observability | Persisted raw diagnostic decoder, per-link support bounds, full contact results and retained native indices. Trial logs and independent final verifier remain the task evidence. |
+| AgentLoop autonomy | Regression proves failed prepare can make its refresh node ready through existing trusted context. Live recovery and full RGB completion remain acceptance requirements. |
+
+## Validation
+
+- Focused prepare/context regressions: 77 passed.
+- Integrated Adapter/Skill/context suite: 1069 passed, 1 skipped.
+- Existing Pillow-dependent perception-worker module remains skipped in PAOS Python.
+- Ruff and git diff --check pass; exact commands are in the monthly changelog.
+- Raw candidate diagnostic: no motion, no simulator steps, unchanged loaded Panda meshes.
+
+## Acceptance status
+
+Run4 starts Skill 2.7.13 and Node 0.8.0 using robotwin-blocks-ranking-graspnet.
+Three prior independent tasks did not reach physical Actions; they are failures,
+not RGB successes. Required finish remains three tasks with at least one full
+RGB arrangement, terminal acquire/place evidence, release-retreat-return checks,
+fresh final observation, independent ForgeTaskVerifier and playable cumulative video.
~~~

### Git 提交 / Git Commit
- Branch: feature/planning-loop
- Commit receipt will be appended after the source commit.

## v11.7.15 (2026-09-25 21:40) - codex

### 变更摘要 / Change Summary [完成 / Completed]
- [model] [fix] run2 真实 GraspNet X-forward 位姿被 identity 转成 canonical Z-forward，导致手掌朝向与接近轴垂直；同时深度适配错误改写 RoboTwin 固定 0.12 m 的参考距离，使真实指尖偏离 provider 深度 40 mm。修复 provider profile 轴旋转与 generic contact-to-hand 平移计算，保留所有碰撞及运动检查。(local)
- [Model] [Fix] Real run2 GraspNet X-forward poses were treated as canonical Z-forward. Depth adaptation also rewrote RoboTwin fixed 0.12 m reference distance, causing a 40 mm fingertip error. Correct the provider frame mapping and generic contact-to-hand offset while retaining collision and motion checks. (local)
- [eval] [fix] 使用独立 RoboTwin target-to-endlink 公式验证实际指尖深度、夹爪闭合轴与 provider 接近轴；以原始候选执行无运动验证，再继续三轮 RGB AgentLoop 验收。检查选择回执的参数投影与感知恢复失败证据。(local)
- [Eval] [Fix] Test actual fingertip depth, closing axis and approach axis against independent RoboTwin endlink conversion; replay captured candidates without motion, then continue RGB AgentLoop acceptance. Inspect selection projection and perception recovery errors. (local)

### 影响文件 / Intended files
- examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py
- examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml
- examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py
- Relevant existing deployment manifests, tests and acceptance documentation.

### 边界 / Boundary
普通配置与坐标公式修复，使用既有 provenance 和普通测试；不新增 hash、gate 或 oracle 数据。
Ordinary profile/frame-math repair using existing provenance and tests; no new hash, gate or oracle evidence.

### 补充实现 / Additional implementation
- [env] [fix] 原轮次同进程负载下无动作复现 LocateAnything 启动 OOM：规划 worker 占 6.93 GiB，感知加载最后 44 MiB 失败。只在 serialized Query 退出时回收无引用对象及未使用 CUDA allocator cache，不删除持久化世界、规划对象、机械臂状态或有效轨迹。补失败/成功清理测试并实测后续感知。(local)
- [Env] [Fix] Reproduced LocateAnything startup OOM without motion under the original process load: planner worker used 6.93 GiB and perception failed allocating 44 MiB. Reclaim unreferenced objects and unused allocator cache at serialized Query exit; retain world, planner, robot state and valid trajectories. Test successful and failed query cleanup and repeat perception. (local)

### 验证 / Validation
- [eval] [exp] 1052 passed, 1 skipped；所有现有运动与碰撞检查保留；三轮真实任务验收继续进行。(local)
- [Eval] [Exp] 1052 passed, 1 skipped; existing motion and collision checks preserved; three-trial real AgentLoop acceptance continues. (local)

### 文件变更详情 / Exact changed files

#### [修改 / Modified] PhyAgentOS/forge/capability_runtime/grasp_proposal.py L30-L45, L249-L255, L507-L526
~~~diff
diff --git a/PhyAgentOS/forge/capability_runtime/grasp_proposal.py b/PhyAgentOS/forge/capability_runtime/grasp_proposal.py
index 476f95c..05437ed 100644
--- a/PhyAgentOS/forge/capability_runtime/grasp_proposal.py
+++ b/PhyAgentOS/forge/capability_runtime/grasp_proposal.py
@@ -30,6 +30,16 @@ _CANDIDATE_KEYS = {
 }
 _QUALIFICATIONS = ("proposed", "low_confidence", "ambiguous")
 _FUNNEL_STAGES = ("decoded", "canonicalized", "deduplicated", "retained")
+GRASP_GEOMETRY_SCHEMA = {
+    "type": "object",
+    "additionalProperties": False,
+    "required": ["width_m", "height_m", "depth_m"],
+    "properties": {
+        name: {"type": "number", "exclusiveMinimum": 0}
+        for name in ("width_m", "height_m", "depth_m")
+    },
+    "description": "Optional provider-predicted grasp dimensions in metres; not motion admission.",
+}


 class GraspProposalProvider(Protocol):
@@ -239,6 +249,7 @@ GRASP_TOOL_SPEC: dict[str, Any] = {
                                 },
                             },
                         },
+                        "grasp_geometry": deepcopy(GRASP_GEOMETRY_SCHEMA),
                         "score": {"type": "number", "minimum": 0, "maximum": 1},
                         "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                         "provenance": {
@@ -496,8 +507,20 @@ def _validate_candidate(
     allowed_provenance: set[str] | None = None,
     allowed_provenance_by_entity: Mapping[str, set[str]] | None = None,
 ) -> str | None:
-    if not isinstance(candidate, dict) or set(candidate) != _CANDIDATE_KEYS:
+    if (
+        not isinstance(candidate, dict)
+        or not _CANDIDATE_KEYS <= set(candidate)
+        or set(candidate) - _CANDIDATE_KEYS - {"grasp_geometry"}
+    ):
         return "invalid_candidate"
+    if "grasp_geometry" in candidate:
+        geometry = candidate["grasp_geometry"]
+        if (
+            not isinstance(geometry, dict)
+            or set(geometry) != {"width_m", "height_m", "depth_m"}
+            or any(not _finite_number(value) or value <= 0 for value in geometry.values())
+        ):
+            return "invalid_candidate_geometry"
     candidate_ref = candidate.get("candidate_ref")
     if not isinstance(candidate_ref, str) or _CANDIDATE_REF.fullmatch(candidate_ref) is None:
         return "invalid_candidate_ref"
~~~

#### [修改 / Modified] PhyAgentOS/forge/capability_runtime/manipulation_prepare.py L7-L16, L116-L122
~~~diff
diff --git a/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py b/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
index 8952a34..24195f5 100644
--- a/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
+++ b/PhyAgentOS/forge/capability_runtime/manipulation_prepare.py
@@ -7,7 +7,10 @@ from copy import deepcopy
 from dataclasses import dataclass, field
 from typing import Any, Mapping, Protocol

-from PhyAgentOS.forge.capability_runtime.grasp_proposal import _validate_candidate
+from PhyAgentOS.forge.capability_runtime.grasp_proposal import (
+    GRASP_GEOMETRY_SCHEMA,
+    _validate_candidate,
+)
 from PhyAgentOS.forge.manipulation import ArmAssignment, ManipulationIntent

 PREPARATION_TOOL_ID = "manipulation.prepare"
@@ -113,6 +116,7 @@ MANIPULATION_TOOL_SPEC: dict[str, Any] = {
                                 },
                             },
                         },
+                        "grasp_geometry": deepcopy(GRASP_GEOMETRY_SCHEMA),
                         "score": {"type": "number", "minimum": 0, "maximum": 1},
                         "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                         "provenance": {
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet-tool-transform.json L6-L12
~~~diff
diff --git a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet-tool-transform.json b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet-tool-transform.json
index 1fd2446..ec5660d 100644
--- a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet-tool-transform.json
+++ b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet-tool-transform.json
@@ -6,7 +6,7 @@
   "origin_frame": "grasp_center",
   "target_frame": "canonical_contact_center",
   "units": "m",
-  "provider_T_contact_center": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
+  "provider_T_contact_center": [0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1],
   "source_chain": [
     {
       "path": "models/graspnet.py",
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml L17-L25
~~~diff
diff --git a/examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml b/examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml
index 506cfea..bae929c 100644
--- a/examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml
+++ b/examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-graspnet.yaml
@@ -17,9 +17,9 @@ workspace_bounds_m:
   z_max_m: 1.40
 grasp_adaptation:
   extrinsic_semantics: world_to_camera_cv
-  # GraspNet reports grasp_center directly in the observation frame.
-  # No GraspGen depth reconstruction is applied.
-  provider_T_contact_center: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
+  # GraspNet: X approach, Y closing. Canonical hand: Z approach, Y closing.
+  # Preserve grasp_center; rotate axes only. No GraspGen backoff is applied.
+  provider_T_contact_center: [0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1]
   # RoboTwin Robot.*_plan_path consumes its standard gripper target. Internally
   # it converts that target to the Curobo panda_hand endlink using these values.
   robot_target_frame: robotwin_gripper
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py L2-L11, L251-L277
~~~diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
index 5a850fe..807894b 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
@@ -2,8 +2,10 @@

 from __future__ import annotations

+import gc
 import json
 import math
+import sys
 import time
 from dataclasses import asdict
 from pathlib import Path
@@ -249,6 +251,27 @@ class RoboTwinPersistentEngine:
         return self.backend._scene_revision

     def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
+        try:
+            return self._query(operation, arguments)
+        finally:
+            if operation in {"route_readiness", "contact_qualification", "observe"}:
+                # The provider serializes Queries against Actions. Retain the
+                # world and live planner tensors, but return unused allocator
+                # memory to the GPU before another perception process loads.
+                torch = sys.modules.get("torch")
+                if torch is not None and torch.cuda.is_initialized():
+                    gc.collect()
+                    before = torch.cuda.memory_reserved()
+                    torch.cuda.empty_cache()
+                    print(
+                        f"planner idle CUDA cache: operation={operation} "
+                        f"reserved_before={before} "
+                        f"reserved_after={torch.cuda.memory_reserved()} "
+                        f"allocated={torch.cuda.memory_allocated()}",
+                        file=sys.stderr,
+                    )
+
+    def _query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
         if operation == "oracle_grasp_candidates":
             if set(arguments) != {
                 "request", "provider_T_contact_center", "binding_ref"
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py L1-L7, L261-L267, L288-L297, L305-L312, L316-L322
~~~diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py
index 1b6c23c..0a9fd19 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py
@@ -1,7 +1,7 @@
 """Calibration-bound conversion from provider grasps to RoboTwin targets.

 The adapter owns two deterministic frame conversions: provider base to the
-GraspGen canonical contact center, then canonical contact center to the
+canonical contact center (Z approach, Y closing), then contact center to the
 RoboTwin standard gripper target consumed by ``Robot.*_plan_path``. It performs
 no planning, simulation, Gateway invocation, or motion authorization.
 """
@@ -261,6 +261,7 @@ def adapt_grasp_candidate(
             raise GraspAdaptationError(f"{label} must be positive")
     reference_distance = float(reference_distance)
     gripper_bias = float(gripper_bias)
+    hand_to_contact = gripper_bias
     depth_adaptation = profile.get("grasp_depth_adaptation")
     if depth_adaptation is not None:
         if (
@@ -287,10 +288,10 @@ def adapt_grasp_candidate(
             or float(tip_forward) <= float(depth)
         ):
             raise GraspAdaptationError("provider grasp depth or tool tip distance is invalid")
-        # GraspNet defines depth as the finger-tip x coordinate relative to
-        # grasp_center.  Choose the standard RoboTwin target whose panda_hand
-        # plus the URDF-derived finger reach reproduces that same depth.
-        reference_distance = float(tip_forward) + gripper_bias - float(depth)
+        # Provider depth is fingertip insertion past its contact origin.
+        # Keep RoboTwin's target-to-hand reference fixed; only the physical
+        # hand-to-contact offset depends on the provider's predicted depth.
+        hand_to_contact = float(tip_forward) - float(depth)
     if reference_distance <= gripper_bias:
         raise GraspAdaptationError("robot target reference distance must exceed gripper bias")
     robot_delta = _matrix(profile["robot_delta_matrix"], 3, 3, "robot_delta_matrix")
@@ -304,7 +305,8 @@ def adapt_grasp_candidate(
         raise GraspAdaptationError("robot_delta_matrix does not bind RoboTwin gripper x to endlink z")
     canonical_rotation = [row[:3] for row in world_from_canonical[:3]]
     robot_target_rotation = _multiply_rotation(canonical_rotation, robot_delta)
-    target_offset = _mat_vec(robot_target_rotation, [-reference_distance, 0.0, 0.0])
+    target_to_contact = reference_distance - gripper_bias + hand_to_contact
+    target_offset = _mat_vec(robot_target_rotation, [-target_to_contact, 0.0, 0.0])
     robot_target_position = [
         world_from_canonical[index][3] + target_offset[index] for index in range(3)
     ]
@@ -314,7 +316,7 @@ def adapt_grasp_candidate(
     planner_offset = _mat_vec(robot_target_rotation, [reference_distance - gripper_bias, 0.0, 0.0])
     planner_position = [robot_target_position[index] + planner_offset[index] for index in range(3)]
     reconstructed_contact = [
-        planner_position[index] + planner_rotation[index][2] * gripper_bias for index in range(3)
+        planner_position[index] + planner_rotation[index][2] * hand_to_contact for index in range(3)
     ]
     round_trip_residual = max(
         abs(reconstructed_contact[index] - world_from_canonical[index][3]) for index in range(3)
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py L3-L9, L102-L108, L110-L150
~~~diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py b/examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py
index 9a7f052..4ada21b 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grasp_adaptation.py
@@ -3,6 +3,7 @@ from __future__ import annotations
 import hashlib
 import json
 from copy import deepcopy
+from pathlib import Path

 import pytest

@@ -101,7 +102,7 @@ def test_graspnet_depth_aligns_provider_tip_depth_without_world_z_offset():

     result = adapt_grasp_candidate(proposal, payload, base, profile)

-    expected_reference = 0.11224903 + 0.08 - 0.01
+    expected_reference = 0.12 - 0.08 + 0.11224903 - 0.01
     assert result["contact_center_pose"]["position_m"] == pytest.approx([1.11, 2.22, 3.33])
     assert result["robot_target_pose"]["position_m"] == pytest.approx(
         [1.11, 2.22, 3.33 - expected_reference]
@@ -109,6 +110,41 @@ def test_graspnet_depth_aligns_provider_tip_depth_without_world_z_offset():
     assert result["robot_target_round_trip_residual_m"] < 1e-8


+@pytest.mark.parametrize("depth", [0.01, 0.02, 0.03, 0.04])
+@pytest.mark.parametrize("quaternion", [[0, 0, 0, 1], [0, 2 ** -0.5, 0, 2 ** -0.5]])
+def test_graspnet_profile_matches_native_robot_axes_and_fingertip(depth, quaternion):
+    import numpy as np
+    import yaml
+
+    from robotwin20_adapter.grasp_postprocessing import (
+        _quaternion_rotation,
+        derive_robot_hand_pose,
+    )
+
+    proposal, payload, base, profile = _inputs()
+    deployed = yaml.safe_load((Path(__file__).parents[1] /
+        "profiles/robotwin20/route-inputs-graspnet.yaml").read_text())["grasp_adaptation"]
+    profile["provider_T_contact_center"] = deployed["provider_T_contact_center"]
+    profile["grasp_depth_adaptation"] = deployed["grasp_depth_adaptation"]
+    proposal["grasp_geometry"] = {"width_m": 0.04, "height_m": 0.02, "depth_m": depth}
+    proposal["grasp_frame"]["orientation_xyzw"] = quaternion
+    provider_rotation = np.asarray(_quaternion_rotation(quaternion, "provider"))
+    proposal["approach_direction"]["vector"] = provider_rotation[:, 0].tolist()
+    result = adapt_grasp_candidate(proposal, payload, base, profile)
+    hand = derive_robot_hand_pose(result["robot_target_pose"],
+        reference_distance_m=0.12, gripper_bias_m=0.08,
+        delta_matrix=deployed["robot_delta_matrix"])
+    rotation = np.asarray(_quaternion_rotation(hand["orientation_xyzw"], "hand"))
+    center = np.array([1.1, 2.2, 3.3])
+    # Independently apply the robot's fixed conversion, then URDF finger reach.
+    fingertip = np.asarray(hand["position_m"]) + rotation[:, 2] * 0.11224903
+    assert rotation[:, 2] == pytest.approx(provider_rotation[:, 0])
+    assert rotation[:, 1] == pytest.approx(provider_rotation[:, 1])
+    assert result["ingress_direction"]["vector"] == pytest.approx(rotation[:, 2])
+    assert fingertip == pytest.approx(center + depth * provider_rotation[:, 0])
+    assert result["contact_center_pose"]["position_m"] == pytest.approx(center)
+
+
 def test_adaptation_is_deterministic_and_does_not_mutate_inputs():
     inputs = _inputs()
     before = deepcopy(inputs)
~~~

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py L224-L257
~~~diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
index 4af5923..7e1a86a 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
@@ -224,3 +224,34 @@ def test_sample_pool_is_filtered_before_retained_limit(tmp_path):
     assert len(data["candidates"]) == 10
     assert data["candidates"][0]["score"] == 1.0
     assert data["candidates"][-1]["score"] == 0.55
+
+
+def test_graspnet_geometry_crosses_public_proposal_and_prepare_boundary(tmp_path):
+    from jsonschema import validate
+    from PhyAgentOS.forge.capability_runtime.grasp_proposal import (
+        GRASP_TOOL_SPEC,
+        GraspProposalEndpoint,
+    )
+    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import (
+        MANIPULATION_TOOL_SPEC,
+        validate_arguments,
+    )
+
+    class GeometryWorker(Worker):
+        def request(self, payload):
+            reply = super().request(payload)
+            for item in reply["candidates"]:
+                item["grasp_geometry"] = {"width_m": .04, "height_m": .02, "depth_m": .01}
+            return reply
+
+    provider = GraspNetProposalProvider(GeometryWorker(), artifact_store=_store(tmp_path))
+    proposed = GraspProposalEndpoint(provider).invoke(REQUEST)
+    assert proposed["status"] == "available"
+    validate(proposed, GRASP_TOOL_SPEC["output_schema"])
+    prepared = {key: REQUEST[key] for key in (
+        "observation_ref", "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms",
+    )}
+    prepared.update(candidate_set_ref=proposed["candidate_set_ref"], candidates=proposed["candidates"])
+    assert validate_arguments(prepared) is None
+    validate(prepared, MANIPULATION_TOOL_SPEC["input_schema"])
+    assert prepared["candidates"][0]["grasp_geometry"]["depth_m"] == .01
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/CHANGELOG.md L1-L17
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/CHANGELOG.md b/examples/forge-skills/pick-place-workflow/CHANGELOG.md
index 99bfdd5..81c5ab7 100644
--- a/examples/forge-skills/pick-place-workflow/CHANGELOG.md
+++ b/examples/forge-skills/pick-place-workflow/CHANGELOG.md
@@ -1,5 +1,17 @@
 # Change Log

+## v2.7.12 (2026-09-25) - codex
+
+- [model] [fix] Correct GraspNet X-forward to canonical Z-forward mapping and native RoboTwin fingertip-depth conversion; publish Node 0.7.15.
+- [model] [fix] 修复 GraspNet X-forward 到 canonical Z-forward 旋转及 RoboTwin 实际指尖深度转换；发布 Node 0.7.15。
+
+
+## v2.7.11 (2026-09-25) - codex
+
+- [model] [fix] Carry optional metric grasp_geometry through public proposal/preparation contracts; publish Node 0.7.14.
+- [model] [fix] 公共候选生成与准备契约保留可选米制 grasp_geometry，发布 Node 0.7.14。
+
+
 ## v2.7.10 (2026-09-25) - codex

 - [policy] [feat] Add observed GraspNet benchmark profile and publish Node 0.7.13; retain independent GraspGen closure.
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml L127-L141
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml b/examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml
index cf8204e..a863806 100644
--- a/examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml
+++ b/examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml
@@ -127,6 +127,15 @@ output_schema:
               frame_id: {type: string, minLength: 1}
               unit: {const: unitless}
               vector: {type: array, minItems: 3, maxItems: 3, items: {type: number}}
+          grasp_geometry:
+            type: object
+            additionalProperties: false
+            required: [width_m, height_m, depth_m]
+            properties:
+              width_m: {type: number, exclusiveMinimum: 0}
+              height_m: {type: number, exclusiveMinimum: 0}
+              depth_m: {type: number, exclusiveMinimum: 0}
+            description: Optional provider-predicted grasp dimensions in metres; not motion admission.
           score: {type: number, minimum: 0, maximum: 1}
           confidence: {type: number, minimum: 0, maximum: 1}
           provenance:
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml L105-L119
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml b/examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml
index 66c91c0..454a148 100644
--- a/examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml
+++ b/examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml
@@ -105,6 +105,15 @@ input_schema:
                 maxItems: 3
                 items:
                   type: number
+          grasp_geometry:
+            type: object
+            additionalProperties: false
+            required: [width_m, height_m, depth_m]
+            properties:
+              width_m: {type: number, exclusiveMinimum: 0}
+              height_m: {type: number, exclusiveMinimum: 0}
+              depth_m: {type: number, exclusiveMinimum: 0}
+            description: Optional provider-predicted grasp dimensions in metres; not motion admission.
           score:
             type: number
             minimum: 0
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/pyproject.toml L1-L6
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index b167c3f..01134b6 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,6 +1,6 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.10"
+version = "2.7.12"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
 dependencies = ["httpx>=0.28,<1.0"]
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/skill.yaml L1-L6, L239-L248
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index bf243f1..63d7751 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,6 +1,6 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.10"
+version: "2.7.12"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
 gateway_url: http://127.0.0.1:19020
@@ -239,10 +239,10 @@ artifacts:
   resolver: local
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.13-linux-x86_64
-      version: "0.7.13"
+      artifact_id: robotwin20_persistent_host-0.7.15-linux-x86_64
+      version: "0.7.15"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: c1b07287749b76c358416b38c55ddc0a3e38686fc9e0c8b83a6e4d26c426041b
+      sha256: d63e4cce65e037511bf2156db471e5b9ed1d117cac69816912070c5371d9a15a
~~~

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py L266-L272, L742-L763
~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
index aa2f8ab..3bf5544 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
@@ -266,7 +266,7 @@ def test_bundle_and_package_versions_match_the_feature_revision():
     )
     import tomllib

-    assert bundle_manifest["version"] == "2.7.10"
+    assert bundle_manifest["version"] == "2.7.12"
     assert tomllib.loads(package_text)["project"]["version"] == bundle_manifest["version"]


@@ -742,3 +742,22 @@ async def test_grasp_propose_never_creates_action_session_or_motion_routes():
     ]
     assert all(not path.endswith("/grasp.propose:invoke") for path in paths)
     assert all(not path.startswith("/invocations/") for path in paths)
+
+
+@pytest.mark.parametrize("geometry", [
+    None, {}, {"width_m": .04, "height_m": .02},
+    {"width_m": .04, "height_m": .02, "depth_m": 0},
+    {"width_m": .04, "height_m": .02, "depth_m": -.01},
+    {"width_m": .04, "height_m": .02, "depth_m": True},
+    {"width_m": .04, "height_m": .02, "depth_m": float("nan")},
+    {"width_m": .04, "height_m": .02, "depth_m": float("inf")},
+    {"width_m": .04, "height_m": .02, "depth_m": .01, "motion_authorized": True},
+])
+def test_optional_grasp_dimensions_reject_malformed_geometry(geometry):
+    from PhyAgentOS.forge.capability_runtime.grasp_proposal import _validate_candidate
+
+    result = _validate_candidate(
+        candidate(grasp_geometry=geometry), frame_id="camera_front",
+        requested_entity_refs={"entity://bottle-1"}, seen_candidate_refs=set(),
+    )
+    assert result == "invalid_candidate_geometry"
~~~

#### [新增 / Added] examples/forge-adapters/robotwin20/tests/test_persistent_memory_lifecycle.py L1-L44
~~~diff
+from types import SimpleNamespace
+
+import pytest
+import robotwin_persistent_engine as engine_module
+
+
+@pytest.mark.parametrize("operation", ["observe", "contact_qualification", "route_readiness"])
+@pytest.mark.parametrize("fails", [False, True])
+def test_query_reclaims_unused_cache_after_success_and_failure(monkeypatch, operation, fails):
+    calls = []
+    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
+    world = object()
+    engine.backend = world
+    result = {"status": "available"}
+
+    def query(name, arguments):
+        calls.append(name)
+        if fails:
+            raise ValueError("qualification failed")
+        return result
+
+    cuda = SimpleNamespace(is_initialized=lambda: True, memory_reserved=lambda: 100,
+        memory_allocated=lambda: 50, empty_cache=lambda: calls.append("empty_cache"))
+    monkeypatch.setitem(engine_module.sys.modules, "torch", SimpleNamespace(cuda=cuda))
+    monkeypatch.setattr(engine_module.gc, "collect", lambda: calls.append("collect"))
+    engine._query = query
+    if fails:
+        with pytest.raises(ValueError, match="qualification failed"):
+            engine.query(operation, {})
+    else:
+        assert engine.query(operation, {}) is result
+    assert calls == [operation, "collect", "empty_cache"]
+    assert engine.backend is world
+
+
+def test_query_does_not_initialize_cuda_or_reclaim_during_status(monkeypatch):
+    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
+    engine._query = lambda operation, arguments: {"status": "available"}
+    monkeypatch.setitem(engine_module.sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
+        is_initialized=lambda: False, empty_cache=lambda: pytest.fail("must not initialize CUDA"))))
+    assert engine.query("observe", {}) == {"status": "available"}
+    monkeypatch.delitem(engine_module.sys.modules, "torch")
+    assert engine.query("observe", {}) == {"status": "available"}
+    assert engine.query("snapshot", {}) == {"status": "available"}
~~~

#### [新增 / Added] docs/forge/IMPLEMENTATION_REVIEW_V11_7_15.md L1-L65
~~~diff
+# v11.7.14-v11.7.15 GraspNet integration review
+
+Date: 2026-09-25. Scope: public candidate geometry, provider axes/depth,
+serialized planner memory lifecycle. Acceptance is still active.
+
+## Findings and repairs
+
+1. **Blocker — public producer/consumer mismatch.** GraspNet returned valid optional
+   width/height/depth, but the public proposal validator rejected all extra fields.
+   v11.7.14 adds the shared provider-neutral geometry schema to proposal and prepare,
+   validates finite positive metric dimensions, and retains rejection of unknown fields.
+   Task task_5117890e1fbf42d5 confirms nine real candidates reached preparation.
+2. **Blocker — inconsistent grasp axes.** Native GraspNet X is approach and Y closes.
+   The identity provider transform treated Z as approach in the Panda adapter.
+   v11.7.15 rotates provider axes into canonical Z-forward/Y-closing, preserving
+   the center and updating the existing transform attestation. No synthetic grasps.
+3. **Blocker — wrong native target conversion in depth adaptation.** Overwriting
+   reference_distance with tip + bias - depth made the apparent round trip use a
+   different reference from RoboTwin's actual fixed 0.12 m conversion. The fingertip
+   was 40 mm farther back along the approach axis. Keep that reference fixed and
+   use hand_to_contact = tip - depth; target_to_contact = reference - bias + hand_to_contact.
+   Independent native-conversion tests cover two orientations and four depths.
+4. **Major — cross-stage GPU starvation.** After run2 preparation the simulator/planner
+   process occupied 6.93 GiB; a no-motion LocateAnything startup failed allocating
+   the last 44 MiB. Reclaim only unreferenced Python objects and unused CUDA allocator
+   cache at serialized observe/contact/route Query exit. Live planner tensors, world
+   state and Action ownership persist. Live post-planning perception remains to verify.
+
+## Seven review dimensions
+
+| Dimension | Evidence and disposition |
+|---|---|
+| Architecture integration | Provider frame matrix remains in Adapter profile; PAOS Core only accepts generic optional metric geometry. Runtime owns memory and robot state. |
+| Recovery/idempotency | Memory cleanup executes on successful and failed Queries; same world is retained. Action invocation/status/reconciliation unchanged. Run2 had no Actions. |
+| Robotics safety | Independent fixed-offset round trip; no changed collision mesh, IK limit, margins, admission or motion authorization. Query serialization rejects active movement. |
+| Configuration/reproducibility | 24 real scored proposals before adapter NMS, at most 10 retained. GraspNet profile and existing attestation agree. Run-specific inputs/artifacts retained. GraspNet resampling is stochastic. |
+| Maintainability | Two existing frame parameters now retain separate physical meanings; new tests compare to native conversion rather than repeating the old formula. |
+| Observability | Query cleanup logs allocated/reserved CUDA bytes. OOM diagnostic and per-candidate rejection artifacts retained. Run2 session metadata corrected to actual historical identity. |
+| AgentLoop autonomy | Coordinator, selected argument projection and Action control remain unchanged. Repeated top-level wrapper arguments are still an observed concern; their exact underlying model tool calls are not retained in the parent session log. No unsupported root-cause claim. |
+
+## Validation
+
+- Public geometry repair: 146 focused tests; full Adapter/Skill 1037 passed, 1 skipped.
+- Frame/depth repair: 45 focused tests; then full suite 1045 passed, 1 skipped.
+- Integrated frame/depth/resource lifecycle: 1052 passed, 1 skipped in 13.44 seconds.
+- The skipped existing perception-worker module needs Pillow in the PAOS interpreter.
+- Same-load LocateAnything startup diagnostic reproduced CUDA OOM; it is not motion evidence.
+
+Command:
+
+    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests -q
+
+## Real acceptance status
+
+Root: /home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260925T211115
+
+- Run1 task_e6bc12008ff64bb9: failed at invalid_candidate before motion.
+- Run2 task_5117890e1fbf42d5: real perception and GraspNet succeeded; all nine
+  candidates failed contact/route qualification. Recovery observation succeeded;
+  subsequent proposal-model startup failed due to the reproduced resource condition.
+- Run3: pending corrected deployment. No RGB completion or video success is claimed.
+
+Acceptance requires three independent tasks, at least one full RGB placement,
+terminal Actions with retreat/return evidence, independent ForgeTaskVerifier success,
+and a playable cumulative video. The repairs and unit tests alone do not satisfy it.
~~~

### Git 提交 / Git Commit
- Branch: feature/planning-loop
- Source commit: 44fa473a50697d206c6563a2d4e8cd3791d8a8e1; pushed to origin/feature/planning-loop. Includes v11.7.14 public geometry repair.

### 部署收据 / Deployment receipt
- [env] [exp] Skill 2.7.12 与 Node 0.7.15 安装、校验并启动成功；第三轮独立任务使用本版本运行。动作与最终验收结论待实测。(local)
- [Env] [Exp] Skill 2.7.12 and Node 0.7.15 installed, verified and started; third independent task launched on this source. Motion and final acceptance results remain pending. (local)

## v11.7.14 (2026-09-25 21:18) - codex

### 变更摘要 / Change Summary [完成 / Completed]
- [model] [fix] 实测 task_e6bc12008ff64bb9 的 GraspNet 候选携带 grasp_geometry，但公共候选契约只允许旧八字段，导致 invalid_candidate。补齐 provider-neutral 可选 width/height/depth 米制几何在 propose→prepare 的契约与严格数值校验；不移除深度适配所需证据。(local)
- [Model] [Fix] Actual GraspNet candidates carry grasp_geometry but the public candidate contract accepts only the original eight fields, causing invalid_candidate. Carry optional provider-neutral metric width/height/depth through proposal and preparation, retaining required depth evidence. (local)
- [eval] [fix] 补充跨 Adapter→公共 Runtime→prepare 的回归，覆盖有/无几何与畸形几何；更新锁定 Node/Skill 后继续独立 RGB 验收。(local)
- [Eval] [Fix] Add Adapter-to-public-Runtime-to-prepare regressions for optional and malformed geometry; rebuild the locked Node/Skill and continue independent RGB trials. (local)

### 失败边界 / Failure boundary

实际补丁已完成，下面记录精确变更。
- 这是既有跨系统候选字段不一致的修复，不新增 hash/gate 或宽泛允许任意字段；普通单模块测试未覆盖实际 Producer/Consumer 组合，现用契约集成测试补齐。
- This repairs an existing producer/consumer mismatch; no new hashes/gates or arbitrary extra fields. An integration test covers the real boundary omitted by isolated tests.

### v11.7.14 实际变更 / Actual changes

- [model] [fix] `PhyAgentOS/forge/capability_runtime/grasp_proposal.py:L21-L31,L252-L255,L508-L523` 增加可选 provider-neutral `grasp_geometry` schema 与宽/高/深度正数校验；公共输出不再丢弃真实 GraspNet 几何。(local)
- [Model] [Fix] Adds optional provider-neutral grasp_geometry schema and positive width/height/depth validation, preserving real GraspNet geometry in public output. (local)
- [policy] [fix] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L10-L14,L85-L88` 复用同一可选字段 schema，使 Coordinator 传递到 prepare 时仍严格校验。(local)
- [Policy] [Fix] Reuses the same optional schema so Coordinator remains strict when forwarding to prepare. (local)
- [eval] [test] Adapter and Skill proposal/prepare regressions cover valid, missing and malformed geometry; 146 passed。(local)
- [Eval] [Test] Adapter and Skill proposal/prepare regressions cover valid, missing and malformed geometry; 146 passed. (local)


### 验证 / Validation
- [eval] [exp] 完整 Adapter/Skill 回归 1037 passed, 1 skipped；真实 run2 的 grasp.propose 成功并传递九个候选到 prepare。原边界缺陷已修复，最终 RGB 验收仍未通过。(local)
- [Eval] [Exp] Full Adapter/Skill regression: 1037 passed, 1 skipped. Actual run2 proposal successfully carried nine candidates into preparation. Public boundary repair is verified; final RGB acceptance remains pending. (local)
- 精确累计 Diff、行号及七维度审查见 v11.7.15 同批提交。 / Exact cumulative diffs, lines and seven-dimension review follow in v11.7.15 in the same commit.

## v11.7.13 (2026-09-25 21:10) - codex

### 变更摘要 / Change Summary [实现完成，在线验收进行中 / Implemented; live acceptance in progress]
- [model] [fix] 完成 GraspNet 真实点云 worker 验证，仅修复实证问题；候选评分排序、截断与统计保持真实来源，GraspGen 参数不进入 GraspNet。(local)
- [Model] [Fix] Validate the GraspNet worker on captured observed clouds, repair demonstrated failures, and preserve score ordering and truthful funnel counts without GraspGen parameters. (local)
- [policy] [feat] 在既有 Skill/profile 边界增加 observed + benchmark goal + runtime_monitored 的 GraspNet profile，更新并重新部署 Node/Skill。(local)
- [Policy] [Feat] Add a GraspNet profile composing observed geometry, benchmark goals and monitored simulation actions within the existing Skill boundary; rebuild and deploy the Node and Skill. (local)
- [eval] [exp] 运行针对性回归、七维代码审核及三个独立 RGB AgentLoop 任务，至少一次三块完整排列与视频才通过验收；未知 Action 以原 invocation 对账。(local)
- [Eval] [Exp] Run focused regressions, seven-dimension review and three independent RGB AgentLoop tasks; require one complete three-block success and video, reconciling unknown Actions by the original invocation. (local)
- [docs] [fix] 补齐 README/Skill 发布记录与最新五版本索引；先前宽测试的环境失败不再视作已证明的既有缺陷。(local)
- [Docs] [Fix] Complete README and Skill release notes and the latest-five index; do not treat previous environment failures as proven pre-existing defects. (local)

### 预期影响 / Expected files
- Adapter runtime/graspnet_worker.py and its focused tests if observed inference exposes defects.
- Skill skill.yaml, profiles, README/SKILL and runtime install tests; deployed runtime env.
- CHANGELOG.md, current archive and seven-dimension acceptance report.

### 实际变更与精确行号 / Changes and exact ranges

#### examples/forge-adapters/robotwin20/README.md L643-L647

~~~diff
diff --git a/examples/forge-adapters/robotwin20/README.md b/examples/forge-adapters/robotwin20/README.md
index 8cb6eca..ca88101 100644
--- a/examples/forge-adapters/robotwin20/README.md
+++ b/examples/forge-adapters/robotwin20/README.md
@@ -643,5 +643,5 @@ export ROBOTWIN20_MODEL_API_KEY=...
 ```

-The perception, GraspGen, route, controller-qualification, and motion-capability variables
+The perception, GraspNet, route, controller-qualification, and motion-capability variables
 referenced by those profiles must also be set. Then run from the development profile
 directory:
~~~

#### examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml L3-L8

~~~diff
diff --git a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
index 628cb40..6db4ffb 100644
--- a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
+++ b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspnet.yaml
@@ -3,5 +3,6 @@ provider_id: graspnet
 model_variant: baseline
 artifact_root: ${ROBOTWIN20_ARTIFACT_ROOT}
-max_candidates: 24
+max_candidates: 10
+sample_count: 24
 score_threshold: 0.02
 apply_nms: true
~~~

#### examples/forge-adapters/robotwin20/runtime/graspnet_worker.py L127-L132, L134-L138

~~~diff
diff --git a/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py b/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
index 6efac6f..2a23aad 100644
--- a/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
+++ b/examples/forge-adapters/robotwin20/runtime/graspnet_worker.py
@@ -127,4 +127,6 @@ def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
             }
         )
+    canonical_count = len(candidates)
+    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
     candidates = candidates[:max_candidates]
     return {
@@ -132,5 +134,5 @@ def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
         "status": "available" if candidates else "empty",
         "candidates": candidates,
-        "funnel": {"decoded": len(group), "canonicalized": len(candidates), "deduplicated": len(candidates), "retained": len(candidates)},
+        "funnel": {"decoded": len(group), "canonicalized": canonical_count, "deduplicated": canonical_count, "retained": len(candidates)},
     }

~~~

#### examples/forge-skills/pick-place-workflow/CHANGELOG.md L1-L12

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/CHANGELOG.md b/examples/forge-skills/pick-place-workflow/CHANGELOG.md
index 018c33d..99bfdd5 100644
--- a/examples/forge-skills/pick-place-workflow/CHANGELOG.md
+++ b/examples/forge-skills/pick-place-workflow/CHANGELOG.md
@@ -1,4 +1,12 @@
 # Change Log

+## v2.7.10 (2026-09-25) - codex
+
+- [policy] [feat] Add observed GraspNet benchmark profile and publish Node 0.7.13; retain independent GraspGen closure.
+- [policy] [feat] 新增 GraspNet 观测几何 benchmark profile，发布 Node 0.7.13，保留独立 GraspGen 配置。
+- [model] [fix] Rank native GraspNet output before the 24-candidate cap, then apply adapter NMS and retain at most 10 candidates.
+- [model] [fix] GraspNet 原生候选排序后取 24 个，再由 adapter NMS 后保留最多 10 个。
+
+
 ## v2.6.19 (2026-09-24) - codex

~~~

#### examples/forge-skills/pick-place-workflow/README.md L85-L88, L143-L155

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/README.md b/examples/forge-skills/pick-place-workflow/README.md
index b2a947f..50debc0 100644
--- a/examples/forge-skills/pick-place-workflow/README.md
+++ b/examples/forge-skills/pick-place-workflow/README.md
@@ -85,7 +85,4 @@ dataflow. `robotwin-blocks-ranking-oracle` keeps observation-owned semantic iden
 uses bound actor geometry and task-definition goals for the `blocks_ranking_rgb`
 development baseline. No profile automatically falls back to another.
-`robotwin-blocks-ranking-oracle` keeps observation-owned semantic identity but
-uses bound actor geometry and task-definition goals for the `blocks_ranking_rgb`
-development baseline. No profile automatically falls back to another.

 All persistent profiles enable adapter-owned task video. All
@@ -146,2 +143,13 @@ The tests use PAOS's real `ForgeToolClient` with an `httpx.MockTransport` and th
 exercise discovery, readiness/context, ToolSpec binding, and Query invocation through
 the documented Gateway routes. No test enables or performs motion.
+
+### Observed RGB acceptance with GraspNet
+
+Use robotwin-blocks-ranking-graspnet for benchmark-injected task goals and
+monitored simulation Actions with observed geometry. The provider takes segmented
+RGB-D object point clouds; GraspNet decodes its native output, selects the best
+24 scored candidates, and the adapter applies NMS and retains at most 10 for
+manipulation.prepare. No GraspGen backoff or contact offset is used.
+Select graspnet.yaml and persistent-materializer.yaml together via the
+existing deployment environment. Rebuild and install Node 0.7.13 and Skill 2.7.10
+before running this profile; install readiness does not prove task success.
~~~

#### examples/forge-skills/pick-place-workflow/SKILL.md L389-L400

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/SKILL.md b/examples/forge-skills/pick-place-workflow/SKILL.md
index 13edb18..d0dd3a3 100644
--- a/examples/forge-skills/pick-place-workflow/SKILL.md
+++ b/examples/forge-skills/pick-place-workflow/SKILL.md
@@ -389,2 +389,12 @@ failed or unknown execution. For successful dynamic-scene progress, complete
 the current checkpoint graph and call `forge_task_continue_plan`; discovery
 correction and failure replan are not normal forward-progression mechanisms.
+
+### GraspNet observed benchmark profile
+
+The robotwin-blocks-ranking-graspnet profile uses observed scene geometry,
+real GraspNet pose candidates and monitored simulation Actions. Only task
+descriptions and benchmark destination regions come from the benchmark task
+definition. Use task.goal destination references and reobserve after world
+changes; never replace observed point clouds or provider output with simulator
+actor geometry or template grasps. Candidate preparation, Action admission and
+verification remain owned by the existing Runtime/Coordinator boundaries.
~~~

#### examples/forge-skills/pick-place-workflow/pyproject.toml L1-L5

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index 20916d6..b167c3f 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.9"
+version = "2.7.10"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
~~~

#### examples/forge-skills/pick-place-workflow/skill.yaml L1-L5, L64-L110, L240-L248

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index 6c23564..bf243f1 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,5 +1,5 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.9"
+version: "2.7.10"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
@@ -64,4 +64,47 @@ profiles:
       ROBOTWIN20_SIMULATION_ACTION_MODE: runtime_monitored
       ROBOTWIN20_GOAL_SOURCE: benchmark_task_definition
+  robotwin-blocks-ranking-graspnet:
+    dataflow: profiles/robotwin-persistent/dataflow.yaml
+    required_binaries:
+      - robotwin20_persistent_host
+    required_assets: []
+    required_environment:
+      - ROBOTWIN20_PAOS_PYTHON
+      - ROBOTWIN20_ARTIFACT_ROOT
+      - ROBOTWIN20_RUNTIME_ROOT
+      - ROBOTWIN20_RUNTIME_PROFILE
+      - ROBOTWIN20_WORKER_PYTHON
+      - ROBOTWIN20_MATERIALIZER_PYTHON
+      - ROBOTWIN20_GRASP_PROFILE
+      - ROBOTWIN20_MATERIALIZER_ARGUMENTS
+      - ROBOTWIN20_MODEL_API_BASE
+      - ROBOTWIN20_MODEL_API_KEY
+      - ROBOTWIN20_MODEL
+      - ROBOTWIN20_REASONING_EFFORT
+      - ROBOTWIN20_ROUTE_GEOMETRY_SOURCE
+      - ROBOTWIN20_SIMULATION_ACTION_MODE
+      - ROBOTWIN20_GOAL_SOURCE
+      - LOCATEANYTHING_PYTHON
+      - LOCATEANYTHING_CACHE_DIR
+      - LOCATEANYTHING_MODULES_CACHE_DIR
+      - SAM2_PYTHON
+      - SAM2_REPO_ROOT
+      - SAM2_CHECKPOINT
+      - GRASPNET_PYTHON
+      - GRASPNET_CHECKPOINT
+      - GRASPNET_SOURCE_ROOT
+      - GRASPNET_DEVICE
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_PLAN
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_EVIDENCE
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_VALIDATION
+      - ROBOTWIN20_LEFT_MOTION_CAPABILITY
+      - ROBOTWIN20_LEFT_MOTION_CAPABILITY_VALIDATION
+      - ROBOTWIN20_RIGHT_MOTION_CAPABILITY
+      - ROBOTWIN20_RIGHT_MOTION_CAPABILITY_VALIDATION
+    environment:
+      ROBOTWIN20_ROUTE_GEOMETRY_SOURCE: observed
+      ROBOTWIN20_SIMULATION_ACTION_MODE: runtime_monitored
+      ROBOTWIN20_GOAL_SOURCE: benchmark_task_definition
   robotwin-blocks-ranking-observed:
     dataflow: profiles/robotwin-persistent/dataflow.yaml
@@ -197,9 +240,9 @@ artifacts:
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.12-linux-x86_64
-      version: "0.7.12"
+      artifact_id: robotwin20_persistent_host-0.7.13-linux-x86_64
+      version: "0.7.13"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: 106da563b7d43b0b64845b55640f69630c9430d5b762aedaedc32c29205601a2
+      sha256: c1b07287749b76c358416b38c55ddc0a3e38686fc9e0c8b83a6e4d26c426041b
~~~

#### examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py L267-L271

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
index 3e44b99..aa2f8ab 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
@@ -267,5 +267,5 @@ def test_bundle_and_package_versions_match_the_feature_revision():
     import tomllib

-    assert bundle_manifest["version"] == "2.6.20"
+    assert bundle_manifest["version"] == "2.7.10"
     assert tomllib.loads(package_text)["project"]["version"] == bundle_manifest["version"]

~~~

#### examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py L330-L349

~~~diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py b/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
index 234715a..e7f319c 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
@@ -330,2 +330,20 @@ def test_runtime_manager_status_reads_http_health_and_fails_closed_on_missing_co
         server.server_close()
         thread.join(timeout=2)
+
+
+def test_graspnet_acceptance_profile_preserves_observed_action_boundaries():
+    manifest = load_manifest(BUNDLE_ROOT / "skill.yaml")
+    profile = manifest.profiles["robotwin-blocks-ranking-graspnet"]
+    assert profile.environment == {
+        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "observed",
+        "ROBOTWIN20_SIMULATION_ACTION_MODE": "runtime_monitored",
+        "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
+    }
+    assert profile.dataflow == manifest.profiles["robotwin-blocks-ranking-observed"].dataflow
+    assert "GRASPNET_CHECKPOINT" in profile.required_environment
+    assert not any(name.startswith("GRASPGEN_") for name in profile.required_environment)
+    adapter = BUNDLE_ROOT.parents[1] / "forge-adapters/robotwin20"
+    grasp = yaml.safe_load((adapter / "profiles/robotwin20/graspnet.yaml").read_text())
+    assert grasp["sample_count"] == 24
+    assert grasp["max_candidates"] == 10
+    assert grasp["apply_nms"] is True
~~~

#### examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py L1-L55

~~~diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py b/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py
new file mode 100644
index 0000000..3fcf28f
--- /dev/null
+++ b/examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py
@@ -0,0 +1,55 @@
+"""GraspNet ranking contract; no optional image/model packages required."""
+
+import importlib.util
+import sys
+from pathlib import Path
+
+import numpy as np
+
+
+def _module(name):
+    runtime = Path(__file__).resolve().parents[1] / "runtime"
+    if str(runtime) not in sys.path:
+        sys.path.insert(0, str(runtime))
+    spec = importlib.util.spec_from_file_location(name, runtime / (name + ".py"))
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    return module
+
+
+def test_graspnet_ranks_before_limit_and_reports_full_threshold_funnel(tmp_path, monkeypatch):
+    from contextlib import nullcontext
+    from types import SimpleNamespace
+
+    module = _module("graspnet_worker")
+    points = tmp_path / "observed.npy"
+    np.save(points, np.ones((20, 3), dtype=np.float32))
+    grasps = [SimpleNamespace(
+        translation=np.array([index * .01, 0, 1]), rotation_matrix=np.eye(3),
+        score=score, width=.04, height=.02, depth=.01,
+    ) for index, score in enumerate([.1, .4, .01, .9, .8])]
+
+    class Network:
+        def parameters(self):
+            return iter([SimpleNamespace(device="cpu")])
+
+        def __call__(self, inputs):
+            return inputs
+
+    decoded = SimpleNamespace(detach=lambda: SimpleNamespace(
+        cpu=lambda: SimpleNamespace(numpy=lambda: grasps)))
+    module._MODEL = (Network(), lambda _: [decoded], lambda values: values)
+    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
+        no_grad=nullcontext,
+        from_numpy=lambda array: SimpleNamespace(to=lambda device: array),
+    ))
+    result = module._handle({
+        "schema_version": "paos-grasp-worker/v1", "provider": "graspnet",
+        "request_id": "observed-test", "point_cloud_path": str(points),
+        "max_candidates": 2, "score_threshold": .02,
+    })
+    assert [candidate["score"] for candidate in result["candidates"]] == [.9, .8]
+    assert result["candidates"][0]["matrix"][0][3] == .03
+    assert result["funnel"] == {
+        "decoded": 5, "canonicalized": 4, "deduplicated": 4, "retained": 2,
+    }
~~~

#### docs/forge/IMPLEMENTATION_REVIEW_V11_7_13.md L1-L70

~~~diff
diff --git a/docs/forge/IMPLEMENTATION_REVIEW_V11_7_13.md b/docs/forge/IMPLEMENTATION_REVIEW_V11_7_13.md
new file mode 100644
index 0000000..f3fb839
--- /dev/null
+++ b/docs/forge/IMPLEMENTATION_REVIEW_V11_7_13.md
@@ -0,0 +1,70 @@
+# v11.7.13 GraspNet deployment and RGB acceptance review
+
+Date: 2026-09-25, Asia/Shanghai. Branch: feature/planning-loop.
+
+## Findings and repairs
+
+1. **Major, repaired: deployment did not expose the requested composition.**
+   Generic profiles selected GraspNet, but observed actions were disabled; the
+   benchmark action profile still selected GraspGen. Added the explicit
+   robotwin-blocks-ranking-graspnet profile, reusing generic dataflow and existing
+   observed geometry, benchmark goal and monitored Action owners.
+2. **Major, repaired: native decode order controlled the worker cap.**
+   Real inference on a captured 704-point perception cloud produced 1,024 decoded
+   candidates. The previous first 24 scores were unsorted (0.091, 0.117, ..., 0.614).
+   Sort by native score before the 24-candidate cap. Report the threshold count
+   before truncation. Adapter NMS retains at most 10; it does not pad candidates.
+3. **Major, repaired: deployed artifacts lagged source.**
+   Rebuilt Node 0.7.13 and Skill 2.7.10 together using the existing artifact lock.
+   The old task had only settled Queries and no Action invocation; Coordinator
+   cancelled it before RuntimeManager stopped the old deployment.
+4. **Minor, repaired: stale package assertion and documentation.**
+   Update the package assertion from 2.6.20 to 2.7.10, remove duplicate oracle prose,
+   correct the generic provider name and document the observed benchmark profile.
+5. **Test coverage correction.** The PAOS environment lacks Pillow, so the existing
+   perception-worker module skips collection. The new GraspNet ranking regression
+   is in its own file and executes without optional image or model dependencies.
+
+## Seven dimensions
+
+| Dimension | Source review | Evidence / boundary |
+| --- | --- | --- |
+| Architecture integration | Pass | Provider ranking in isolated worker; selection/configuration in adapter/profile; no Core task-specific branch. |
+| Recovery and idempotency | Unchanged; live evidence pending | Same-invocation reconciliation and Coordinator task ownership preserved; old query-only task cancelled through CLI. |
+| Robotics safety | Preserved; full route pending | Observed geometry, GraspNet transform and provider depth; existing workspace/contact/collision/route/Action gates remain enabled. |
+| Configuration and reproducibility | Pass for deployment | Explicit GraspNet env, checkpoint/source, sample 24 / retain 10, new artifact root, model gpt-5.6-sol high, existing Node lock verified. |
+| Maintainability | Pass | Existing extension seams, independent provider configs, isolated regression; no new protocol or speculative gate. |
+| Observability | Improved | Honest pre-cap worker count and scored candidates; source patch, session, config and process exit saved per run. |
+| AgentLoop autonomy | Live validation in progress | PAOS Agent creates task and plans each segment; operator does not fabricate bindings or drive robot actions. |
+
+## Validation
+
+Dedicated GraspNet interpreter successfully loaded the existing baseline checkpoint
+and ran inference on a captured observed point cloud. Local source commit and
+models/graspnet.py matched the existing transform attestation. No new attestation
+scheme or relaxed geometry checks were introduced.
+
+Commands:
+
+    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests -q
+    /home/yanxu/miniconda3/envs/paos/bin/python -m ruff check examples/forge-adapters/robotwin20/runtime/graspnet_worker.py examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+    git diff --check
+
+The first full run reported 1026 passed, 1 skipped. The isolated GraspNet ranking
+regression then passed separately; final combined count is recorded in changelog.
+The earlier Python 3.13/environment failures are not evidence of pre-existing code
+failures. The PAOS Python 3.12 invocation with script paths and asyncio plugin is
+used here. Optional Pillow-dependent worker tests remain skipped in this interpreter.
+
+## Acceptance requirement remains active
+
+Three independent RGB tasks are required, with at least one complete red/green/blue
+placement, terminal Actions, post-release retreat and return evidence, an independent
+ForgeTaskVerifier result, and a playable cumulative video. Package readiness and
+unit tests do not satisfy this requirement. First live GraspNet task:
+task_e6bc12008ff64bb9. Artifacts:
+/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260925T211115/run1.
+
+Real baseline inference resamples the point cloud stochastically; the captured
+input, checkpoint, source revision and resulting candidates are retained. This
+review does not claim identical candidate ordering across independent model runs.
~~~

### 验证 / Validation
- [eval] [exp] 聚焦 121 passed / 1 skipped；最终完整 Adapter/Skill 1027 passed / 1 skipped；拆出的排序测试另外 1 passed，不将重叠测试相加。(local)
- [Eval] [Exp] Focused 121 passed / 1 skipped; final full Adapter/Skill 1027 passed / 1 skipped; isolated ranking regression 1 passed. Overlapping suites are not added. (local)
- [eval] [exp] 真正 GraspNet checkpoint 与 704 点观测点云推理成功；Node/Skill 已安装并启动，第一轮 AgentLoop task_e6bc12008ff64bb9 进行中，三轮验收尚未完成。(local)
- [Eval] [Exp] Actual GraspNet checkpoint inference on a 704-point observed cloud succeeded. Node/Skill deployed; first AgentLoop task_e6bc12008ff64bb9 is running. Three-trial acceptance remains incomplete. (local)
- [docs] [fix] 更正前版宽测试归因：可选依赖与解释器问题不构成已证明的既有代码缺陷；本轮正确环境回归通过。(local)
- [Docs] [Fix] Correct the previous broad-test attribution: interpreter/optional-dependency errors did not prove pre-existing defects; the correctly configured regression passes. (local)

### Git 提交 / Git Commit
- Source commit: a210c44937cdcb3514a09341b33c28a13539b6ab; pushed to origin/feature/planning-loop.
- Branch: feature/planning-loop
