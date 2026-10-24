"""Compose the existing PAOS Agent and Runtime with a persistent Isaac worker."""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.planning_context import PlanningContextUnavailableError, context_from_task
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import ForgeSkillBindingResolver
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.forge.tool_client import ForgeToolClient
from PhyAgentOS.planning import AdmissionContext
from PhyAgentOS.skill_runtime.integration import ActiveRuntimeRegistry, ActiveSkillRuntime
from pick_place_workflow.perception_binding import BindingRequest, PerceptionBindingAdapter
from pick_place_workflow.persistent_runtime import SQLiteAssignmentArtifactStore
from pick_place_workflow.semantic_task_creation import AsyncQuerySemanticPlanBuilder

from .engine import IsaacSimLabEngine
from .paos_client import build_labutopia_runtime
from .perception_runtime import build_visual_providers
from .profile import LabUtopiaProfile
from .visual_perception import RGBLabelPointInference


class ObservedQueryPort:
    """Retain successful observation receipts used by the semantic plan builder."""

    def __init__(self, client):
        self.client = client
        self.observations = {}

    async def get_tool(self, tool_id):
        return await self.client.get_tool(tool_id)

    async def __call__(self, tool_id, arguments):
        response = await self.client.invoke_query_tool(tool_id, arguments)
        payload = response.get("data", {})
        if tool_id == "scene.observe" and payload.get("status") == "available":
            self.observations[payload["observation_ref"]] = payload
        return payload


class LabPlanningContext:
    """Project simulator revision plus real Query receipts and Coordinator state.

    A plan's original observation identifies the selected object. The subtask
    refreshes that binding before preparing any motion at a newer revision.
    Neither an Agent-authored reference nor an invented scene is admitted.
    """

    def __init__(self, coordinator, engine, queries):
        self.coordinator, self.engine, self.queries = coordinator, engine, queries

    def __call__(self, task_id):
        task = self.coordinator.get_task(task_id)
        revision = self.engine.backend.current_scene_revision()
        if not revision:
            raise PlanningContextUnavailableError("Isaac session has no current scene revision")
        graph = task.active_revision.plan_graph
        observed = {
            reference
            for node in (graph.nodes if graph is not None else ())
            if (reference := node.input_bindings.get("binding", {}).get("observation_ref"))
            in self.queries.observations
        }
        try:
            persisted = context_from_task(task, allow_refresh=True)
        except PlanningContextUnavailableError:
            # A first pending Action has no settled scene yet. Its original
            # Query receipts still identify the selected objects while the
            # existing node executor reconciles that same invocation.
            if task.execution_records and (not observed or any(record.terminal for record in task.execution_records)):
                raise
            persisted = AdmissionContext(scene_revision=revision)
        evidence = set(persisted.evidence_refs) | observed
        settlements = {item.node_id: item.status for item in self.coordinator.effective_node_settlements(task_id)}
        return persisted.model_copy(update={"scene_revision": revision,
                                           "evidence_refs": frozenset(evidence),
                                           "settlements": tuple(settlements.items())})


def environment_guidance(sensor_ref, execute):
    mode = "Simulated motion is authorized." if execute else "Read-only qualification; motion is disabled."
    return f"""Laboratory deployment: persistent Isaac simulation with no liquid or chemistry model.
{mode}
Use forge_task_create semantic_subtasks to bind only the reagent labels and operations requested by the user through Queries.
Categories are reagent_bottle, mixing_vessel and stir_tool. Sensor: {sensor_ref}. max_age_ms: 1000.
Use a label selector only when the user specifies a label; never infer reagent identity from a bottle's fixed scene position.
Create ordered semantic subtasks from the requested workflow using operation="pour" or operation="stir". These semantic operations are executed through the internal PAOS Tools object.pour and tool.stir; do not use the legacy pour_cycle or stir_cycle names in semantic_subtasks.
Pass every requested operation value in that subtask's parameters object: pour requires tilt_rad and hold_s; stir requires radius_m, depth_m, turns, duration_s and direction (cw or ccw).
Do not hard-code a bottle count, operation sequence, or numeric process values. Ask the user for missing required values before creating a manipulation task; do not silently fill them from deployment defaults.
Each subtask includes physical acquire, process and return; do not invent object references or coordinates.
Use semantic_intent with allowed_arms=[franka], coordination_mode=single_arm, a goal and success_criteria.
Set verification mode=off: physical Runtime measurements decide process completion; no model chemistry verdict.
After task creation, use existing planning tools to execute ready nodes. Respect failed or uncertain outcomes.
Report only measured no-liquid manipulation, never transferred volume or chemical mixing quality.
"""


def compose_host(*, profile, workspace, provider, inference, model, sensor_ref, execute=False,
                 execution_timeout_s=1800):
    workspace = Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    artifact_root = workspace / "artifacts" / "labutopia"
    artifact_root.mkdir(parents=True, exist_ok=True)
    engine = IsaacSimLabEngine(profile, observation_artifact_root=artifact_root)
    visual, grasps = build_visual_providers(profile.perception_config_path, engine, artifact_root, inference)
    coordinator = AgentTaskCoordinator(workspace=workspace,
                                       config=ForgeConfig(execution_timeout_s=execution_timeout_s), client=None)
    assignments = SQLiteAssignmentArtifactStore(workspace / "assignment-artifacts.sqlite3")
    bundle = build_labutopia_runtime(
        profile=profile, engine=engine, understanding_provider=visual, grasp_provider=grasps,
        preparation_provider=None, capability_provider=visual, resolve_preparation=None,
        target_resolver=visual, tool_context_provider=lambda _: {"ready": True, "sensor_refs": [sensor_ref]},
        perception_adapter=PerceptionBindingAdapter(None, BindingRequest(
            sensor_refs=(sensor_ref,), source_category="reagent_bottle", destination_category="mixing_vessel", max_age_ms=1000)),
        subtask_context_resolver=coordinator.resolve_subtask_context,
        assignment_store=assignments, observation_artifact_root=artifact_root, allow_live=execute,
    )
    client = ForgeToolClient("http://labutopia.local", transport=bundle.transport, timeout_s=900)
    coordinator.client = client
    active = ActiveSkillRuntime(
        skill_name="labutopia-capabilities", skill_version="1", profile="labutopia-mixture",
        runtime_instance_id=f"labutopia-{uuid4().hex}", gateway_url=client.base_url,
        gateway_identity=None, client=client, invocation_ids=set(), session_ids=set(), task_binding_ids=set())
    registry = ActiveRuntimeRegistry(active)
    coordinator.binding_resolver = ForgeSkillBindingResolver(registry, authorized_tool_ids=frozenset({
        *PerceptionBindingAdapter._QUERY_SPECS, "manipulation.execute_subtask"}))
    coordinator.runtime_invocation_ids = active.invocation_ids
    coordinator.runtime_session_ids = active.session_ids
    coordinator.runtime_task_binding_ids = active.task_binding_ids
    queries = ObservedQueryPort(client)
    loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=workspace, model=model,
                     forge_tool_client=client, forge_task_coordinator=coordinator,
                     semantic_plan_builder=AsyncQuerySemanticPlanBuilder(queries),
                     planning_context_provider=LabPlanningContext(coordinator, engine, queries),
                     turn_timeout_s=1200, max_iterations=40, restrict_to_workspace=True)
    loop.set_long_horizon_controller(loop.build_long_horizon_controller())
    return loop, coordinator, bundle, assignments


async def run_instruction(*, profile, workspace, config_path, instruction, sensor_ref, execute=False, model=None,
                          execution_timeout_s=1800):
    import httpx
    from openai import OpenAI
    from PhyAgentOS.cli.commands import _make_provider
    from PhyAgentOS.config.loader import load_config

    config = load_config(Path(config_path).expanduser())
    model = model or config.agents.defaults.model
    settings = config.get_provider(model)
    key = settings.resolve_api_key(base_dir=Path(config_path).expanduser().parent)
    provider = _make_provider(config, model_override=model)
    rgb_client = OpenAI(api_key=key, base_url=config.get_api_base(model),
                        http_client=httpx.Client(trust_env=False, timeout=180))
    loop, coordinator, bundle, assignments = compose_host(
        profile=profile, workspace=workspace, provider=provider,
        inference=RGBLabelPointInference(rgb_client, model=model), model=model,
        sensor_ref=sensor_ref, execute=execute, execution_timeout_s=execution_timeout_s)
    session_key = f"cli:lab-{uuid4().hex[:12]}"
    # Deployment guidance belongs to the system context, separate from the instruction.
    prompt_builder = loop.context.build_system_prompt
    loop.context.build_system_prompt = lambda *a, **k: prompt_builder(*a, **k) + "\n\n" + environment_guidance(sensor_ref, execute)
    try:
        response = await loop.process_direct(instruction, session_key=session_key)
        outcomes = await loop.wait_for_long_horizon_tasks(session_key)
        tasks = list(coordinator.store.find_by_origin_session_key(session_key))
        report = {"instruction": instruction, "session_key": session_key, "simulated_motion_enabled": execute,
                  "agent_response": response, "controller_outcomes": [asdict(item) for item in outcomes],
                  "tasks": [task.model_dump(mode="json") for task in tasks]}
        Path(workspace, "acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        await loop.close_mcp()
        await coordinator.client.close()
        bundle.client.close()
        bundle.provider.target_resolver.close()
        assignments.close()
        rgb_client.close()
        provider_client = getattr(provider, "_client", None)
        if provider_client is not None:
            await provider_client.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path.home() / ".PhyAgentOS/config.json")
    parser.add_argument("--sensor-ref", default="sensor://tabletop_third_person")
    parser.add_argument("--model")
    parser.add_argument("--execute", action="store_true", help="Enable simulated motion")
    parser.add_argument("--execution-timeout-s", type=float, default=1800,
                        help="Existing Coordinator Action reconciliation budget per composite subtask")
    parser.add_argument("instruction")
    args = parser.parse_args(argv)
    report = asyncio.run(run_instruction(profile=LabUtopiaProfile.from_json(args.profile),
        workspace=args.workspace, config_path=args.config, instruction=args.instruction,
        sensor_ref=args.sensor_ref, execute=args.execute, model=args.model,
        execution_timeout_s=args.execution_timeout_s))
    print(json.dumps({"session_key": report["session_key"],
                      "tasks": [{"task_id": task["task_id"], "status": task["status"]} for task in report["tasks"]]}, ensure_ascii=False))
    return 0 if report["tasks"] and all(task["status"] == "completed" for task in report["tasks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
