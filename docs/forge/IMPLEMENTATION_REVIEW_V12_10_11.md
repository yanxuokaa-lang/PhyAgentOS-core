# Implementation Review v12.10.11 / 七维 Code Review

## Findings and Disposition / 发现与处置

### Major: wrapped transport failures lost their public reason / 已修复

`Qwen3VLVLLMSceneUnderstandingInference` classified a raw timeout or transport
exception for its local diagnostic, then raised a new base
`Qwen3VLVLLMInferenceError` without that class. The PAOS endpoint therefore
reported `error.reason=provider_failure` even when the provider had established
`timeout` or `transport`; fallback could still run, but the public failure fact
and retryability were inconsistent. The exception now carries a bounded class
and retryable flag through the wrapper. Authentication is classified before the
generic HTTP/transport match.

### Major: Core diagnostics were coupled to current model names / 已修复

`_provider_diagnostics` accepted only three historical fallback model strings.
A valid configured provider route with another model was silently omitted,
making deployment diagnosis incomplete and violating configuration
externalization. Core now accepts a bounded provider-neutral token and validates
composed error classes against the stable class vocabulary; arbitrary or
oversized values are omitted. Declared exception classes use the same
fail-closed validation.

### Major: Adapter diagnostic sinks had no common size/shape bound / 已修复

The lifecycle wrapper and persistent JSONL sink checked only that diagnostic
values were strings. A provider or configuration could therefore write an
unbounded route or whitespace-containing text into readiness and artifact
diagnostics. Both seams now require a printable, non-whitespace token of at
most 128 characters. This is a concrete transport/logging boundary limit, not a
task-specific gate.

## Seven Dimensions / 七个维度

1. **Architecture / 架构**: pass. Provider classification remains Adapter-owned;
   Core only validates and projects bounded facts; fallback policy and AgentLoop
   authority are unchanged.
2. **Correctness / 正确性**: pass after fixes. Timeout, transport,
   authentication, contract, and generic provider failures retain stable public
   reasons; invalid declared classes fail closed.
3. **Recovery and idempotency / 恢复与幂等**: pass. No new retry, fallback
   policy, Action replay, or task mutation was introduced. Existing unknown
   Action reconciliation remains authoritative.
4. **Robotics safety / 机器人安全**: pass within scope. Changes touch only
   read-only scene-understanding diagnostics and provider lifecycle metadata;
   admission, planning, collision, authorization, stop, and motion paths are
   unchanged. All validation is fake/no-motion.
5. **Extensibility / 扩展兼容**: pass after fixes. Provider route names are
   configuration-driven bounded tokens rather than a fixed model-name list;
   there is no RGB, color, arrangement, camera, object-count, or fixed-arm
   branch.
6. **Observability and maintainability / 可观测性与可维护性**: pass after
   fixes. Full provider diagnostics remain in bounded adapter artifacts, while
   Core exposes only stable categories and routes; invalid values cannot leak
   exception text or inflate JSONL records.
7. **AgentLoop autonomy and convergence / AgentLoop 自主性与收敛**: pass.
   Provider errors remain Query failures. The AgentLoop still chooses whether
   to collect new evidence or stop; no observation, understanding, binding,
   replan, Action, or unknown-Action retry is automatic.

## Changed Files / 修改文件

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py:L27-L87,L128-L144,L265-L286`
  - Added bounded exception metadata and preserved classified errors through
    generic wrapping; added authentication classification.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_lifecycle.py:L15-L20,L281-L299`
  - Marked lifecycle failures as transport/retryable and bounded wrapper
    diagnostics.
- `PhyAgentOS/forge/capability_runtime/understanding.py:L24-L27,L379-L429`
  - Replaced fixed route allowlist with bounded token validation and fail-closed
    error-class validation.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py:L63-L65,L136-L170`
  - Bounded readiness and persistent diagnostic route/error fields.
- `examples/forge-adapters/robotwin20/tests/test_qwen3_vl_vllm_scene_understanding.py:L186-L245`
  - Added timeout wrapping and authentication classification regressions.
- `examples/forge-adapters/robotwin20/tests/test_scene_understand_provider.py:L102-L180`
  - Added dynamic route, invalid token, wrapped transport, and invalid declared
    class regressions.
- `examples/forge-adapters/robotwin20/tests/test_qwen3_vl_vllm_lifecycle.py:L144-L168`
  - Covered a non-hard-coded configured route through the lifecycle seam.
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py:L25-L44`
  - Covered JSONL sink rejection of oversized/unstructured tokens.

## Validation / 验证

- Adapter provider/lifecycle/fallback/endpoint/host focused suite: `80 passed`.
- Core planning/tool/runtime focused suite: `118 passed`.
- Ruff: passed for all changed source and tests.
- `compileall`: passed for Core understanding and Adapter source.
- `git diff --check`: passed.
- Full Adapter collection: `844 passed, 18 failed`; the failures are optional
  dependency gaps (`scipy`, `cv2`, `PyYAML`) and existing Action/video/backend
  fixtures outside the changed Provider diagnostics path. No changed-path test
  failed.
- No task was created or resumed, no Gateway Query/Action was invoked, no
  simulator step or physical motion advanced, and Runtime was not restarted.

## Remaining Risks / 残余风险

The public error vocabulary remains intentionally small; a new provider class
must be added to the Core vocabulary and its tests before it can cross the
ToolSpec boundary. This review does not claim live vLLM availability or a
successful physical task execution.
