# Implementation Review v12.10.3 / 七维实现审查

## Findings / 发现

### Major: an oversized request terminated a live persistent worker / 已修复

`JsonlProcessWorkerClient._write()` rejects an oversized request before writing
bytes, but `request()` previously aborted the worker for every exception. The
world process therefore exited for a caller-side serialization error even
though the protocol generation remained synchronized. `PersistentWorkerClient`
also marked the world lost for that typed pre-write rejection. The two layers
now preserve the live worker only for `worker_request_too_large`; response
overflow and all ambiguous transport failures still fail closed.

`JsonlProcessWorkerClient._write()` 虽在写入前拒绝超限请求，但 `request()` 以前会对
所有异常终止 worker。即使没有发送任何字节、协议仍同步，调用侧序列化错误也会关闭
world process。`PersistentWorkerClient` 也会把该明确的发送前拒绝标记为 world lost。
现在两层只对 `worker_request_too_large` 保留活 worker；响应超限和其他有歧义的传输
故障仍 fail-closed。

### Minor: receipt truncation was not consistently observable / 已修复

Oversized references and malformed nested/non-finite terminal values could be
silently clipped or pass through the receipt projection. Projection now admits
only bounded scalar terminal values and bounded reference lists, marks every
omission with `receipt_truncated`, rejects non-finite JSON numbers, and keeps
oversized scene effects non-carry-forward-authorizing.

过长引用和异常嵌套/非有限终态值可能被静默截断或穿过 receipt 投影。现在只允许有界
标量终态值与有界引用列表，任何省略均设置 `receipt_truncated`，拒绝非有限 JSON 数值，
并继续对过大 scene effects 禁止 carry-forward。

## Seven Dimensions / 七维验收

1. **Architecture / 架构**: pass. Request budget handling belongs to the JSONL
   transport owner; terminal projection remains provider-owned. No AgentLoop or
   Gateway behavior was moved into the Adapter.
2. **Correctness / 正确性**: pass. A pre-write request rejection leaves the
   worker usable; an oversized response still invalidates the generation and
   yields an infrastructure-owned unknown result.
3. **Recovery and idempotency / 恢复与幂等**: pass. No request is resent
   automatically. A rejected request did not reach the worker; ambiguous Action
   outcomes remain reconciliation-only.
4. **Robotics safety / 机器人安全**: pass within scope. No motion, admission,
   frame, calibration, collision, stop, or authorization policy changed.
5. **Extensibility / 扩展兼容**: pass. The rules are generic JSONL/receipt
   boundaries and contain no task, entity, color, camera, benchmark, or arm-name
   branching.
6. **Observability and maintainability / 可观测性与可维护性**: pass. Typed
   protocol errors remain distinct; receipt omissions are visible; full Action
   diagnostics remain in Runtime artifacts.
7. **AgentLoop autonomy and convergence / AgentLoop 自主性与收敛**: pass.
   AgentLoop policy is unchanged: no retry/replan/next Action is inferred from an
   unknown result.

Final result / 最终结果: Blocker 0, Major 0, Minor 0.

## Validation / 验证

- Changed-path Adapter suites: `56 passed`.
- Full Adapter suite: `831 passed, 21 failed`; residual failures are outside the
  changed path and include missing optional `scipy`/`cv2`, two existing fake
  Action contract mismatches, and an existing YAML monkeypatch failure.
- Skill full suite: `383 passed`; release/projection subset: `75 passed`.
- Core AgentLoop/planning subset: `130 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Node `1.0.1` and Skill `3.0.9` archives built under
  `/tmp/paos-v12.10.3-release-hJuPJb`; Node SHA-256 is
  `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63`, and
  Skill bundle SHA-256 is
  `8704dc608c6d20d1440a306c5bef180cd076e009b172c46e0cf0f4f218849ba7`.

All tests are no-motion. No task was created/resumed, no live Gateway Action was
sent, and no simulator step or physical motion was advanced. No Runtime was
stopped, installed, or restarted in this review turn.
