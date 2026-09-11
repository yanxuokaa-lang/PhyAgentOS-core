"""Compose adapter providers for the existing pick-place Skill runtime."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml
from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeTransport
from pick_place_workflow.persistent_runtime import build_persistent_runtime

from .arm_candidates import CompleteRouteSelector
from .persistent_capabilities import PersistentCapabilityProvider
from .persistent_client import build_persistent_route_readiness
from .persistent_preparation import PersistentPreparationProvider
from .persistent_route_builder import PersistentRouteBuilder
from .prepared_routes import PreparedRoutes
from .route_readiness import RouteReadinessEvaluationAdapter
from .target_layout import LAYOUT_TOOL_SPEC, ObservedLayout, RememberUnderstanding


@dataclass(frozen=True)
class PersistentDeployment:
    preparation_provider: PersistentPreparationProvider
    capability_provider: PersistentCapabilityProvider
    prepared_routes: PreparedRoutes
    layout: ObservedLayout | None = None

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
        query_decorator=(lambda tool_id, endpoint: RememberUnderstanding(endpoint, deployment.layout)
                         if tool_id in {"scene.observe", "scene.understand"} else endpoint)
        if deployment.layout is not None else None,
    )
    if deployment.layout is not None:
        runtime.register_tool(LAYOUT_TOOL_SPEC, deployment.layout,
                              context_provider=lambda: tool_context_provider("manipulation.layout"))
    transport = CapabilityRuntimeTransport(runtime, gateway_identity=gateway_identity)
    return PersistentRuntimeBundle(deployment=deployment, runtime=runtime, transport=transport)


def build_persistent_deployment(*, client, artifact_root: Path, scene_source,
                                materializer_command, materializer_arguments,
                                arm_profile_digest: str, materializer_timeout_s=120,
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
    layout = ObservedLayout(client, artifact_root, scene_source)
    builder.scene_source = layout.scene_facts
    routes = PreparedRoutes(client, artifact_root)
    evaluator = readiness_evaluator if readiness_evaluator is not None else RouteReadinessEvaluationAdapter(
        build_persistent_route_readiness(client))
    preparation = PersistentPreparationProvider(
        client=client, route_builder=builder,
        selector=CompleteRouteSelector(evaluator, builder.arm_profile), prepared_routes=routes,
    )
    capabilities = PersistentCapabilityProvider(
        client=client, artifact_root=artifact_root,
        arm_profile=Path(materializer_arguments["arm-planning-profile"]), profile_digest=arm_profile_digest,
    )
    return PersistentDeployment(preparation, capabilities, routes, layout)
