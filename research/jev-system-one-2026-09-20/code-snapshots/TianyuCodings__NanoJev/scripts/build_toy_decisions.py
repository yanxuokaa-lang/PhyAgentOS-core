#!/usr/bin/env python3
"""构建自写、程序真值的微型决策数据；仅使用 Python 标准库。"""
import argparse
import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path


SPLITS = ("train", "dev", "calibration", "test", "ood")
DEFAULT_COUNTS = dict(zip(SPLITS, (64, 16, 16, 32, 16)))
ROUTES = {
    "billing": ("重复扣款", "a duplicate charge", "扣费、付款与退款问题", "Charges, payments, and refunds"),
    "account": ("忘记账户密码", "a forgotten account password", "账户密码与身份验证", "Passwords and identity checks"),
    "technical": ("软件按钮报错", "a software button error", "软件功能错误与故障", "Software errors and broken features"),
    "shipping": ("包裹未送达", "an undelivered parcel", "包裹运输与投递问题", "Parcel transport and delivery"),
    "documentation": ("询问操作手册位置", "a request for the user manual", "查找说明文档与使用指南", "Finding manuals and usage guides"),
    "privacy": ("要求删除个人资料", "a request to delete personal data", "个人资料删除与隐私请求", "Personal data deletion and privacy"),
}
NEAR_NEGATIVE = {"billing": "shipping", "account": "technical", "technical": "account",
                 "shipping": "billing", "documentation": "technical", "privacy": "account"}
REFUNDS = {
    "none": ("尚未提出退款申请", "no refund was requested"),
    "requested": ("已申请退款，尚未处理", "a refund was requested but not processed"),
    "processing": ("退款正在处理中，尚未完成", "the refund is processing and not complete"),
    "approved": ("退款已批准，但尚未到账", "the refund was approved but not paid"),
    "denied": ("退款申请已拒绝，未付款", "the refund was denied and not paid"),
    "issued": ("退款已到账，处理完成", "the refund was paid and completed"),
}
IMPACTS = [
    ("功能正常，没有使用障碍", "all features work without obstruction"),
    ("次要功能受阻，有替代办法", "a minor feature is blocked with a workaround"),
    ("核心功能受阻，有替代办法", "a core feature is blocked with a workaround"),
    ("服务完全中断，无替代办法", "the entire service is down without a workaround"),
]
SCORE_CRITERIA = {
    "zh": ["功能正常，无使用障碍", "次要功能受阻，有替代办法", "核心功能受阻，有替代办法", "服务完全中断，无替代办法"],
    "en": ["All features work normally", "Minor feature blocked; workaround exists",
           "Core feature blocked; workaround exists", "Entire service down; no workaround"],
}
TEMPLATES = {
    "train": ("工单主诉：{issue}。退款记录：{refund}。使用影响：{impact}。",
              "Ticket topic: {issue}. Refund record: {refund}. Impact: {impact}."),
    "dev": ("客户反馈{issue}；财务状态为{refund}；当前情况是{impact}。",
            "The customer reports {issue}; finance says {refund}; currently {impact}."),
    "calibration": ("核查摘要：主要问题是{issue}。另查得{refund}，且{impact}。",
                    "Review summary: the main issue is {issue}; separately, {refund}, and {impact}."),
    "test": ("请看独立记录——问题：{issue}；退款：{refund}；功能：{impact}。",
             "Independent log — topic: {issue}; refund: {refund}; functionality: {impact}."),
}
QUESTION_PREFIX = {
    "train": ("根据记录，", "Using this record, "),
    "dev": ("请核对当前事实后判断：", "Check the current facts: "),
    "calibration": ("仅依据这份核查摘要，", "Based only on this review, "),
    "test": ("读取上述独立记录并回答：", "Read the independent log and answer: "),
}


def dynamic_candidates(options, positive, hard_negative, size, rng):
    chosen = [positive, hard_negative]
    remaining = [x for x in options if x not in chosen]
    rng.shuffle(remaining)
    chosen.extend(remaining[:size - len(chosen)])
    rng.shuffle(chosen)
    return {key: options[key] for key in chosen}


def support_record(split, index, facts, rng):
    route, refund, severity = facts
    lang = "zh" if index % 2 == 0 else "en"
    li = int(lang == "en")
    state_id = f"support:{route}:{refund}:{severity}"
    state = TEMPLATES[split][li].format(issue=ROUTES[route][li], refund=REFUNDS[refund][li],
                                      impact=IMPACTS[severity][li])
    prefix = QUESTION_PREFIX[split][li]
    options = {key: value[2 + li] for key, value in ROUTES.items()}
    criteria = dynamic_candidates(options, route, NEAR_NEGATIVE[route], 2 + index % 4, rng)
    instructions = (
        ("只按工单主诉选择支持团队；退款记录和功能影响是另外两个字段。",
         "Choose a support team from the main topic only; refund and impact are separate fields."),
        ("退款是否已经实际到账完成？申请、处理中、批准或拒绝均不算到账。",
         "Has the refund actually been paid and completed? Requests, processing, approval, or denial do not count."),
        ("按明确记载的使用影响，选择最匹配的严重程度。",
         "Choose the severity level matching the explicitly recorded impact."),
    )
    return {
        "id": state_id, "state_id": state_id, "family_id": "support_decisions_v1", "split": split,
        "state": state,
        "questions": {
            "route": {"type": "choice", "instructions": prefix + instructions[0][li], "criteria": criteria},
            "completed": {"type": "boolean", "instructions": prefix + instructions[1][li]},
            "severity": {"type": "score", "instructions": prefix + instructions[2][li], "criteria": SCORE_CRITERIA[lang]},
        },
        "gold": {"route": route, "completed": refund == "issued", "severity": severity},
        "metadata": {"source": "self_authored_programmatic", "license": "CC0-1.0",
                     "source_group_id": state_id, "template_id": f"support:{split}:{lang}", "language": lang,
                     "facts": {"main_topic": route, "refund_status": refund, "impact_level": severity}},
    }


def ood_record(index, facts, rng):
    role, status, evidence = facts
    lang = "zh" if index % 2 == 0 else "en"
    li = int(lang == "en")
    role_words = {"staff": ("员工", "employee"), "visitor": ("访客", "visitor")}
    status_words = {
        "requested": ("仅提交申请", "request submitted only"),
        "approved": ("审批通过但尚未启用", "approved but not activated"),
        "pending": ("仍待审批，尚未启用", "approval pending; not activated"),
        "activated": ("访问权限已经启用", "access has been activated"),
    }
    docs = [("没有提交材料", "no documents provided"), ("仅提交身份证明", "identity proof only"),
            ("身份证明和授权函齐全", "identity proof and authorization letter both provided")]
    state_id = f"access:{role}:{status}:{evidence}"
    state = (f"权限档案：身份为{role_words[role][li]}；进度为{status_words[status][li]}；材料为{docs[evidence][li]}。"
             if li == 0 else
             f"Access file: role={role_words[role][li]}; status={status_words[status][li]}; documents={docs[evidence][li]}.")
    action = "deny" if role == "visitor" else ("grant" if evidence == 2 else "request_documents")
    options = {
        "grant": ("符合规则，允许开通", "Eligible; allow activation"),
        "deny": ("身份不符，拒绝开通", "Role ineligible; deny activation"),
        "request_documents": ("材料不足，要求补齐", "Missing evidence; request documents"),
        "billing": ("转交退款处理", "Route to refund handling"),
        "archive": ("不核查规则，直接归档", "Archive without checking the rules"),
    }
    near = "grant" if action != "grant" else "request_documents"
    criteria = dynamic_candidates({k: v[li] for k, v in options.items()}, action, near, 2 + index % 4, rng)
    route_q = (
        "仅按身份和材料决定：访客一律拒绝；员工须身份证明及授权函齐全才允许，否则要求补材料。忽略当前进度。",
        "Decide from role and documents only: deny visitors; allow employees with both identity proof and authorization; otherwise request missing documents. Ignore current status.",
    )
    bool_q = ("访问权限是否已经实际启用？申请或审批通过均不等于启用。",
              "Has access actually been activated? A request or approval does not mean activation.")
    score_q = ("只评估材料完整程度，忽略身份和申请进度。", "Assess document completeness only, ignoring role and request status.")
    levels = (["没有材料", "只有身份证明", "身份证明和授权函齐全"] if li == 0 else
              ["No documents", "Identity proof only", "Identity proof plus authorization"])
    return {
        "id": state_id, "state_id": state_id, "family_id": "access_evidence_ood_v1", "split": "ood",
        "state": state,
        "questions": {
            "route": {"type": "choice", "instructions": route_q[li], "criteria": criteria},
            "completed": {"type": "boolean", "instructions": bool_q[li]},
            "severity": {"type": "score", "instructions": score_q[li], "criteria": levels},
        },
        "gold": {"route": action, "completed": status == "activated", "severity": evidence},
        "metadata": {"source": "self_authored_programmatic", "license": "CC0-1.0",
                     "source_group_id": state_id, "template_id": f"access:ood:{lang}", "language": lang,
                     "facts": {"role": role, "access_status": status, "evidence_level": evidence}},
    }


def build_records(seed=17, counts=None):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    if any(type(counts.get(s)) is not int or counts[s] < 0 for s in SPLITS):
        raise ValueError("split 数量必须是非负整数")
    # 先分配唯一事实组；语言、模板、候选变序都在分区之后生成。
    support_facts = list(itertools.product(ROUTES, REFUNDS, range(len(IMPACTS))))
    random.Random(seed).shuffle(support_facts)
    if sum(counts[s] for s in SPLITS[:-1]) > len(support_facts):
        raise ValueError(f"support 分区总数超过 {len(support_facts)} 个唯一事实组")
    ood_facts = list(itertools.product(("staff", "visitor"), ("requested", "approved", "pending", "activated"), range(3)))
    random.Random(seed + 1).shuffle(ood_facts)
    if counts["ood"] > len(ood_facts):
        raise ValueError(f"OOD 数量超过 {len(ood_facts)} 个唯一事实组")
    records = {}
    offset = 0
    for split_number, split in enumerate(SPLITS[:-1]):
        rng = random.Random(seed + 1000 + split_number)
        selected = support_facts[offset:offset + counts[split]]
        records[split] = [support_record(split, i, facts, rng) for i, facts in enumerate(selected)]
        offset += counts[split]
    records["ood"] = [ood_record(i, facts, random.Random(seed + 2000 + i))
                      for i, facts in enumerate(ood_facts[:counts["ood"]])]
    validate_records(records)
    return records


def validate_records(records):
    seen_ids, seen_groups, templates = set(), {}, {}
    for split, rows in records.items():
        for row in rows:
            if row["id"] in seen_ids:
                raise ValueError("重复的状态 ID")
            seen_ids.add(row["id"])
            group = row["metadata"]["source_group_id"]
            if group in seen_groups and seen_groups[group] != split:
                raise ValueError("事实组跨分区泄漏")
            seen_groups[group] = split
            tid = row["metadata"]["template_id"]
            if tid in templates and templates[tid] != split:
                raise ValueError("模板跨分区泄漏")
            templates[tid] = split
            if row["metadata"]["language"] == "zh" and len(row["state"]) > 100:
                raise ValueError("中文 state 超过 100 字")
            for qid, question in row["questions"].items():
                if set(question) - {"type", "instructions", "criteria"}:
                    raise ValueError("SDK question 内含额外 metadata")
                gold = row["gold"][qid]
                if question["type"] == "boolean":
                    assert type(gold) is bool and "criteria" not in question
                elif question["type"] == "choice":
                    assert 2 <= len(question["criteria"]) <= 5 and gold in question["criteria"]
                else:
                    assert type(gold) is int and 0 <= gold < len(question["criteria"])
                if "criteria" in question:
                    values = question["criteria"].values() if isinstance(question["criteria"], dict) else question["criteria"]
                    assert all(len(value) <= 40 for value in values)


def write_dataset(output_dir, seed=17, counts=None):
    records = build_records(seed, counts)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "openjev-toy-v1", "seed": seed, "source": "self_authored_programmatic",
        "license": "CC0-1.0", "teacher": None,
        "limits": ["仅用于算法通路试验；不是 JeV 能力复现或现实校准证据。",
                   "按唯一事实组合先分区；表述模板不跨分区，但训练与 ID 测试共享规则。",
                   "OOD 仅为一个新权限/证据规则族；不能据此代表一般跨域能力。"],
        "splits": {},
    }
    for split, rows in records.items():
        payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
        (output_dir / f"{split}.jsonl").write_text(payload, encoding="utf-8")
        manifest["splits"][split] = {
            "states": len(rows), "questions": 3 * len(rows),
            "sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "boolean_labels": dict(Counter(str(row["gold"]["completed"]).lower() for row in rows)),
            "choice_k": dict(Counter(len(row["questions"]["route"]["criteria"]) for row in rows)),
            "score_labels": dict(Counter(row["gold"]["severity"] for row in rows)),
            "languages": dict(Counter(row["metadata"]["language"] for row in rows)),
        }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="research/private_toy")
    parser.add_argument("--seed", type=int, default=17)
    for split in SPLITS:
        parser.add_argument(f"--{split}-states", type=int, default=DEFAULT_COUNTS[split])
    args = parser.parse_args()
    counts = {split: getattr(args, f"{split}_states") for split in SPLITS}
    try:
        manifest = write_dataset(args.output_dir, args.seed, counts)
    except (ValueError, AssertionError) as exc:
        parser.error(str(exc) or "生成数据校验失败")
    print(json.dumps({"output_dir": str(Path(args.output_dir)), "splits": manifest["splits"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
