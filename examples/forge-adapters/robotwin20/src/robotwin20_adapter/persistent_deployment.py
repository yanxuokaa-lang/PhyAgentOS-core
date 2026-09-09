"""Compose adapter providers for the existing pick-place Skill runtime."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from .arm_candidates import CompleteRouteSelector
from .persistent_capabilities import PersistentCapabilityProvider
from .persistent_client import build_persistent_route_readiness
from .persistent_preparation import PersistentPreparationProvider
from .persistent_route_builder import PersistentRouteBuilder
from .prepared_routes import PreparedRoutes
from .route_readiness import RouteReadinessEvaluationAdapter


@dataclass(frozen=True)
class PersistentDeployment:
    preparation_provider: PersistentPreparationProvider
    capability_provider: PersistentCapabilityProvider
    prepared_routes: PreparedRoutes

    def runtime_arguments(self):
        return {"preparation_provider": self.preparation_provider,
                "capability_provider": self.capability_provider,
                "resolve_preparation": self.prepared_routes}


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
    return PersistentDeployment(preparation, capabilities, routes)
