"""Current-contract, selection-only host pairs; never historical/held-out proof.

The only imported execution record is explicitly an offline observation import.
The original context, admission, selection persistence and model loop run intact.
An evaluation executor stops at an admitted selection, not a fake Tool receipt.
"""
from __future__ import annotations

import json
import math
import runpy
import shutil
import sys
from pathlib import Path
from statistics import mean
from time import monotonic

import httpx
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from PhyAgentOS.agent.context import ContextBuilder
from PhyAgentOS.agent.decision_calibration import ProbeAPI
from PhyAgentOS.agent.decision_evaluation import (
    _create_run_dir,
    _git_commit,
    _write_json,
    run_decision_evaluation,
)
from PhyAgentOS.agent.decision_provider import JEVHTTPDecisionProvider
from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.planning_loop import AgentLoopNodeExecutor, NodeContextProvider
from PhyAgentOS.agent.skills import SkillsLoader
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.agent.tools.registry import ToolRegistry
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import DecisionPointConfig, ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.task import AgentTaskCoordinator, ToolExecutionRecord
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanNode,
    canonical_sha256,
    plan_graph_digest,
    project_tool_spec,
)
from PhyAgentOS.providers.base import GenerationSettings
from PhyAgentOS.providers.custom_provider import CustomProvider
from PhyAgentOS.verification.contracts import TaskVerificationContract


class ReplayCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1)
    expected_entity_refs: list[str] | None = None


class HostReplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_dir: Path
    output_root: Path
    jev: ProbeAPI
    system2: ProbeAPI
    cases: list[ReplayCase] = Field(min_length=1, max_length=6)
    decision_timeout_s: float = Field(default=60, ge=1, le=120)
    jev_timeout_s: float = Field(default=10, gt=0, le=30)
    fallback_reserve_s: float = Field(default=15, gt=0, le=60)
    max_iterations: int = Field(default=3, ge=1, le=6)
    max_requests: int = Field(default=18, ge=2, le=60)
    max_tokens: int = Field(default=2048, ge=256, le=8192)


def summarize_pairs(results: list[dict]) -> dict:
    """Include failed/abstaining arms in latency; never call small-N p95 proof."""
    summary = {"arm_count": len(results), "actual_substitutions": 0, "latency": {}}
    for arm in ("system2", "jev"):
        rows = [item for item in results if item["arm"] == arm]
        elapsed = sorted(item["elapsed_ms"] for item in rows)
        if elapsed:
            summary["latency"][arm] = {"n": len(elapsed), "mean_ms": mean(elapsed),
                "p95_ms": elapsed[math.ceil(.95 * len(elapsed)) - 1], "estimator": "nearest_rank"}
        if arm == "jev":
            summary["actual_substitutions"] = sum(
                row.get("matches_authored_expectation") is True and row["system2_calls"] == 0
                and row["jev_calls"] == 1 and row["status"] == "selected" for row in rows)
    return summary


def sanitized_understanding(snapshot_dir: Path) -> dict:
    """Keep decision facts/ambiguities; exclude images, paths and free-form logs."""
    raw = json.loads((snapshot_dir / "understanding.json").read_text())
    facts = {key: raw[key] for key in (
        "status", "observation_ref", "scene_revision", "calibration_ref",
    )}
    facts["entities"] = [
        {key: entity[key] for key in ("entity_ref", "category", "confidence") if key in entity}
        for entity in raw.get("entities", [])
    ]
    facts["ambiguities"] = [
        {key: item[key] for key in ("code", "entity_refs") if key in item}
        for item in raw.get("ambiguities", [])
    ]
    return facts


def build_host(workspace: Path, facts: dict, spec: dict, goal: str):
    """Import a declared offline source into the existing transactional store."""
    workspace.mkdir(parents=True, exist_ok=False)
    coordinator = AgentTaskCoordinator(workspace=workspace, config=ForgeConfig(), client=None)
    source_ref = "tool:offline-understanding"
    node = PlanNode(node_id="bind-current", obligation_id="select-target",
                    capability="scene.bind", required_evidence=(source_ref,))
    payload = dict(task_id="task-host-replay", revision_id="revision-host-replay",
                   graph_digest="0" * 64, planner_decision_digest=canonical_sha256(goal),
                   policy_snapshot_digest=canonical_sha256(spec),
                   nodes=[node.model_dump(mode="json")])
    payload["graph_digest"] = plan_graph_digest(payload)
    task = coordinator.create_task(
        task_description=goal, verification=TaskVerificationContract(mode="off"),
        plan_graph=PlanGraph.model_validate(payload),
        plan_graph_ref="artifact://offline-replay/current-contract-plan",
    )

    def import_source(current):
        current.runtime_binding = RuntimeBinding(
            binding_id="offline-replay", runtime_profile="offline-selection-only",
            runtime_instance_id="no-runtime", gateway_url="offline://no-gateway",
        )
        current.active_revision.runtime_binding_id = current.runtime_binding.binding_id
        current.tool_bindings = [BoundToolSpec(
            tool_id="scene.bind", semantics="query", spec_sha256=canonical_sha256(spec),
            ready_at_binding=False, input_schema=spec["input_schema"],
            planning_policy=project_tool_spec(spec),
        )]
        current.active_revision.discovery_evidence_refs = (source_ref,)
        current.active_revision.execution_records.append(ToolExecutionRecord(
            record_id="offline-understanding", revision_id=task.active_revision_id,
            tool_id="scene.understand", semantics="query", caller_id="offline-source-import",
            runtime_binding_id=current.runtime_binding.binding_id,
            status="succeeded", response={"data": facts}, evidence_refs=[source_ref],
        ))

    coordinator.store.update(task.task_id, import_source, event_type="offline_replay_source_import",
                             payload={"historical_replay": False, "motion_authorized": False})

    def admission(_task_id):
        return AdmissionContext(scene_revision=facts["scene_revision"], evidence_refs=(source_ref,))

    context = NodeContextProvider(
        coordinator.get_task, coordinator.effective_node_settlements,
        coordinator.effective_planning_execution_records, coordinator.effective_node_settlements,
    ).build(task.task_id, node.node_id, scene_revision=facts["scene_revision"])
    return coordinator, context, admission


class SelectionReachedError(Exception):
    """Evaluation stop after real durable admission, never execution success."""


class SelectionExecutor(AgentLoopNodeExecutor):
    async def _resume_node(self, context):
        if self._node_records(context):
            raise RuntimeError("selection replay must not contain node executions")
        if self._pending_selection(context) is not None:
            raise SelectionReachedError
        return None


class SelectionLoop(AgentLoop):
    async def run_node_turn(self, **kwargs):
        return await super().run_node_turn(**kwargs, selection_only=True)


class ReplayContext(ContextBuilder):
    """Original host prompt, without personal skills or local filesystem names."""
    def __init__(self, workspace, **kwargs):
        super().__init__(workspace, **kwargs)
        self.skills = SkillsLoader(workspace, builtin_skills_dir=workspace / "skills",
                                   installed_skills_dir=workspace / "skills")

    def build_messages(self, *args, **kwargs):
        messages = super().build_messages(*args, **kwargs)
        serialized = json.dumps(messages, ensure_ascii=False)
        serialized = serialized.replace(str(self.workspace.resolve()), "/offline/workspace")
        serialized = serialized.replace(str(Path.home()), "/redacted-home")
        return json.loads(serialized)


class RequestRecorder:
    """Count actual HTTP attempts, including failures; never persist headers/keys."""
    def __init__(self, root: Path, max_requests: int):
        self.root, self.max_requests = root, max_requests
        self.records: list[dict] = []
        self.arm = ""

    async def request(self, request):
        if len(self.records) >= self.max_requests:
            raise RuntimeError("host replay request budget exhausted")
        body = json.loads(request.content)
        record = {"arm": self.arm, "request": body, "status": "pending",
                  "started": monotonic()}
        self.records.append(record)
        request.extensions["replay_record"] = record
        self.save()

    async def response(self, response):
        record = response.request.extensions["replay_record"]
        await response.aread()
        record.update(status=response.status_code, elapsed_ms=(monotonic()-record["started"])*1000)
        try:
            record["response"] = response.json()
        except ValueError:
            record["response"] = {"non_json": True}
        self.save()

    def save(self):
        _write_json(self.root / "requests.json", self.records)

    def finish_pending(self):
        for record in self.records:
            if record["status"] == "pending":
                record.update(status="no_response", elapsed_ms=(monotonic()-record["started"])*1000)
        self.save()


async def run_arm(root, facts, spec, case, config, system2, jev, arm):
    started = monotonic()
    result = {"arm": arm, "status": "interrupted", "motion_authorized": False}
    coordinator = loop = context = None
    try:
        coordinator, context, admission = build_host(root / "workspace", facts, spec, case.goal)
        loop = SelectionLoop(
            bus=MessageBus(), provider=system2, workspace=root / "workspace",
            model=config.system2.model, max_iterations=config.max_iterations,
            turn_timeout_s=config.decision_timeout_s, restrict_to_workspace=True,
            forge_task_coordinator=coordinator, planning_context_provider=admission,
            decision_provider=jev,
            query_decision_config=DecisionPointConfig(
                mode="active" if arm == "jev" else "off", endpoint=config.jev.endpoint,
                model=config.jev.model, timeout_cap_s=config.jev_timeout_s,
                fallback_reserve_s=config.fallback_reserve_s,
                acceptance_policy_ref="artifact://offline-replay/development-only",
            ),
        )
        # No runtime or general-purpose tools can be called from this evaluator.
        loop.tools = ToolRegistry()
        loop.context = ReplayContext(root / "workspace",
                                     forge_context_provider=coordinator.capabilities_summary,
                                     evolution_enabled=True)
        loop.tools.register(ForgePlanSelectTool(coordinator, lambda: loop._planning_dispatch))
        loop.activate_planning_task(context.task_id)
        prepared = loop._projected_query_decision(context)
        _write_json(root / "context.json", context.model_dump(mode="json"))
        _write_json(root / "candidates.json", [] if prepared is None else [
            {"candidate_id": item.candidate_id, "description": item.description,
             "arguments": item.arguments} for item in prepared[1]
        ])
        await SelectionExecutor(loop, coordinator, max_node_turn_continuations=0)(context)
        result["status"] = "no_selection"
    except SelectionReachedError:
        result["status"] = "selected"
    except Exception as exc:
        result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
    finally:
        result["elapsed_ms"] = (monotonic() - started) * 1000
        if coordinator is not None and context is not None:
            result["selection"] = coordinator.pending_planning_selection(
                context.task_id, context.node_id, scene_revision=context.scene_revision)
            result["node_execution_count"] = len(coordinator.planning_node_execution_records(
                context.task_id, context.revision_id, context.node_id))
            selected = result["selection"]
            result["matches_authored_expectation"] = (
                selected is not None and selected["arguments"].get("entity_refs") == case.expected_entity_refs
                if case.expected_entity_refs is not None else None
            )
            _write_json(root / "task.json", coordinator.get_task(context.task_id).model_dump(mode="json"))
        _write_json(root / "result.json", result)
    return result


async def run_host_replay(config: HostReplayConfig, *, repo_root: Path, config_path: Path) -> Path:
    root = _create_run_dir(config.output_root)
    report = {"status": "interrupted", "active_eligible": False,
              "evidence_scope": "current_contract_selection_only_development_replay",
              "independent_held_out": False, "independent_review": False,
              "code_commit": _git_commit(repo_root), "python_version": sys.version,
              "config_path": str(config_path), "seed": None, "checkpoint": None,
              "source_snapshot": str(config.snapshot_dir), "results": []}
    recorder = RequestRecorder(root, config.max_requests)
    log_sink = logger.add(root / "host.log", filter="PhyAgentOS.agent.loop", encoding="utf-8")
    try:
        _write_json(root / "config.json", config.model_dump(mode="json"))
        shutil.copyfile(__file__, root / "runner_source.py")
        shutil.copyfile(repo_root / "PhyAgentOS/agent/loop.py", root / "loop_source.py")
        shutil.copyfile(repo_root / "PhyAgentOS/agent/decision_provider.py", root / "decision_provider_source.py")
        _write_json(root / "development-only-policy.json", {
            "purpose": "exercise isolated acceptance path; not production acceptance evidence",
            "production_active_authorized": False, "motion_authorized": False,
        })
        facts = sanitized_understanding(config.snapshot_dir)
        spec = runpy.run_path(str(repo_root / "examples/forge-skills/pick-place-workflow/src/pick_place_workflow/grounding.py"))["BIND_TOOL_SPEC"]
        _write_json(root / "sanitized_facts.json", facts)
        _write_json(root / "binding_spec.json", spec)
        jev_key, system2_key = config.jev.key(config_path.parent), config.system2.key(config_path.parent)
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                     event_hooks={"request": [recorder.request], "response": [recorder.response]}) as client:
            jev = JEVHTTPDecisionProvider(client=client, api_key=jev_key, api_format="systemone")
            system2 = CustomProvider(api_key=system2_key, api_base=config.system2.endpoint.rsplit("/chat/completions", 1)[0],
                                     default_model=config.system2.model)
            await system2._client.close()
            system2._client = AsyncOpenAI(api_key=system2_key, base_url=config.system2.endpoint.rsplit("/chat/completions", 1)[0],
                                         http_client=client, max_retries=0)
            system2.generation = GenerationSettings(max_tokens=config.max_tokens, temperature=0,
                                                    request_timeout_s=config.decision_timeout_s)
            for index, case in enumerate(config.cases):
                for arm in (("system2", "jev") if index % 2 == 0 else ("jev", "system2")):
                    arm_root = root / f"case-{index}" / arm
                    arm_root.mkdir(parents=True)
                    recorder.arm = f"case-{index}/{arm}"
                    offset = len(recorder.records)
                    result = await run_arm(arm_root, facts, spec, case, config, system2, jev, arm)
                    recorder.finish_pending()
                    records = recorder.records[offset:]
                    result.update(case_index=index, request_count=len(records),
                                  system2_calls=sum("messages" in item["request"] for item in records),
                                  jev_calls=sum("questions" in item["request"] for item in records))
                    report["results"].append(result)
                    _write_json(arm_root / "result.json", result)
                    _write_json(root / "report.json", report)
            report["status"] = "completed"
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__, error=str(exc))
    finally:
        recorder.finish_pending()
        report["metrics"] = summarize_pairs(report["results"])
        _write_json(root / "report.json", report)
        logger.remove(log_sink)
    return root


def evaluate_host_run(root: Path, *, repo_root: Path):
    """Export recorded host pairs to the existing evaluator as calibration only."""
    report = json.loads((root / "report.json").read_text())
    config = HostReplayConfig.model_validate_json((root / "config.json").read_text())
    requests = json.loads((root / "requests.json").read_text())
    decisions = [json.loads(line.split("Agent decision ", 1)[1])
                 for line in (root / "host.log").read_text().splitlines() if "Agent decision " in line]
    if report["status"] != "completed" or len(decisions) != len(config.cases):
        raise ValueError("evaluation requires complete pairs and one actual host decision per case")
    cases, records = [], []
    for index, case in enumerate(config.cases):
        arms = {row["arm"]: row for row in report["results"] if row["case_index"] == index}
        if set(arms) != {"jev", "system2"}:
            raise ValueError("missing paired arm")
        candidates = json.loads((root / f"case-{index}/jev/candidates.json").read_text())
        other = json.loads((root / f"case-{index}/system2/candidates.json").read_text())
        if candidates != other:
            raise ValueError("paired host candidates differ")
        contexts = [json.loads((root / f"case-{index}/{arm}/context.json").read_text())
                    for arm in ("jev", "system2")]
        if contexts[0] != contexts[1]:
            raise ValueError("paired host contexts differ")
        expected = next((row["candidate_id"] for row in candidates
                         if row["arguments"].get("entity_refs") == case.expected_entity_refs), None)
        if case.expected_entity_refs is not None and expected is None:
            raise ValueError("authored target missing from host candidates; do not fabricate coverage")
        ref = str(root / f"case-{index}/jev/context.json")
        case_id = f"host-case-{index}"
        cases.append(dict(case_id=case_id, split="calibration", family_id="single-observation-family",
                          categories=["multi_entity" if expected else "no_applicable_option"],
                          decision_input_ref=ref, goal=case.goal, facts={"source": "sanitized_facts.json"},
                          candidates=[{key: row[key] for key in ("candidate_id", "description")} for row in candidates],
                          expected_selected_id=expected, must_escalate=case.expected_entity_refs is None))
        observation = decisions[index]
        outcome = observation["outcome"]
        provider_outcome = {"selected": "selected", "stale": "selected", "admission_rejected": "selected",
                            "abstained": "escalate", "timeout": "timeout"}.get(outcome, "unavailable")
        host_outcome = {"selected": "selected", "abstained": "escalated", "stale": "stale",
                        "admission_rejected": "admission_rejected"}.get(outcome, "unavailable")
        baseline_versions = {item.get("response", {}).get("model") for item in requests
                             if item["arm"] == f"case-{index}/system2"}
        baseline_versions.discard(None)
        records.append(dict(case_id=case_id, decision_input_ref=ref,
            provider="jev_systemone", requested_model=config.jev.model,
            model_version=observation["model_version"], system2_provider="original_agent_loop_custom_provider",
            system2_model=config.system2.model,
            system2_model_version=next(iter(baseline_versions)) if len(baseline_versions) == 1 else None,
            provider_outcome=provider_outcome,
            selected_id=observation["selected_candidate_id"] if provider_outcome == "selected" else None,
            host_outcome=host_outcome, decision_trace_ref=observation["decision_trace_ref"] if host_outcome == "selected" else None,
            system2_invoked=arms["jev"]["system2_calls"] > 0,
            decision_total_elapsed_ms=arms["jev"]["elapsed_ms"],
            system2_only_elapsed_ms=arms["system2"]["elapsed_ms"]))
    export = _create_run_dir(root / "evaluation-inputs")
    _write_json(export / "dataset.json", dict(version="jev_decision_evaluation_dataset_v1",
        name="current-contract-host-calibration", dataset_version=root.name,
        sampling_plan_ref=str(root / "config.json"), labeling_protocol_ref="authored-goal-to-observed-category",
        labeler_id="codex-same-author", reviewer_id="codex-same-author", planned_held_out_cases=0, cases=cases))
    _write_json(export / "measurements.json", dict(version="jev_decision_measurements_v1",
                                                   evidence_mode="measured", records=records))
    _write_json(export / "config.json", dict(version="jev_decision_evaluation_config_v1",
        dataset="dataset.json", measurements="measurements.json", output_root=str(root / "evaluation"),
        decision_point="query_input_selection", splits=["calibration"]))
    return run_decision_evaluation(config_path=export / "config.json", repo_root=repo_root)
