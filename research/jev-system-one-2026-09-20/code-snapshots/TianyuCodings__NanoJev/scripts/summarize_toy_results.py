#!/usr/bin/env python3
"""Build the compact report from frozen evaluator outputs; no model calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'research/toy_results'
ARMS = [
    ('Base 原生单步选项', 'base_teacher_native_baseline'),
    ('Instruct 原生单步选项', 'instruct_teacher_native_baseline'),
    ('Base + 参考分布监督', 'base_teacher_predictions'),
    ('Instruct + 参考分布监督', 'instruct_teacher_predictions'),
    ('Base + 程序 gold', 'base_gold_predictions'),
]


def main():
    rows, calibration_rows, all_metrics = [], [], {}
    for label, stem in ARMS:
        d = json.loads((RESULTS / f'{stem}_metrics.json').read_text())
        all_metrics[stem] = d
        for split in ['test', 'ood']:
            r = d['raw'][split]
            g, f = r['student_gold']['overall'], r['teacher_fidelity_raw']
            rows.append(dict(model=label, artifact=stem, split=split,
                             **{key:g[key] for key in ['accuracy','nll','brier','ece']},
                             tv=f['tv'], kl=f['forward_kl_teacher_student'],
                             accuracy_state_bootstrap_ci=r['student_state_cluster_ci']['intervals']['accuracy']))
        if stem.endswith('_predictions'):
            t = d['calibration']
            calibration_rows.append(dict(model=label, temperature=t['temperature'], boundary=t['at_grid_boundary'],
                **{f'{split}_nll_raw':d['raw'][split]['student_gold']['overall']['nll'] for split in ['test','ood']},
                **{f'{split}_nll_calibrated':d['calibrated'][split]['student_gold']['overall']['nll'] for split in ['test','ood']}))
    teacher = all_metrics['base_teacher_predictions']['raw']
    for split in ['test','ood']:
        g = teacher[split]['teacher_gold']['overall']
        rows.append(dict(model='Jev 教师', artifact='teacher', split=split,
                         **{key:g[key] for key in ['accuracy','nll','brier','ece']},tv=0,kl=0))
    summary = dict(dataset=dict(states=144,questions=432,train_states=64,dev_states=16,
                               calibration_states=16,test_states=32,ood_states=16,seed=17),
                   raw_metrics=rows,calibration=calibration_rows,
                   teacher_precision='two-decimal identity rounded proxy; all 432 targets retained')
    (RESULTS/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    md = [
        '# OpenJev toy：已经运行的完整实验', '',
        '2026-09-17。数据生成、Jev 标注、三个学生训练对照、独立留出集评估和本地 checkpoint 推理入口均已实现。'
        '这是 144 个自写状态的通路实验，不是完整 Jev 能力复现。详细算法与扩大方案见 [实施计划](implementation_plan_zh.md)。', '',
        '## 数据、模型与训练', '',
        '- 64 train / 16 dev / 16 calibration / 32 test / 16 OOD states，各 3 题，共 432 题。中英文各半；Choice K=2–5；OOD 为新权限/证据规则族。',
        '- 程序产生事实与 gold，Jev 只看 state 与 questions，不看 gold。432 个 teacher 向量全部和为 1、全部保留，argmax 全部符合 gold。train 的 Choice/Score 都是 one-hot，teacher/gold 训练差异直接来自 Boolean softness。',
        '- Qwen3-0.6B-Base / Qwen3-0.6B，全参 + 动态候选头；Choice 无位置集合注意力，Score 独立等级，Boolean 单路径。相同 seed=17、数据顺序、训练预算；未做多 seed 确证。',
        '- 每臂 12 步只训头 + 120 步全参，每步 12 题；FP32 参数/Adam 状态 + BF16 autocast。teacher 分支按 dev teacher CE 选 checkpoint，gold 分支按 dev gold NLL；没有使用 test 选择 checkpoint。',
        '- Base teacher / Instruct teacher 的 best step 都是 36；Base gold 为 132。运行中另有两步 smoke，不参与成绩比较。',
        '- 原生基线是完整题目下的合法 A/B/C 等单 token logits 条件化概率，不是生成长答案，也不假定这些分数天然已校准。', '',
        '## 同规则留出集：96 道题、32 个状态', '',
        '| 模型 | Accuracy ↑ | NLL ↓ | Brier ↓ | ECE ↓ | 对 Jev TV ↓ | 对 Jev KL ↓ |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for r in rows:
        if r['split']=='test':
            md.append(f"| {r['model']} | {r['accuracy']:.2%} | {r['nll']:.4f} | {r['brier']:.4f} | {r['ece']:.4f} | {r['tv']:.4f} | {r['kl']:.4f} |")
    md += ['', '这些是原始未温度缩放的概率。KL 方向为 `KL(Jev rounded proxy || student)`，TV 为半个 L1；'
           'Brier 按类别求和，ECE 为 10 个等宽区间的 top-label ECE。教师一致性与真值质量是不同维度。', '',
           '## 新规则 OOD：48 道题、16 个状态', '',
           '| 模型 | Accuracy ↑ | NLL ↓ | Brier ↓ | 对 Jev TV ↓ | 对 Jev KL ↓ |',
           '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['split']=='ood':
            md.append(f"| {r['model']} | {r['accuracy']:.2%} | {r['nll']:.4f} | {r['brier']:.4f} | {r['tv']:.4f} | {r['kl']:.4f} |")
    md += ['', 'Instruct 参考分布监督的 dev teacher KL=0.1294，Base 参考分布监督为0.1886，因此 Instruct 是后续扩展的合理起点；'
           '这仍是小样本、单 seed、单主要训练规则族的发现，不能概括为所有决策任务上的优胜。'
           'Instruct 的 OOD accuracy 按 state 聚类 bootstrap 95% 区间约为 [77.1%,93.8%]；'
           'ID 全对时经验 bootstrap 退化成 [100%,100%]，不代表总体准确率已被证明为100%。', '',
           '## 校准实验没有被隐藏', '',
           '只在独立 calibration 的48题上选共享温度，固定搜索区间[.25,4]。没有按 test 或 OOD 改温度。', '',
           '| 模型 | T | test NLL 原始→校准 | OOD NLL 原始→校准 |',
           '|---|---:|---:|---:|']
    for r in calibration_rows:
        suffix='（搜索边界）' if r['boundary'] else ''
        md.append(f"| {r['model']} | {r['temperature']:.4f}{suffix} | {r['test_nll_raw']:.4f} → {r['test_nll_calibrated']:.4f} | {r['ood_nll_raw']:.4f} → {r['ood_nll_calibrated']:.4f} |")
    md += ['', '**反例很明确：** Instruct 的 T=.25 让 ID 更集中，但 OOD NLL 从0.508升到1.055。'
           '不能自动把这个温度作为跨域默认。CLI默认T=1，使用其他温度必须明确传入。'
           'Base gold 的真实标签分数更好，但对 Jev KL 比 Instruct 参考分布监督更高，也说明“更像老师”和“更符合这批真值”不是同一个优化目标。', '',
           '## 追加诊断对下一阶段的影响', '',
           '训练结束后另做40道解析概率题及8次硬币对照，未用于模型选择。Jev在50%事件上Choice报heads .89–.95，'
           '同state的Noul报.48–.49；70%事件上分别为.99–1和.69。见 [原语概率语义对照](probability_semantics_zh.md)。'
           '这使独立概率真值与跨原语一致性成为后续数据的必要组成，不能只优化teacher fidelity。', '',
           '冻结学生也跑完同一40题：平均对解析reference的TV=.3521，按K=2/5/20/64/255为.0824/.1478/.3314/.5141/.6846。'
           'K与state长度同时增长，规则族和符号标签也不同，不能将退化单独归因于K。'
           '这表明动态维度输出已实现，而大候选、新机制上的分布恢复仍需要数据和容量实验。'
           '见 [学生追加诊断](student_distribution_probe_brief_zh.md)。这些指标不是实际事件频率上的总体校准误差。', '',
           '## 并行与结构验证', '',
           '所有学生前向都展开全部完整候选路径，一次 backbone forward 处理多个 state/question；autoregressive decode steps=0。'
           '当前学生后端仍重复计算前缀，没有把共享树优化当作已部署能力。', '',
           '另用训练后的 Instruct checkpoint 实测 K=2/5/20/64/255：346 条候选路径在一次 backbone forward 中输出五个对应维度的完整分布，'
           '概率和误差小于2e-7，FP32峰值显存约3.33GB。见 [动态候选验证](dynamic_candidates_check.json)。'
           '这是结构与接口验证，不是大K准确率或校准证明。', '',
           '真实 tiny Qwen 的树/展开 FP32 检查通过：最大叶表示差4.77e-7、最大参数梯度差6.26e-7，'
           '错误mask和position负对照均被检出。BF16梯度相对L2差约0.623%，如实记录为数值差异。'
           '见 [Qwen数值检查](qwen_tree_check_zh.md)。训练后混批/置换与时延见 [专门报告](trained_invariance_timing_zh.md)。'
           '已训练 Base 学生在BF16逐题与8-state混批间最大概率差0.01508，超过预设诊断容差；FP32降至4.46e-6。'
           '该失败记录保留，推理入口提供明确的fp32/bf16选择。固定短输入8state/24题的BF16 p50=84.72ms，约283题/秒。', '',
           '独立推理验收也已通过：不读取teacher/gold，只加载本地checkpoint，两种精度都在一次forward返回2states/6questions/15paths的结果；'
           '见 [FP32输出](toy_results/inference_example_fp32.json) 与 [BF16输出](toy_results/inference_example_bf16.json)。', '',
           '## 可复现产物与执行限制', '',
           '- 数据：[生成器](../scripts/build_toy_decisions.py)、[Jev标注器](../scripts/label_toy_decisions.mjs)、[teacher审计](toy_teacher_audit_zh.md)。',
           '- 学生：[训练](../scripts/train_toy_decisions.py)、[独立批量推理](../scripts/predict_toy_decisions.py)、[无teacher推理输入](toy_inference_example.json)。',
           '- 评测：[评估器](../scripts/evaluate_toy_decisions.py)、[本报告生成器](../scripts/summarize_toy_results.py)、[精确汇总JSON](toy_results/summary.json)。',
           '- 逐类型、逐family、可靠性分箱、温度、state聚类CI保存在 `research/toy_results/*_metrics.json`；原始teacher响应和逐题预测留在忽略目录。',
           '- 服务器工作目录：`capyubara-0:/home/rwang/openjev_codex_20260917`，权重分别在 `runs/{base_teacher,instruct_teacher,base_gold}/best.safetensors`；tokenizer、backbone config、revision与训练log同目录。',
           '- 每臂峰值torch allocated约17.2GB，分别使用GPU0/1/2。下载/初始化以外，含阶段内dev检查、保存与最终评测的计时约29/28/47秒（按Base teacher/Instruct teacher/Base gold顺序）；不是完整端到端开发耗时。',
           '- 环境Python3.14.4、torch2.14.0+cu130、transformers5.17.0。宿主缺Python.h，显式撤销该torch版本的native Triton overrides，回退ATen；未安装系统包。该内部兼容函数不承诺跨torch版本稳定。',
           '- 首次环境smoke与Instruct原生基线分别遇到缺headers、聊天模板返回结构问题；日志保留，修复后重跑相同配置，未依据test重调训练。',
           '- 本批144个API请求实际$0.003219762；本轮两轮Fable讨论CLI标价$3.138348，不能把CLI标价当作Vercel扣费。', '',
           '**尚未完成的验证：** 多规则族规模化数据、高K/长state质量、集合交互收益消融、reranker/更大模型/多seed对照、共享稀疏kernel加速和RL训练。'
           '这些已有实施方案，但不能由本次toy结果代替。后续应优先补查询分布与真实不确定性，再判断RL是否带来额外收益。', '']
    (ROOT/'research/toy_experiment_report_zh.md').write_text('\n'.join(md))
    print(json.dumps({'summary':str(RESULTS/'summary.json'),'rows':len(rows)},ensure_ascii=False))


if __name__=='__main__': main()
