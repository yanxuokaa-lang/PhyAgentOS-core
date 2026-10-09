"""Create the fixed synthetic v1 dataset used by the probe.

The source cases below are deliberately small and reviewable. Evaluation families
are distinct from development families and never cross a split.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def state(status: str, task: str | None, goal: str | None, pending: str | None, **caps: bool) -> dict[str, Any]:
    return {
        "has_current_task": status != "none",
        "task_ref": f"synthetic:task:{task}" if task else None,
        "task_status": status,
        "task_goal_summary": goal,
        "pending_clarification": {"present": pending is not None, "question_summary": pending},
        "capabilities": {name: bool(caps.get(name, False)) for name in ("read_status", "pause", "resume", "stop")},
    }


EXEC = state("executing", "0001", "整理桌面物品", None, read_status=True, pause=True, stop=True)
PAUSED = state("paused", "0002", "整理桌面物品", None, read_status=True, resume=True, stop=True)
WAITING = state("waiting_for_user", "0003", "整理桌面物品", "选择收纳区域", read_status=True, stop=True)
TERMINAL = state("terminal", "0004", "整理桌面物品", None, read_status=True)
NONE = state("none", None, None, None)


def case(case_id: str, split: str, message: str, context: list[dict[str, str]], current: dict[str, Any], intent: str, route: str, ops: list[str], reason: str, *tags: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family_id": case_id[:-1] if case_id.startswith("e") else case_id,
        "split": split,
        "message": message,
        "recent_turns": context,
        "capability_state": current,
        "gold_intent": intent,
        "gold_route": route,
        "gold_control_operations": ops,
        "gold_reason": reason,
        "tags": list(tags),
        "annotation_status": "adjudicated",
        "source_kind": "synthetic",
    }


def development() -> list[dict[str, Any]]:
    return [
        case("d01", "development", "现在做到哪一步了？", [], EXEC, "status_query", "status_read", [], "当前任务可读状态", "status"),
        case("d02", "development", "刚才的整理结果是什么？", [], TERMINAL, "status_query", "status_read", [], "终态任务仍可查询", "terminal"),
        case("d03", "development", "现在有任务吗？", [], NONE, "status_query", "system2", [], "没有当前任务对象", "no_task"),
        case("d04", "development", "暂停一下。", [], EXEC, "task_control", "task_control", ["pause"], "pause capability 可用", "control"),
        case("d05", "development", "继续刚才的任务。", [], PAUSED, "task_control", "task_control", ["resume"], "resume capability 可用", "control"),
        case("d06", "development", "停止当前整理。", [], EXEC, "task_control", "task_control", ["stop"], "stop capability 可用", "control"),
        case("d07", "development", "恢复当前任务。", [], NONE, "task_control", "system2", ["resume"], "对象和能力缺失", "control", "no_task"),
        case("d08", "development", "红色那个。", [{"role": "assistant", "text": "选择红色还是蓝色？"}], WAITING, "clarification_answer", "clarification_reply", [], "回答待澄清问题", "clarification"),
        case("d09", "development", "红色那个是什么意思？", [], NONE, "mixed_or_unclear", "system2", [], "无待回答问题", "unclear"),
        case("d10", "development", "不要停，查一下进度。", [], EXEC, "status_query", "status_read", [], "否定 stop，正向查询状态", "negation", "status"),
        case("d11", "development", "文档里的“停止任务”是什么意思？", [], EXEC, "analysis", "system2", [], "引用操作词并请求解释", "quotation", "analysis"),
        case("d12", "development", "把这些物品分类放好。", [], EXEC, "new_task", "system2", [], "提出新的执行目标", "new_task"),
        case("d13", "development", "分析一下怎样分类更合理。", [], EXEC, "analysis", "system2", [], "请求分析而非执行", "analysis"),
        case("d14", "development", "你好，今天怎么样？", [], NONE, "conversation", "conversation", [], "简单对话", "conversation"),
        case("d15", "development", "继续。", [], NONE, "mixed_or_unclear", "system2", [], "无任务时指代不足", "unclear"),
        case("d16", "development", "停止任务并分析失败原因。", [], EXEC, "mixed_or_unclear", "system2", ["stop"], "控制与分析两个正向要求", "mixed", "control"),
        case("d17", "development", "选蓝色。", [{"role": "assistant", "text": "请选择红色或蓝色。"}], WAITING, "clarification_answer", "clarification_reply", [], "回答待澄清问题", "clarification"),
        case("d18", "development", "任务完成了吗？", [], TERMINAL, "status_query", "status_read", [], "可查询终态结果", "terminal", "status"),
        case("d19", "development", "不要暂停，请继续整理。", [], EXEC, "new_task", "system2", [], "否定 pause 与新执行要求，不作控制命令", "negation", "new_task"),
        case("d20", "development", "谢谢。", [], NONE, "conversation", "conversation", [], "简单对话", "conversation"),
    ]


def evaluation() -> list[dict[str, Any]]:
    specs = [
        ("状态到哪一步了？", EXEC, "status_query", "status_read", [], "查询执行中状态", ("status",)),
        ("现在进度如何？", EXEC, "status_query", "status_read", [], "查询执行中状态", ("status",)),
        ("整理结束后的结果能看吗？", TERMINAL, "status_query", "status_read", [], "查询终态结果", ("terminal", "status")),
        ("任务已经完成了吗？", TERMINAL, "status_query", "status_read", [], "查询终态结果", ("terminal", "status")),
        ("当前有没有正在处理的任务？", NONE, "status_query", "system2", [], "没有当前任务对象", ("no_task", "status")),
        ("帮我看看任务状态。", NONE, "status_query", "system2", [], "没有任务可绑定", ("no_task", "status")),
        ("先暂停整理。", EXEC, "task_control", "task_control", ["pause"], "pause capability 可用", ("control",)),
        ("请暂停当前任务。", EXEC, "task_control", "task_control", ["pause"], "pause capability 可用", ("control",)),
        ("继续处理刚才的任务。", PAUSED, "task_control", "task_control", ["resume"], "resume capability 可用", ("control",)),
        ("把暂停的任务恢复。", PAUSED, "task_control", "task_control", ["resume"], "resume capability 可用", ("control",)),
        ("停止当前整理工作。", EXEC, "task_control", "task_control", ["stop"], "stop capability 可用", ("control",)),
        ("请停止任务。", EXEC, "task_control", "task_control", ["stop"], "stop capability 可用", ("control",)),
        ("恢复任务，但现在没有任务。", NONE, "task_control", "system2", ["resume"], "resume 对象不可用", ("control", "no_task")),
        ("暂停一下当前任务。", NONE, "task_control", "system2", ["pause"], "pause 对象不可用", ("control", "no_task")),
        ("不要停止，告诉我进度。", EXEC, "status_query", "status_read", [], "否定 stop，查询状态", ("negation", "status")),
        ("不要暂停，当前到哪了？", EXEC, "status_query", "status_read", [], "否定 pause，查询状态", ("negation", "status")),
        ("“暂停”这个词在说明书里怎么理解？", EXEC, "analysis", "system2", [], "引用控制词并解释", ("quotation", "analysis")),
        ("文档说的恢复任务是指什么？", PAUSED, "analysis", "system2", [], "讨论文档概念", ("quotation", "analysis")),
        ("蓝色的那个。", [{"role": "assistant", "text": "选红色还是蓝色？"}], "clarification_answer", "clarification_reply", [], "回答待澄清问题", ("clarification",)),
        ("选第二个。", [{"role": "assistant", "text": "请选择两个收纳区域。"}], "clarification_answer", "clarification_reply", [], "回答待澄清问题", ("clarification",)),
    ]
    rows: list[dict[str, Any]] = []
    for index, (message, current, intent, route, ops, reason, tags) in enumerate(specs, 1):
        context = current if isinstance(current, list) else []
        actual_state = WAITING if isinstance(current, list) else current
        rows.append(case(f"e{index:02d}a", "evaluation", message, context, actual_state, intent, route, ops, reason, *tags))
        rows.append(case(f"e{index:02d}b", "evaluation", message.replace("。", "！"), context, actual_state, intent, route, ops, reason, *tags, "paraphrase"))
        rows.append(case(f"e{index:02d}c", "evaluation", message.replace("？", "呢？").replace("。", "吧。"), context, actual_state, intent, route, ops, reason, *tags, "paraphrase"))
    return rows


def build() -> list[dict[str, Any]]:
    rows = development() + evaluation()
    assert len(rows) == 80
    return rows


def main() -> None:
    target = Path(__file__).with_name("samples.jsonl")
    target.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in build()) + "\n", encoding="utf-8")
    print(f"wrote {len(build())} samples to {target}")


if __name__ == "__main__":
    main()
