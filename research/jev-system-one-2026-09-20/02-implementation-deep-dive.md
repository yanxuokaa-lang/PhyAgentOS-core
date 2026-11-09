# Jev 生态：源码级实现深挖

本报告基于 2026-09-20 保存的默认分支文本快照。逐节标出实际实现与未运行边界；分支会继续变化，在线仓库后来的行号可能不同。本地源码是本次分析对象。没有安装这些项目、下载模型权重、调用收费 API、执行训练或连接硬件。

## 实现路线对照

| 路线 | 项目 | 分数来源 | “并行”的具体含义 |
|---|---|---|---|
| 训练专用 readout | kev | LoRA backbone + pointer head | 单序列 block mask 隔离问题 |
| 候选路径 + head | minojev | path hidden + set attention | fresh path batch 或 prefix/suffix 两阶段 |
| 冻结生成模型读 logits | LitJev、SemIf | 候选 token 的 vocab logits | prefix forward + suffix batch forward |
| 推理服务器代理 | openjev-sglang | 一个输出位置的 selected logprobs | warmup + 多个独立 branch 请求 |
| Encoder 决策头 | Von、Verdict | MASK hidden 或动态 label logits | 同题选项合并 / 多题 batch，项目间不同 |
| 现有分类器适配 | jeff、poorjev | sigmoid label score / NLI entailment | encoder unit 或 premise-hypothesis pair batch |
| 本地约束推理 | jevmlx | token/trie 候选评分 | prefix broadcast、按内存分块、可选第二遍 |
| 托管 Jev 应用 | browser/pruner/align/drone/reranker | 远程 Jev API | 原子问题 fan-out，应用代码消费答案 |

## 1. kev：训练 LoRA + 指针决策头

仓库：https://github.com/jaredpalmer/kev

**执行链**：`api.to_record → encode → branch_mask_batch → DecisionModel.hidden_batch → PointerHead → softmax → typed response`。

`encode` 把 state 和所有 question 打包成一个 token sequence；复用 Qwen 的五个特殊 token 标记 state/question/option/end-option/decision。每个 question 的 position id 从 state 尾部重新开始。mask 的基本条件是 `j≤i 且 (seg[j]==0 或 seg[j]==seg[i])`，因此每个问题可看 state 和自身前文，不能看兄弟问题。可选 `option_isolation` 再限制选项彼此的可见性。

不是从 vocab logits 中选 A/B/C：先拿每个选项结束 token 与 `<decide>` 的 hidden state，做 `z_i = W_k h_option_i · W_q h_decide / sqrt(d_pointer)`，再在当前题 K 个候选上 softmax。`PointerHead` 默认投影维度 256；实际模型配置可覆盖。

backbone 使用 `AutoModelForCausalLM(...).model`，舍去词表生成头；LoRA 可覆盖 q/k/v/o 和 FFN gate/up/down。LoRA alpha=2r、dropout=0.05。训练基本损失为标签 cross entropy；可选 Score 的 ranked probability score、选项重排的双向 KL、向冻结 base 分布的 KL anchoring。不能把这些可选项一律说成发布 checkpoint 都开启。

重要容量细节：代码默认 `MAX_STATE=384, MAX_BRANCH=1024`；strict 模式拒绝超长，非 strict 会截 state。训练另检查 packed tokens≤2048。**兼容 API 形状不等于继承官方 64k/32k 能力**。

**后续开发**：已从 Qwen2.5-0.5B 延伸到 Qwen3 0.6B/4B/8B，提交记录包含 v7/v8 配方、anchoring 研究和 locked-test 处理。README 自报 4B/8B 的域外表现，报告在 `runs/`、卡片在 `docs/model-cards/`；本次未下载权重或重跑，亦不把其架构反推成 Jev 官方架构。

**代码入口**

- [`kev/model.py` L30–L67](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/model.py:30)（`encode`）
- [`kev/model.py` L75–L101](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/model.py:75)（`branch_mask_batch`）
- [`kev/model.py` L104–L112](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/model.py:104)（`PointerHead`）
- [`kev/model.py` L115–L175](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/model.py:115)（`DecisionModel`）
- [`kev/train.py` L23–L31](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/train.py:23)（`question_loss`）
- [`kev/train.py` L34–L39](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/jaredpalmer__kev/kev/train.py:34)（`anchor_loss`）


## 2. LitJev：共享 prefill + 第二次 forward，直接读取候选 token logits

仓库：https://github.com/zhengxuyu/litjev

**执行链**：`SchemaDecisionEngine.evaluate → provider.score → TransformersScorer._score → calibrated_distribution → Choice/Score/Noul`。

先编译 prefix 与每个问题的 suffix/候选单 token code。第一次 `model(...use_cache=True, logits_to_keep=1)` 计算共享 prefix；随后通过 `cache.reorder_cache(zeros(N))` 把该 cache 复制给 N 个问题分支。第二次 model forward 批量计算 suffix；从每一行真实 suffix 最后位置的 logits 取该题 candidate token IDs，得到候选分数。

没有生成自然语言，也没有训练新 classifier head；**当前代码是 two-forward，而不是字面的一次 model.forward**。`Evaluation.diagnostics.forward_calls` 明确写 2。对 hybrid Qwen，分支复制要求同时支持 KV 与 convolution/recurrent state；视觉路径还显式处理 M-RoPE delta，因此不能随意换一个不支持该缓存协议的模型。

`SchemaDecisionEngine` 用 temperature 调整后做 softmax。confidence 是归一化 Gini 集中度：`(K*Σp²−1)/(K−1)`，不是 Jev 服务的精确复现。Score 是等级期望，Noul 取 true 概率。诊断保存 candidate token、readout layer、slot 与温度等信息。

**当前边界**：源码默认 model id 为 `Qwen/Qwen3.8-27B`，视觉分支只在指定 `qwen3_5` 类型和 processor 条件下启用。视觉扩展属于该独立项目，不能写成官方 Jev 已支持图像。README 的简短宣传应以这里的实际后端路径补充。

**代码入口**

- [`src/litjev/backend.py` L23–L177](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zhengxuyu__litjev/src/litjev/backend.py:23)（`TransformersScorer`）
- [`src/litjev/decision.py` L75–L130](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zhengxuyu__litjev/src/litjev/decision.py:75)（`SchemaDecisionEngine`）
- [`src/litjev/decision.py` L67–L72](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zhengxuyu__litjev/src/litjev/decision.py:67)（`concentration`）
- [`src/litjev/slots.py` L1–L85](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zhengxuyu__litjev/src/litjev/slots.py:1)


## 3. openjev-sglang：单 token logprob + Radix 前缀复用

仓库：https://github.com/ekzhang/openjev-sglang

**执行链**：`EvaluationService.evaluate → PromptCompiler.prepare → prefix warmup → gather(question branches) → normalize → answer`。

编译器搜集能被 tokenizer 精确编码成一个 token 的大写字母标签，避免数字 10 以上变为多 token；完整 chat template 只渲染一次，把 shared state 与问题 suffix 分开。每个问题仍作为独立 SGLang request 发送，前缀共享依赖 serving 层缓存。

`SGLangClient.generate` 发往 `/generate`，实际设置 `max_new_tokens=1`、`return_logprob=True`、`token_ids_logprob=label_ids`；warmup 也请求一个占位 token 的 logprob，代码注释解释这是为避开 SGLang 0.5.19 混合请求 bug。warmup token 丢弃，不接到问题后。

因此它不是“整个 HTTP 请求只做一个无输出 forward”：有一次 prefix warmup 和 N 个分支请求，每个返回恰好一个 completion token；`parse_generation` 还验证该计数。最终答案不使用生成文本，而使用候选 logprob 经 `exp((logp-max)/T)` 归一化的概率。

并发由 semaphore、最大 active request 与总 timeout 管理；一个分支失败/取消后清理兄弟任务。usage 累加 warmup 与所有 branch 的 prompt/completion 计数，不等于官方“state 一次计费”的定价语义。confidence 使用 `1−H(p)/log K`。

**后续开发**：最近提交围绕 MMLU-Pro、one-token 提示改进、受限 reasoning 的准确率/延迟比较，以及 eval collector 重构。说明开发者在研究“只读一个位置 logits”的能力边界，而非已公开复刻 Jev 权重。

**代码入口**

- [`src/openjev/prompts.py` L72–L142](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/ekzhang__openjev-sglang/src/openjev/prompts.py:72)（`PromptCompiler`）
- [`src/openjev/service.py` L28–L105](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/ekzhang__openjev-sglang/src/openjev/service.py:28)（`EvaluationService`）
- [`src/openjev/backend.py` L27–L90](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/ekzhang__openjev-sglang/src/openjev/backend.py:27)（`SGLangClient`）
- [`src/openjev/backend.py` L93–L123](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/ekzhang__openjev-sglang/src/openjev/backend.py:93)（`parse_generation`）
- [`src/openjev/scoring.py` L1–L40](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/ekzhang__openjev-sglang/src/openjev/scoring.py:1)


## 4. minojev：候选路径表征 + 集合注意力校正 + 按原语校准

仓库：https://github.com/zeredy879/minojev

每个候选是一个 state/question/candidate path。`fresh` 模式把所有完整 path pad 成 batch，取各行最后有效 hidden state；`reuse` 模式对每个不同 state 先 prefill，再展开 cache 并批量执行 suffix。后者是每个 distinct state 一次 prefix 加一次 suffix forward，不能统一写为所有请求绝对一次 forward。

`DecisionHead` 先 LayerNorm + scalar linear，Choice/Boolean 还经过集合注意力校正：把 hidden state 与 `log(candidate_count)` 拼接，投影到 attention_dim，经过 MultiheadAttention，再用小线性头输出每个候选 delta。它让一个候选的分数能考虑同题其他候选，同时避免固定类别数输出头。Score 做概率加权等级期望。

源码头部注释称 Boolean 可看作 `softmax([0,z])`，但当前 forward 对 BOOLEAN 走的是其 group path logits 的 softmax，并参与集合校正；因此细节应跟随实际实现，不只摘注释。

后训练三种模式：① head：冻结 backbone，预计算 hidden features，只训练头；② lora：适配 backbone 与 head；③ last-layers：只解冻最后若干层和 norm。objective 支持 teacher_ce、gold_ce、brier。head 模式可用低精度 backbone 抽特征，而训练头保持自己的数值路径。

校准按 Choice/Boolean/Score 分别拟合 temperature，在 dev 上最小化目标分布 NLL，存入 checkpoint；服务重新计算 softmax 与 Score 期望。当前 `_fit_one` 在 T=0.1..4 的 64 点 log grid 外加入 1.0。发布 README 的 Qwen3-1.7B head-training 结果与 CLI 默认 Qwen3-0.6B/LoRA 不是一回事，应按 checkpoint 配置区分。

**后续开发**：2026-09-20 的提交在更新 benchmark bundle、计量说明与 playground；数值是作者自报，本次没有重新训练验证。

**代码入口**

- [`src/minojev/model.py` L92–L98](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/model.py:92)（`forward_paths`）
- [`src/minojev/model.py` L100–L135](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/model.py:100)（`forward_reuse`）
- [`src/minojev/heads.py` L43–L104](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/heads.py:43)（`DecisionHead`）
- [`src/minojev/posttrain.py` L73–L97](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/posttrain.py:73)（`build_model`）
- [`src/minojev/posttrain.py` L145–L178](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/posttrain.py:145)（`cache_features`）
- [`src/minojev/calibrate.py` L44–L56](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/calibrate.py:44)（`apply_calibration`）
- [`src/minojev/calibrate.py` L122–L135](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/zeredy879__minojev/src/minojev/calibrate.py:122)（`_fit_one`）


## 5. jeff：GLiFormer 后端与 Jev 兼容服务

仓库：https://github.com/logan-markewich/jeff

`build_groups` 将问题转换成 GLiFormer classification group。Choice 标签由 key/description 合成，Score 由有序 level 合成，Noul 可选择 single、single_named 或 yes_no。默认 `isolate=nouls`：每个 Noul 单独 encoder pass，而同请求 Choice/Score 共享 unit；`all` 才全部隔离。

`Engine.run_batch` 给所有 unit 记录原 request owner，调用 backend.score，再映射回答案。后端分数是独立 sigmoid；归一化方式为 `s_i^(1/T)/Σ s_j^(1/T)`，默认 T=3.2。confidence 为均匀基准归一化的最大概率。

**重要兼容差异**：`decode(Score)` 用 T=1 的 raw normalized scores 计算 score，却用 T=3.2 分布填 `probabilities`。所以默认配置下 `score != Σ i*returned_probabilities[i]`，这是代码中的明确选择。Noul 没有此 Score 期望问题。

服务还含跨请求 batcher、队列上限、可选鉴权和速率限制；README 描述 torch 与 ONNX backend，ONNX 仅替换 encoder，其他部件仍在 PyTorch。input_tokens 计的是自己的 tokenizer/重复 unit；output_tokens 在 engine 中是每题 6 的名义值，不是 decode 实测。

GLiFormer-large-v1 400M 与 Jev 的 reasoning-heavy 能力不能画等号。README 自报其推理/阅读任务落后，也给出 CPU/ONNX 的成本并不总优于托管 Jev；本次保留结果，不独立背书。

**代码入口**

- [`src/jeff/core/groups.py` L17–L41](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/logan-markewich__jeff/src/jeff/core/groups.py:17)（`PromptOptions`）
- [`src/jeff/core/engine.py` L15–L72](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/logan-markewich__jeff/src/jeff/core/engine.py:15)（`Engine`）
- [`src/jeff/core/answers.py` L24–L35](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/logan-markewich__jeff/src/jeff/core/answers.py:24)（`normalize`）
- [`src/jeff/core/answers.py` L47–L75](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/logan-markewich__jeff/src/jeff/core/answers.py:47)（`decode`）
- [`src/jeff/server/batcher.py` L1–L107](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/logan-markewich__jeff/src/jeff/server/batcher.py:1)


## 6. Von：从逐候选 cross-encoder 转到 Option-Marker

仓库：https://github.com/wfzyx/von

新版 `OptionMarkerModel` 将 `question + state + SEP + MASK option1 + MASK option2 ...` 放进单序列，ModernBERT 双向 attention 允许同题选项相互交互。抓取每个 MASK 位置 hidden，再经 Linear → GELU → LayerNorm → Dropout → Linear 变成标量 logits。

训练代码的 `compute_marker_rlcd_loss` 实际是监督 CE 加 `brier_weight * Σ(p-onehot)²`，默认权重 0.5。这是该项目命名为 RLCD 的具体损失；没有证据证明与 TypeSafe 私有训练算法相同。optimizer 对 encoder 和 head 分别用 0.5×与 2.5×主学习率。

**single-pass 的单位**：同一个问题的 K 个选项合成一次 encoder forward；`OptionMarkerBackend.evaluate` 仍 for-loop 遍历 questions，各自调用 evaluate_choice/noul/score。因此不能把多题 API 描述成共享 state 的单 forward。

confidence 使用最高与次高概率差。temperature 从 marker_calibration.json 加载，不应照抄 README 多处不同 T 数值。usage 以字符数/4 估计，不是 tokenizer 实测。

**值得跟进的代码路径**：`_get_model` 找不到 option_marker.pt 时会构造基础 encoder 和新 scorer；在这条分支没有看到加载训练后 scorer 权重。因此采用者需要确认实际 checkpoint 资产，而不是仅因函数能返回分布就认定用了发布模型。这里是静态代码观察，没有执行该分支。

**后续开发**：2026-09-19/20 的提交直接记录新 Option-Marker 架构、训练流水线与 benchmark 更新，是可追踪的实质实现演进。

**代码入口**

- [`src/von/models/option_marker.py` L15–L32](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/wfzyx__von/src/von/models/option_marker.py:15)（`OptionMarkerScorer`）
- [`src/von/models/option_marker.py` L35–L79](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/wfzyx__von/src/von/models/option_marker.py:35)（`OptionMarkerModel`）
- [`src/von/backends/option_marker_backend.py` L59–L88](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/wfzyx__von/src/von/backends/option_marker_backend.py:59)（`_get_model`）
- [`src/von/backends/option_marker_backend.py` L239–L287](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/wfzyx__von/src/von/backends/option_marker_backend.py:239)（`evaluate`）
- [`training/train_option_marker.py` L83–L114](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/wfzyx__von/training/train_option_marker.py:83)（`compute_marker_rlcd_loss`）


## 7. Verdict / OpenJev：ModernBERT + GLiClass，显式 abstention

仓库：https://github.com/Heman10x-NGU/Verdict-open-jev

`DecisionEngine.evaluate` 为每个 query 构造文本和动态标签，组成 batch 一次调用 GLiClass 模型；从每行 logits 截取真实候选数，再可选 temperature calibration、softmax，输出分类/评分/布尔结果。

这里的 single forward 是**多个完整 query 行的 batch**，并非 kev 的 shared state block mask。模型入口默认 `knowledgator/gliclass-modern-base-v2.0`，是否使用作者后训练 checkpoint 由传入路径决定，不能把包默认对象自动算作发布的 RLCD 权重。

设计中有 `INSUFFICIENT_EVIDENCE` 候选。Noul 可计算排除 abstention 后 true/false 的条件概率；Score 也仅在 substantive mass 上求期望。结果包含 `is_abstention`、模型 ID、calibration_status，接口比 Jev 原始 response 更丰富，不能假定完全 drop-in。

校准状态很具体：只有 calibrator.scope 为 `restricted_5_candidate_selection` 且当前 5 候选时标 `calibrated_for_scope`；其他情况是 `unvalidated_scope`。concentration 是归一化负熵。这个分支比 README 的泛化“校准置信度”描述更准确。

最近提交新增 TF-IDF/reference floors 结果及 openjev alias。另有 `Heman10x-NGU/openJev-verdict-2.0` 的检索线索，应视作独立后续仓库，不能自动把旧仓库代码与新仓库成绩合并。

**代码入口**

- [`core/engine_encoder.py` L51–L252](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/Heman10x-NGU__Verdict-open-jev/core/engine_encoder.py:51)（`DecisionEngine`）
- [`core/engine_encoder.py` L37–L48](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/Heman10x-NGU__Verdict-open-jev/core/engine_encoder.py:37)（`_compute_concentration`）
- [`core/calibration.py` L1–L332](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/Heman10x-NGU__Verdict-open-jev/core/calibration.py:1)
- [`scripts/train.py` L1–L436](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/Heman10x-NGU__Verdict-open-jev/scripts/train.py:1)


## 8. poorjev：NLI 成对判断 + 温度拟合 + 经验拒答阈值

仓库：https://github.com/rupeshpoojary9/poorjev

默认 NLI 模型是 `MoritzLaurer/deberta-v3-base-zeroshot-v2.0`。将 state 作为 premise、每个选项/命题作为 hypothesis，对序列分类 logits 做 softmax，读取 entailment 类。Noul 直接使用命题支持度；Choice/Score 在更上层 client 归一化各候选分数。

后端 `batch_size=16,max_length=512`，按 pair 分块 forward。因此“一个 ask、一趟模型”只在 pair 数落在一个 batch 等条件下成立；长文本还会 truncation，不能继承 Jev 的大窗口。

温度校准实际为 `softmax(log(p)/T)`，先粗网格再以 0.05 步长精搜，使标注 gold 的 NLL 最小。`cross_val_calibrate` 默认 5-fold；但少于 k 条时退化为同集拟合再返回，而非 hold-out。

拒答阈值在校准记录上按 confidence 从高到低累积错误，选经验 risk 不超过 target 的最大覆盖点。它是**经验 selective prediction 阈值**；本函数没有给出分布无关 finite-sample conformal risk 保证。所以 README 的“provably calibrated”不能仅凭这个实现成立。ECE 0.170→0.071 只保留为作者在其评测上的报告。

**代码入口**

- [`src/poorjev/backends/local_nli.py` L26–L108](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/rupeshpoojary9__poorjev/src/poorjev/backends/local_nli.py:26)（`LocalNLIBackend`）
- [`src/poorjev/calibration.py` L57–L69](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/rupeshpoojary9__poorjev/src/poorjev/calibration.py:57)（`fit_temperature`）
- [`src/poorjev/calibration.py` L88–L113](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/rupeshpoojary9__poorjev/src/poorjev/calibration.py:88)（`cross_val_calibrate`）
- [`src/poorjev/calibration.py` L126–L148](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/rupeshpoojary9__poorjev/src/poorjev/calibration.py:126)（`fit_abstention_threshold`）


## 9. SemIf：冻结开放模型的选项 readout 与 prefix cache

仓库：https://github.com/TheoLeeCJ/SemIf

`score_shared` 要求所有 row 的 state 完全相同。先编译每个完整 prompt，提取共同 state prefix；代码把 prefix 最后 token 留给 suffix，是为了避免 JSON 拼接边界引起 tokenizer merge 差异。

第一次 forward 只计算 prefix cache；`cache.reorder_cache(zeros(N))` 展开缓存；第二次 forward 处理 padded suffix，只保留各行真实结束位置 logits，然后选 candidate slots 做 softmax。时间细分为 encode、prefill、replicate、suffix_forward。

特别值得保留的是响应中的 `probability_status = conditional option score; uncalibrated as decision confidence`。这是候选条件分数，不宣称官方 RLCD 或天然概率校准。项目还含 direct、serial、MLX 路径与独立 benchmark 脚本，实验比较必须标明用了哪条路径。

**代码入口**

- [`src/semif_phase1/shared.py` L53–L146](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/TheoLeeCJ__SemIf/src/semif_phase1/shared.py:53)（`score_shared`）
- [`src/semif_phase1/shared.py` L13–L36](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/TheoLeeCJ__SemIf/src/semif_phase1/shared.py:13)（`_state_prefix`）
- [`src/semif_phase1/direct.py` L1–L79](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/TheoLeeCJ__SemIf/src/semif_phase1/direct.py:1)


## 10. jevmlx：Apple Silicon 上的约束决策工程

仓库：https://github.com/bnsd55/jevmlx

这里已经是较完整的本地 serving/eval 工程：MLX + mlx-lm，shared prefix cache broadcast，schema 到决策 rows 的编译，候选 trie，多字段约束、分块评分、可选重新评分和校准。

`engine.py` 当前约 3000+ 行，入口 `run_parallel_generation` 不应被理解为一条永远相同的单 forward 路径：模块明确按 cache memory 分块，包含 multi-token trie 与 selective second pass 等辅助路径。是否触发要看 schema、候选编码和内存设置。本次只做模块与部分入口阅读，未逐分支核验整个引擎。

model load 阶段探测 chat template 是否支持 system role，Qwen3 关闭 thinking；不支持 system role 的模型会调整 prompt layout。当前明确要求 macOS/arm64；源码写明 PyTorch/CUDA backend 已移除。不能因为目录里有纯 Python 测试就认为 Linux 上可跑其实际 MLX 推理。

后续阅读重点：`_broadcast_cache`、`_score_rows`、`_prefill`、`run_parallel_generation`，以及 `schema.py`/`trie.py`/`constraints.py`。源码已保存，可继续按具体部署机器深入。

**代码入口**

- [`jevmlx/engine.py` L432–L448](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/bnsd55__jevmlx/jevmlx/engine.py:432)（`_broadcast_cache`）
- [`jevmlx/engine.py` L2402–L2442](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/bnsd55__jevmlx/jevmlx/engine.py:2402)（`_prefill`）
- [`jevmlx/engine.py` L2445–L2684](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/bnsd55__jevmlx/jevmlx/engine.py:2445)（`run_parallel_generation`）


## 11. jev-ultrafast：一次请求并行问操作与各操作的目标

仓库：https://github.com/browser-use/jev-ultrafast

`action_space` 从当前可见 DOM actions 构建有限集合：CLICK、TYPE_TEXT、SELECT 和滚动/等待等 controls，再加 DONE/BLOCKED。`choose` 不串行地“先问操作，再请求目标”，而是一次 HTTP 同时问 operation 与 click_target/type_text_target/select_target。代码只使用被选操作对应的 target head，避免无关 speculative head 触发动作。

state 带 URL/title/text、元素 role/value/checked/selected/expanded 和最近 10 次执行。返回同时保存 operation 与 target 的完整分布，因而可以回看选择错误发生在哪一层。

`Agent.command` 分 predict/act。真正输入前检查 page freshness，先消费 decision 再执行，执行记录先于下一次 observation；连续 3 次非 wait 动作未改变页面则 blocked。此处已有检查属于该上游的浏览器执行边界，本次没有将机制加入当前工作项目。

TYPE_TEXT 交给**另一个生成式模型**产生字段值，默认配置指向 DeepSeek-compatible endpoint，随后由 Browser 执行。Jev 只决定填哪个字段，不写自由文本。截图是观察/记录资产，不意味着 Jev 本身读取截图。

**代码入口**

- [`jev_ultrafast/model.py` L48–L78](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/browser-use__jev-ultrafast/jev_ultrafast/model.py:48)（`action_space`）
- [`jev_ultrafast/model.py` L81–L148](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/browser-use__jev-ultrafast/jev_ultrafast/model.py:81)（`choose`）
- [`jev_ultrafast/model.py` L160–L198](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/browser-use__jev-ultrafast/jev_ultrafast/model.py:160)（`field_text`）
- [`jev_ultrafast/agent.py` L52–L161](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/browser-use__jev-ultrafast/jev_ultrafast/agent.py:52)（`command`）


## 12. jev-pruner：按块判断保留价值，不重写输出

仓库：https://github.com/tamaratran/jev-pruner

`output.ts` 先估计 token；默认超过 10,000 tokens 才进入裁剪。默认按 20 行分块、最多 200 块，单行超过 2000 字符会拆开。二进制和整体结构化材料（JSON、XML、diff、cat/jq/git show 等）走保留路径，避免让残缺文档看起来完整。

每块一个 Noul：是否至少包含一行后续任务需要的内容。state 包含用户任务、命令、历史片段、诊断与结果及文本块。criteria 明确“一行重要即保整块”，不是让模型重新摘要。

请求预算默认 30k、state 预算 25k；历史分段评分的任一 keep vote 都能保留 chunk。keep threshold 默认 0.5。保留原文，删除位置插 omission marker，并给完整输出的恢复路径。后续源码还处理 protected lines、refinement、scoring request 预算及 coverage 不完整时回退。

`jev.ts` 是薄 transport：构建 systemone 请求、检查 answers 对象和 Noul 有限数值。具体保留策略在 output/retention/history，而不是藏在 SDK 里。

**后续开发**：commit/PR 记录显示从 Claude Code 扩展至 Codex，新增 paired log-reading evaluation、interleaved stderr 处理与 retention cohort。与“缩短文本”相比，更应看答题信息是否仍可恢复的实验，而不只比较压缩率。

**代码入口**

- [`src/output.ts` L1–L675](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/tamaratran__jev-pruner/src/output.ts:1)
- [`src/jev.ts` L1–L166](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/tamaratran__jev-pruner/src/jev.ts:1)
- [`src/retention.ts` L1–L56](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/tamaratran__jev-pruner/src/retention.ts:1)


## 13. jev-align：人标注 + GEPA 改 question/rubric

仓库：https://github.com/sutro-sh/jev-align

不是训练 Jev 权重。它把 task specification 当作可优化对象，让用户标注 Jev 不确定的样本，再用 GEPA 反思错误，生成新的 instructions/criteria。

`prediction_ambiguity` 对单概率用 `1−2*abs(p−0.5)`；有 native confidence 用 `1−confidence`；多标签取各标签最大 ambiguity。`select_batch` 默认 5 条，其中 4 条最模糊、1 条随机 exploration，避免只看不确定样本而漏掉自信错误。

`ClassAwareBatchSampler` 在一次 GEPA run 内固定所选 ID，优先近期和类别覆盖；`F1BatchEvaluator` 按 candidate 定义分组批量评估。二元用 F1，多类 macro-F1，多标签 micro-F1，Score 用 fit_score；逐条回传 false positive/false negative、概率和期望标签，让优化器能修改具体错误边界。

这是一条“失败经验改变未来问法”的可读实现路径。生产运行定义是否替换仍要看 session/CLI 的 candidate 接受流程；不能因优化器给出更好训练批次分数就认定已改善未见样本。

**代码入口**

- [`src/jev_align/acquisition.py` L14–L25](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/sutro-sh__jev-align/src/jev_align/acquisition.py:14)（`prediction_ambiguity`）
- [`src/jev_align/acquisition.py` L34–L61](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/sutro-sh__jev-align/src/jev_align/acquisition.py:34)（`select_batch`）
- [`src/jev_align/optimizer.py` L46–L95](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/sutro-sh__jev-align/src/jev_align/optimizer.py:46)（`ClassAwareBatchSampler`）
- [`src/jev_align/optimizer.py` L98–L248](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/sutro-sh__jev-align/src/jev_align/optimizer.py:98)（`F1BatchEvaluator`）
- [`src/jev_align/session.py` L1–L589](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/sutro-sh__jev-align/src/jev_align/session.py:1)


## 14. jev-drone：慢速语义战术层与快速控制层分离

仓库：https://github.com/RomanSlack/jev-drone

本节检查的是 MuJoCo 仿真 `run.py + tactics.py` 路径，不代表所有 tunnel 模式，更不代表实机验证。

源码标明 500Hz 几何控制、50Hz guidance/reflex、15Hz 相机 scene、约 3Hz Jev 战术判断。`decision_needed` 只在近障、扇区阻挡或目标丢失时触发；`Tactician.offer` 把 scene 放进容量 1 的线程队列，控制环不等待 HTTP。

Jev 一次回答三题：maneuver Choice（hold/gap_left/gap_right/climb/brake/reacquire）、risk Score（0..2）、target_truly_lost Noul。state 是相机处理后的扇区距离、目标方位/可见性等结构化描述，再加飞行器能力与任务。不是把图像直接发给 Jev。

代码设 call_hz=3、call_budget=160、stale_after_s=1.5；coarse scene tuple 用于跳过未变化状态。guidance 只有当 source=jev 且未过期才消费建议；climb 还需要可观测上方空间条件；最终反射层控制速度和高度。

一个容易误读的点：confidence 被存进 judgment，但所读 guidance 接受条件没有 confidence 阈值；不要仅凭变量存在就说“高置信才飞”。同时成功请求才增加 calls，故这里 budget 并非所有失败尝试总数上限。上述均为静态阅读，不是飞行效果或安全认证。

**代码入口**

- [`tactics.py` L109–L219](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/RomanSlack__jev-drone/tactics.py:109)（`Tactician`）
- [`tactics.py` L91–L96](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/RomanSlack__jev-drone/tactics.py:91)（`decision_needed`）
- [`tactics.py` L99–L101](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/RomanSlack__jev-drone/tactics.py:99)（`build_state`）
- [`run.py` L60–L234](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/RomanSlack__jev-drone/run.py:60)（`Guidance`）


## 15. jev-reranker：listwise / pointwise / pairwise 与 token 分块

仓库：https://github.com/hotchpotch/jev-reranker

当前 `JevReranker` 已不只是一个 Noul 排序示例：提供三种 mode，默认 listwise。默认并发 listwise=4、其余=20；单 document 长度默认 4000，split state budget 26000、request budget 48000。

`score_listwise` 用 estimate 同时检查 state+最长问题 与整个 request 的预算；超预算按文档长度进行平衡分块。`balanced_chunks` 先放长文档，优先当前总长度小且还有容量的 chunk。provider 仍报 context 超限时，缩小预算递归拆分；如果单个 query/document 都放不下则显式报错。

`reranker.py` 负责 transport、三种评分语义、阈值、排序和 run detail；`_ranking.py` 仅负责 listwise partitioning，不应把分块逻辑当作排序模型本体。块间概率是否可直接比较是实际任务级问题，不能从类型相同推断排序可靠；资料包同时收了 ORDER BY 评测仓库。

原始完整输入、tokenizer、模式、拆块和任务分布会影响结果；这里记录实现，没有运行付费 rerank。

**代码入口**

- [`src/jev_reranker/_ranking.py` L13–L27](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/hotchpotch__jev-reranker/src/jev_reranker/_ranking.py:13)（`balanced_chunks`）
- [`src/jev_reranker/_ranking.py` L30–L103](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/hotchpotch__jev-reranker/src/jev_reranker/_ranking.py:30)（`score_listwise`）
- [`src/jev_reranker/reranker.py` L105–L910](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/hotchpotch__jev-reranker/src/jev_reranker/reranker.py:105)（`JevReranker`）


## 16. pi-jev：将待执行 tool call 转成四个语义判断

仓库：https://github.com/y0usaf/pi-jev

`buildGateState` 将 cwd、tool name、参数摘要、平台和最近用户要求送入模型；长字符串参数被截短，防止完整 edit/write 内容无差别出站，但仍须结合实际截断值判断它看到了什么。

三道 Noul 分别问 destructive、exfiltration、beyond_scope，再用 Score 判断 0..3 的影响等级。`evaluateGate` 对各维分别比较阈值，只要一项满足便 flag；impact 另看 minConfidence。它不是一个“你觉得安全吗”的笼统问题。

**实现边界**：该函数对缺失或类型不匹配的三个 Noul 使用 0；impact 缺失不参与判断。仅从本函数不能宣称“缺字段必拦截”；最终行为还要连同 client 解析与宿主 hook 错误策略看。本资料未将其作为已验证安全控制推荐。

值得学习的是将具体失败案例用于修正 question wording；代码注释给出原措辞把 git 可恢复性当作借口的例子。它是作者的测量记录，不是本次重新测得。

**代码入口**

- [`src/gate.ts` L1–L229](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/y0usaf__pi-jev/src/gate.ts:1)
- [`src/index.ts` L1–L649](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/y0usaf__pi-jev/src/index.ts:1)


## 不同实现的 confidence 不可混用

| 实现 | 读到的公式/语义 |
|---|---|
| 官方 Adapter Choice | `(p_max−1/K)/(1−1/K)` |
| 官方 Adapter Score | 相对众数的距离集中度 |
| LitJev | `(K*Σp²−1)/(K−1)`，Gini 集中度 |
| openjev-sglang、Verdict concentration | `1−H(p)/ln K` |
| jeff | 均匀基准归一化的 p_max |
| Von Option-Marker | top-1 probability − top-2 probability |
| poorjev 校准记录 | temperature 后的 max probability |

例如 p=(0.7,0.2,0.1)：归一化 p_max=0.55，Gini=0.31，top-2 margin=0.5，max probability=0.7。即使模型返回完全相同分布，`confidence>=0.6` 在四种实现里也会得出不同结果。换后端应按任务数据重新判断阈值含义，不能只换 base_url 就沿用决策策略。

## 如何使用这些代码资料

1. 研究独立决策模型：先读 kev 的 encode/mask/head，再读 minojev 的 head-only 与校准，比较模型学习到了什么。
2. 研究零训练 readout：并读 LitJev、SemIf、openjev-sglang，比较 tokenizer 标签、prefix cache 与 forward 次数。
3. 研究应用接入：优先看 jev-ultrafast 的 speculative operation/target 与 jev-align 的问法优化循环。
4. 研究实时具身系统：看 jev-drone 的异步战术层，单独阅读控制与观察；这里未执行其仿真或证明实机适用。
5. 准备真正运行时，从各 repo 的 pyproject/package 与 README 选择环境；本次保存的是选定文本源码，未保留权重、二进制、所有数据集或完整 Git 工作树。
