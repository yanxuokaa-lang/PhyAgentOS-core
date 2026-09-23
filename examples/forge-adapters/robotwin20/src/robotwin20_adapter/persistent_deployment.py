"""Compose adapter providers for the existing pick-place Skill runtime."""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml
from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeTransport
from pick_place_workflow.grounding import BIND_TOOL_SPEC, TARGET_TOOL_SPEC, TASK_GOAL_TOOL_SPEC
from pick_place_workflow.persistent_runtime import build_persistent_runtime

from .arm_candidates import CompleteRouteSelector
from .grounding import Grounding, GroundingEndpoint, RememberObservation
from .observed_collision import ObservedCollisionPolicy
from .observed_support import SupportEstimationPolicy
from .persistent_action_approval import (
    DEFERRED_EXECUTION_CHECKS,
    DISABLED_ACTION_MODE,
    RUNTIME_MONITORED_ACTION_MODE,
    PersistentSimulationActionApprover,
)
from .persistent_capabilities import PersistentCapabilityProvider
from .persistent_client import PersistentWorkerError, build_persistent_route_readiness
from .persistent_preparation import PersistentPreparationProvider
from .persistent_route_builder import PersistentRouteBuilder
from .prepared_routes import PreparedRoutes
from .route_readiness import RouteReadinessEvaluationAdapter


class PersistentTaskGoalProvider:
    """Read task-definition goals without projecting them as observations."""

    def __init__(self, client: Any, *, goal_source: str = "benchmark_task_definition") -> None:
        self.client = client
        if goal_source not in {"benchmark_task_definition", "observation_owned"}:
            raise ValueError("goal_source must be benchmark_task_definition or observation_owned")
        self.goal_source = goal_source

    def goal(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.goal_source == "observation_owned":
            return {
                "status": "unavailable",
                "motion_authorized": False,
                "error": {
                    "code": "benchmark_goal_disabled",
                    "message": "observation-owned profile does not expose benchmark destinations",
                },
            }
        value = dict(self.client.query("task_goal_facts", request))
        value["goal_source"] = self.goal_source
        return value


class TaskGoalEndpoint:
    def __init__(self, provider: PersistentTaskGoalProvider) -> None:
        self.provider = provider

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.provider.goal(arguments)
        except (KeyError, ValueError, TypeError, OSError, PersistentWorkerError) as exc:
            return {
                "status": "unavailable",
                "motion_authorized": False,
                "error": {"code": "task_goal_unavailable", "message": str(exc)},
            }


@dataclass(frozen=True)
class PersistentDeployment:
    preparation_provider: PersistentPreparationProvider
    capability_provider: PersistentCapabilityProvider
    prepared_routes: PreparedRoutes
    grounding: Grounding | None = None
    task_goal_provider: Any | None = None

    def runtime_arguments(self):
        return {"preparation_provider": self.preparation_provider,
                "capability_provider": self.capability_provider,
                "resolve_preparation": self.prepared_routes}


@dataclass(frozen=True)
class PersistentRuntimeBundle:
    """One adapter-owned Runtime/transport pair for the existing Forge API."""

    deployment: PersistentDeployment
    runtime: CapabilityRuntime
    transport: CapabilityRuntimeTransport

    def client_transport(self) -> CapabilityRuntimeTransport:
        """Return the transport accepted by ``ForgeToolClient``."""
        return self.transport


def build_persistent_runtime_bundle(
    *,
    deployment: PersistentDeployment,
    client: Any,
    understanding_provider: Any,
    grasp_provider: Any,
    tool_context_provider: Callable[[str], dict[str, Any]],
    tool_input_defaults: Mapping[str, Mapping[str, Any]] | None = None,
    gateway_identity: str = "robotwin20-persistent-runtime",
) -> PersistentRuntimeBundle:
    """Compose the persistent providers behind one provider-neutral transport.

    The caller owns the client/world lifetime. This function only registers the
    existing Tool endpoints; it does not reset a world, start an Action, or
    issue motion commands. Action admission remains in the persistent endpoint
    and final user-level success remains Coordinator/Verifier-owned.
    """
    if any(component.client is not client for component in (
        deployment.preparation_provider,
        deployment.capability_provider,
        deployment.prepared_routes,
    )):
        raise ValueError("persistent runtime and deployment must share one worker client")
    runtime = build_persistent_runtime(
        client=client,
        understanding_provider=understanding_provider,
        grasp_provider=grasp_provider,
        preparation_provider=deployment.preparation_provider,
        capability_provider=deployment.capability_provider,
        resolve_preparation=deployment.prepared_routes,
        tool_context_provider=tool_context_provider,
        tool_input_defaults=tool_input_defaults,
        query_decorator=(lambda tool_id, endpoint: RememberObservation(endpoint, deployment.grounding, tool_id)
                         if tool_id in {"scene.observe", "scene.understand"} else endpoint)
        if deployment.grounding is not None else None,
    )
    if deployment.grounding is not None:
        for spec, resolve in ((BIND_TOOL_SPEC, deployment.grounding.bind),
                              (TARGET_TOOL_SPEC, deployment.grounding.target)):
            runtime.register_tool(spec, GroundingEndpoint(resolve),
                                  context_provider=lambda tool_id=spec["tool_id"]: tool_context_provider(tool_id))
    if deployment.task_goal_provider is not None:
        goal_spec = deepcopy(TASK_GOAL_TOOL_SPEC)
        if getattr(deployment.task_goal_provider, "goal_source", None) == "observation_owned":
            goal_spec["planning"]["requires_before_plan"] = False
        runtime.register_tool(
            goal_spec,
            TaskGoalEndpoint(deployment.task_goal_provider),
            context_provider=lambda: tool_context_provider("task.goal"),
        )
    transport = CapabilityRuntimeTransport(runtime, gateway_identity=gateway_identity)
    return PersistentRuntimeBundle(deployment=deployment, runtime=runtime, transport=transport)


def build_persistent_deployment(*, client, artifact_root: Path, scene_source,
                                materializer_command, materializer_arguments,
                                arm_profile_digest: str, materializer_timeout_s=120,
                                preparation_timeout_s=330,
                                route_geometry_source="observed",
                                simulation_action_mode=DISABLED_ACTION_MODE,
                                goal_source="observation_owned",
                                task_name=None,
                                readiness_evaluator=None):
    """Build real adapter components, retaining caller-owned client lifetime.

    The default evaluator only proves no-motion readiness; unavailable contact
    and stop evidence remains unavailable. Deployments may inject an existing
    complete-evidence evaluator, never a fabricated success projection.
    """
    profile_path = Path(materializer_arguments["route-input-profile"])
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if profile["stop_policy"]["failure_recovery"] != "hold_and_reconcile":
        raise ValueError("persistent deployment requires hold_and_reconcile route policy")
    builder = PersistentRouteBuilder(
        client=client, artifact_root=artifact_root, scene_source=scene_source,
        command=materializer_command, materializer_arguments=materializer_arguments,
        timeout_s=materializer_timeout_s,
    )
    grounding = Grounding(client, artifact_root, scene_source,
                          support_policy=SupportEstimationPolicy(**profile.get("observed_support", {})),
                          collision_policy=(ObservedCollisionPolicy(**profile["observed_collision"])
                                            if "observed_collision" in profile else None))
    if route_geometry_source == "observed":
        builder.scene_source = grounding.scene_facts
    elif route_geometry_source == "oracle":
        builder.scene_source = grounding.oracle_scene_facts
    else:
        raise ValueError("route_geometry_source must be observed or oracle")
    if simulation_action_mode not in {
        DISABLED_ACTION_MODE,
        RUNTIME_MONITORED_ACTION_MODE,
    }:
        raise ValueError("simulation_action_mode must be disabled or runtime_monitored")
    if goal_source not in {"benchmark_task_definition", "observation_owned"}:
        raise ValueError("goal_source must be benchmark_task_definition or observation_owned")
    if simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE and route_geometry_source != "oracle":
        raise ValueError("runtime_monitored simulation Actions require oracle route geometry")
    routes = PreparedRoutes(client, artifact_root)
    evaluator = readiness_evaluator if readiness_evaluator is not None else RouteReadinessEvaluationAdapter(
        build_persistent_route_readiness(client))
    deferred_checks = (
        DEFERRED_EXECUTION_CHECKS
        if simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE
        else ()
    )
    approval_issuer = (
        PersistentSimulationActionApprover(
            artifact_root,
            task_name=task_name,
            mode=simulation_action_mode,
        )
        if simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE
        else None
    )
    preparation = PersistentPreparationProvider(
        client=client, route_builder=builder,
        selector=CompleteRouteSelector(
            evaluator,
            builder.arm_profile,
            deferred_checks=deferred_checks,
        ),
        prepared_routes=routes,
        approval_issuer=approval_issuer,
        timeout_s=preparation_timeout_s,
    )
    capabilities = PersistentCapabilityProvider(
        client=client, artifact_root=artifact_root,
        arm_profile=Path(materializer_arguments["arm-planning-profile"]), profile_digest=arm_profile_digest,
    )
    return PersistentDeployment(
        preparation,
        capabilities,
        routes,
        grounding,
        PersistentTaskGoalProvider(client, goal_source=goal_source),
    )
