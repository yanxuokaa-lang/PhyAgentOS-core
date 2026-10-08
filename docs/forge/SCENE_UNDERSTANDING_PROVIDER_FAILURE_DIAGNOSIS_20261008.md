# Scene Understanding Provider Failure Diagnosis / 场景理解 Provider 失败诊断

## Incident / 事件

Task `task_c1a20636b1cd4e39` stopped at `after_red_understand` in
`revision_b70559dc91234499`. The red acquire and place Actions had already
settled successfully. The post-place observation and capability query also
completed, but the semantic `scene.understand` Query returned
`understanding_provider_error`.

任务在红块抓取、准备、放置以及放置后观察和能力刷新完成后，停止于
`after_red_understand`。失败不是动作 admission、场景血缘或目标投影失败。

## Evidence / 证据

- Decision trace: `artifacts/planning-traces/task_c1a20636b1cd4e39/revision_b70559dc91234499/after_red_understand/a040b4f374094b9c.json`.
- Input scene revision: `14259a4e40b24c338a3ca5a033b46d37-3`.
- Input freshness: `113 ms`; synchronized capture skew: `0 ms`.
- RGB, depth, state, calibration and both view records were present.
- Runtime diagnostic: `scene-understanding-diagnostics.jsonl` recorded the request as an error after about `9.1 s`.
- vLLM service logs show `/v1/chat/completions` returned HTTP 200 and the service remained running.
- Action video evidence was preserved under the persistent task-video `action-0002/video` directory; no later Action was authorized.

The public failure projection was:

```json
{
  "code": "understanding_provider_error",
  "reason": "provider_failure",
  "failure_stage": "provider",
  "retryable": false,
  "provider_route": "qwen3-vl-4b-vllm",
  "provider_error_class": "none"
}
```

`provider_error_class=none` was not evidence of a healthy provider. It was an
observability loss at the lifecycle wrapper boundary. The available evidence
does not prove whether the original HTTP-200 response failed JSON parsing,
contract projection, or another provider-stage check.

## Root cause and boundary / 根因与边界

1. `LifecycleManagedSceneUnderstandingInference` forwarded `infer()` and
   readiness, but not the wrapped provider's bounded `diagnostic_summary()`.
   Core therefore received `none` after a real provider failure.
2. The fallback profile caught lifecycle and contract subclasses but omitted the
   base `Qwen3VLVLLMInferenceError`, so some provider-stage failures could stop
   before the configured fallback was attempted.
3. The Qwen adapter used one broad inference exception for malformed response
   and projection failures. Those failures are contract failures and are now
   classified as `contract`; unexpected transport/timeout causes retain their
   bounded categories.

## PAOS resolution / PAOS 解决方案

- Adapter owns provider-specific error classification and bounded diagnostics.
- Runtime/ToolSpec continues to expose only provider-neutral fields.
- Core and AgentLoop retain `retryable=false` stop behavior when no semantic
  evidence exists; no automatic observe, understand, replan, binding, or Action
  is added.
- Lifecycle management remains operator-owned and does not wake or start a
  provider during discovery readiness checks.
- No task-specific, RGB, color, arrangement, camera, object-count, or fixed-arm
  branch was added.

## Validation / 验证

No task was created or resumed, no real Gateway Query/Action was invoked, and no
simulator or physical motion was advanced. Focused Adapter regression:

```text
74 passed
compileall passed
ruff check passed
git diff --check passed
```

Remaining operational risk: the live provider failure cannot be retroactively
classified beyond the bounded artifact evidence. The next run will preserve the
classification and allow the configured fallback where its policy permits it.
