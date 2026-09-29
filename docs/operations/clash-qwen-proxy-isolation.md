# Clash 与本地 Qwen vLLM 网络隔离 / Clash and Local Qwen vLLM Network Isolation

## 目标 / Goal

- PAOS 主模型保持 `https://api.shuaiapi.com/v1` / `gpt-5.6-sol`，外部请求通过 Clash。
- 本地场景理解保持 `http://127.0.0.1:8012` / `qwen3-vl-4b-awq`，回环请求直接连接。

## 隔离规则 / Isolation Rules

- Runtime 使用 `socks5://127.0.0.1:7897`，并设置 `NO_PROXY/no_proxy=127.0.0.1,localhost,::1`。
- Qwen systemd 服务清除所有继承代理；生产 inference/lifecycle 客户端保持 `trust_env=False`。
- RobotWin 占用约 4.8 GiB GPU 显存时，Qwen 使用 `--gpu-memory-utilization 0.58`。

## 当前场景 seeds 0-9 / Current Scene Seeds 0-9

- 使用生产 `_prompt()`、`_VLLM_SCENE_SCHEMA`、`top_p=1` 和 `max_tokens=768`。
- 传输成功：10/10；RGB 同时识别：0/10。
- 实体计数：`[3,4]`；关系计数：`[2,3]`；歧义计数：`[1]`。
- 颜色频次：`{"blue,white,black":10}`。

| Seed | HTTP | Entities | Colors | Relations | Ambiguities | RGB complete | Seconds |
|---:|---:|---:|---|---:|---:|---|---:|
| 0 | 200 | 3 | blue, white, black | 2 | 1 | no | 5.98 |
| 1 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.67 |
| 2 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.68 |
| 3 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.68 |
| 4 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.7 |
| 5 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.68 |
| 6 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.68 |
| 7 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.62 |
| 8 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.68 |
| 9 | 200 | 4 | blue, white, black | 3 | 1 | no | 4.67 |

## 判定 / Interpretation

- HTTP/JSON 成功但未出现完整 RGB 是语义证据不足，不是 Qwen 服务不可用。
- `scene.bind grounding_unavailable` 是 Runtime idle/action-driven 门禁，不由代理配置或 GPT fallback 绕过。
- GPT 5.6 sol 负责主 Agent，Qwen 负责本地视觉理解。
