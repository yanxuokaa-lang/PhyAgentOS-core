"""PAOS lifecycle adapters for LabUtopia cycle execution.

The module deliberately keeps scene execution in :mod:`isaacsim_lab.engine`.
It only supplies the async client/provider shape consumed by the existing PAOS
complete-cycle endpoint.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import Event, RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from .engine import IsaacSimLabEngine
from .profile import LabUtopiaProfile


class LabUtopiaPAOSClientError(RuntimeError):
    """The LabUtopia client cannot safely start or observe a cycle."""


class LabUtopiaCycleProvider:
    """Own no-motion cycle preparation and task-owned assignment projection."""

    def __init__(self, engine: Any, *, target_resolver: Any | None = None):
        self.engine = engine
        self.target_resolver = target_resolver
        self._prepared: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def cycle_capability(self, operation: str) -> dict[str, Any]:
        declaration = getattr(self.engine, "cycle_capability", None)
        if not callable(declaration):
            return {"operation": operation}
        value = declaration(operation)
        return dict(value) if isinstance(value, Mapping) else {"operation": operation}

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Prepare one immutable request without starting simulator motion."""

        operation = arguments.get("operation") if isinstance(arguments, Mapping) else None
        if operation not in {"pour_cycle", "stir_cycle"}:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": "labutopia_cycle_not_supported"}
        request = deepcopy(dict(arguments))
        binding = request.get("binding")
        if binding is not None:
            if self.target_resolver is None:
                return {"status": "unavailable", "motion_authorized": False,
                        "error": "perception_target_resolver_unavailable"}
            try:
                from pick_place_workflow.manipulation_target import resolve_manipulation_target

                profile = getattr(self.engine, "profile", None)
                process_type = getattr(profile, "configured_process_type", None)
                if process_type not in {"pour", "stir"}:
                    raise LabUtopiaPAOSClientError("target resolution requires a supported process type")
                request["manipulation_target"] = resolve_manipulation_target(
                    self.target_resolver, binding, request, process_type=process_type
                )
            except Exception as exc:
                return {"status": "invalid", "motion_authorized": False,
                        "error": f"perception_target_resolution_failed:{type(exc).__name__}"}
        try:
            prepare = getattr(self.engine, "prepare_cycle", None)
            if not callable(prepare):
                raise LabUtopiaPAOSClientError("engine does not expose prepare_cycle")
            result = prepare(request)
        except Exception as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": f"labutopia_preparation_failed:{type(exc).__name__}"}
        if not isinstance(result, Mapping) or result.get("status") != "available":
            error = result.get("error", "labutopia_preparation_unavailable") if isinstance(result, Mapping) else "labutopia_preparation_unavailable"
            return {"status": "unavailable", "motion_authorized": False, "error": str(error)}
        prepared = result.get("arguments")
        if not isinstance(prepared, Mapping):
            return {"status": "unavailable", "motion_authorized": False,
                    "error": "labutopia_preparation_missing_arguments"}
        preparation_ref = f"preparation://labutopia/{uuid4().hex}"
        assignment_ref = f"artifact://labutopia/assignments/{uuid4().hex}"
        value = deepcopy(dict(prepared))
        value.update(preparation_ref=preparation_ref, assignment_ref=assignment_ref)
        with self._lock:
            self._prepared[preparation_ref] = deepcopy(value)
        return {"status": "available", "motion_authorized": False,
                "entity_ref": value["entity_ref"], "arguments": value,
                "provider": "labutopia_isaacsim"}

    def prepare(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Prepare the standard PAOS manipulation route from one measured binding.

        The generic endpoint supplies the binding and trusted intent.  This
        provider resolves the opaque references into adapter-private execution
        data and requires the engine to return the typed assignment/route
        evidence needed by acquire and place.  A legacy cycle-only engine is
        deliberately unavailable on this path instead of fabricating an
        assignment.
        """
        if not isinstance(request, Mapping):
            return {"status": "invalid", "provider_available": False,
                    "error": "standard_preparation_request_must_be_object"}
        binding = request.get("perception_binding")
        process_type = request.get("process_type")
        if not isinstance(binding, Mapping) or process_type not in {"pour", "stir", "relocate"}:
            return {"status": "invalid", "provider_available": False,
                    "error": "standard_preparation_requires_perception_binding_and_process_type"}
        if self.target_resolver is None:
            return {"status": "unavailable", "provider_available": False,
                    "error": "perception_target_resolver_unavailable"}
        try:
            from pick_place_workflow.manipulation_target import resolve_manipulation_target

            target_request = {
                key: request[key]
                for key in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref")
                if key in request
            }
            if isinstance(request.get("candidate_ref"), str):
                target_request["candidate_ref"] = request["candidate_ref"]
            target = resolve_manipulation_target(
                self.target_resolver, binding, target_request,
                process_type=process_type,
            )
        except Exception as exc:
            return {"status": "invalid", "provider_available": False,
                    "error": f"perception_target_resolution_failed:{type(exc).__name__}"}
        engine_prepare = getattr(self.engine, "prepare_manipulation", None)
        if not callable(engine_prepare):
            return {"status": "unavailable", "provider_available": False,
                    "error": "standard_manipulation_preparation_unavailable"}
        engine_request = deepcopy(dict(request))
        engine_request["manipulation_target"] = target
        try:
            result = engine_prepare(engine_request)
        except Exception as exc:
            return {"status": "unavailable", "provider_available": False,
                    "error": f"labutopia_preparation_failed:{type(exc).__name__}"}
        if not isinstance(result, Mapping):
            return {"status": "unavailable", "provider_available": False,
                    "error": "labutopia_preparation_returned_non_object"}
        if result.get("status") not in {"available", "succeeded"}:
            return {"status": str(result.get("status", "unavailable")),
                    "provider_available": False,
                    "error": str(result.get("error", "labutopia_preparation_unavailable"))}
        value = deepcopy(dict(result))
        value.pop("status", None)
        value.pop("motion_authorized", None)
        value["provider_available"] = True
        value.setdefault("destination_ref", request.get("destination_ref"))
        return value

    def resolve(self, operation: str, arguments: Mapping[str, Any], *, task_id: str | None = None) -> dict[str, Any]:
        """Resolve a prepared request and bind its assignment to the caller task."""

        if operation not in {"pour_cycle", "stir_cycle"}:
            raise LabUtopiaPAOSClientError("unsupported LabUtopia cycle operation")
        request = deepcopy(dict(arguments))
        preparation_ref = request.get("preparation_ref")
        with self._lock:
            expected = self._prepared.get(preparation_ref)
        if expected is None or expected != request:
            raise LabUtopiaPAOSClientError("cycle preparation is unknown or changed")
        if not isinstance(task_id, str) or not task_id:
            raise LabUtopiaPAOSClientError("cycle resolver requires the PAOS task id")
        request["assignment"] = {
            "task_id": task_id,
            "assignment_ref": request["assignment_ref"],
        }
        return request


class LabUtopiaActionDriver:
    """Non-blocking PAOS driver around one engine future."""

    def __init__(self, future: Future, cancel: Event):
        self._future = future
        self._cancel = cancel

    def poll(self) -> Mapping[str, Any] | None:
        if not self._future.done():
            return None
        try:
            result = self._future.result()
        except Exception as exc:
            return {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": True,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
            }
        if not isinstance(result, Mapping):
            return {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": True,
                "failure_owner": "isaacsim_adapter",
                "failure_code": "non_mapping_engine_result",
            }
        return dict(result)

    def cancel(self) -> None:
        self._cancel.set()

    def stop(self) -> None:
        self.cancel()


class LabUtopiaCycleClient:
    """Expose ``start/poll/cancel/stop`` without owning PAOS possession state."""

    def __init__(
        self,
        engine: Any,
        *,
        allow_live: bool = False,
        max_workers: int = 1,
        preparation_provider: LabUtopiaCycleProvider | None = None,
        assignment_store: Any | None = None,
        owns_assignment_store: bool = False,
    ):
        if isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")
        self.engine = engine
        self.allow_live = bool(allow_live)
        self._preparation_provider = preparation_provider or LabUtopiaCycleProvider(engine)
        self._assignment_store = assignment_store
        self._owns_assignment_store = bool(owns_assignment_store)
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="labutopia-paos")
        self._closed = False
        self._lock = RLock()

    def cycle_capability(self, operation: str) -> dict[str, Any]:
        declaration = getattr(self.engine, "cycle_capability", None)
        if not callable(declaration):
            return {"operation": operation, "dry_run": True}
        value = declaration(operation)
        result = dict(value) if isinstance(value, Mapping) else {"operation": operation}
        if not self.allow_live:
            result.update({
                "preparation": False,
                "execution": False,
                "feedback": False,
                "return": False,
                "dry_run": True,
                "motion_authorized": False,
            })
        return result

    @property
    def observation_ready(self) -> bool:
        return bool(getattr(self.engine, "observation_ready", False))

    def capture(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        observe = getattr(self.engine, "observe", None)
        if not callable(observe):
            return None
        result = observe(deepcopy(dict(request)))
        if not isinstance(result, Mapping) or result.get("status") != "available":
            return None
        return result

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._preparation_provider.prepare_cycle(arguments)

    def start(self, operation: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]):
        if not self.allow_live:
            raise LabUtopiaPAOSClientError("live LabUtopia execution is disabled")
        if not operation or not invocation_id:
            raise LabUtopiaPAOSClientError("cycle invocation identity is required")
        with self._lock:
            if self._closed:
                raise LabUtopiaPAOSClientError("LabUtopia client is closed")
        cancel = Event()
        phase_executor = getattr(self.engine, "execute_phase", None)
        if operation in {"acquire", "pour", "place"}:
            if not callable(phase_executor):
                raise LabUtopiaPAOSClientError(
                    f"phase-level execution is unavailable for {operation}"
                )
            future = self._pool.submit(
                phase_executor, operation, deepcopy(dict(arguments)), cancel,
                invocation_id=invocation_id, owner=owner,
            )
        else:
            if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
                raise LabUtopiaPAOSClientError(f"unsupported LabUtopia action operation: {operation}")
            future = self._pool.submit(
                self.engine.execute_cycle,
                operation,
                deepcopy(dict(arguments)),
                cancel,
                invocation_id=invocation_id,
            )
        return LabUtopiaActionDriver(future, cancel)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._pool.shutdown(wait=True, cancel_futures=True)
        close = getattr(self.engine, "close", None)
        try:
            if callable(close):
                close()
        finally:
            if self._owns_assignment_store and self._assignment_store is not None:
                store_close = getattr(self._assignment_store, "close", None)
                if callable(store_close):
                    store_close()


@dataclass(frozen=True)
class LabUtopiaPAOSRuntime:
    """Runtime composition returned by :func:`build_labutopia_runtime`."""

    runtime: Any
    transport: Any
    engine: Any
    provider: LabUtopiaCycleProvider
    client: LabUtopiaCycleClient
    perception_adapter: Any | None = None


def build_labutopia_runtime(
    *,
    profile: LabUtopiaProfile,
    understanding_provider: Any,
    grasp_provider: Any,
    preparation_provider: Any,
    capability_provider: Any,
    observation_source: Any | None = None,
    resolve_preparation: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
    tool_context_provider: Callable[[str], dict[str, Any]],
    allow_live: bool = False,
    engine: Any | None = None,
    gateway_identity: str = "labutopia-paos-runtime",
    possession: Any | None = None,
    perception_adapter: Any | None = None,
    target_resolver: Any | None = None,
    subtask_context_resolver: Callable[[str], Mapping[str, Any]] | None = None,
    assignment_store: Any | None = None,
    understanding_artifact_resolver: Any | None = None,
    understanding_inference: Any | None = None,
    understanding_inference_registry: Any | None = None,
    understanding_inference_id: str | None = None,
    understanding_inference_configuration: Mapping[str, Any] | None = None,
    observation_artifact_root: str | Path | None = None,
) -> LabUtopiaPAOSRuntime:
    """Compose LabUtopia behind PAOS without owning perception orchestration.

    ``perception_adapter`` is the provider-neutral PAOS adapter.  LabUtopia
    only supplies its observation/understanding/grasp/preparation providers;
    when the complete chain is absent, the Agent-facing subtask Tool is not
    registered. A deployment may provide ``understanding_artifact_resolver``
    and either a direct inference or registry selection instead of a
    pre-composed understanding provider. These are passed to the generic PAOS runtime;
    storage ownership and model selection remain outside this adapter.  When
    using the default Isaac engine, ``observation_artifact_root`` is passed to
    its worker and can also back the generic local resolver.  A supplied engine
    remains responsible for writing artifacts to the configured root.
    """

    from PhyAgentOS.forge.capability_runtime import CapabilityRuntimeTransport
    from pick_place_workflow.persistent_runtime import (
        StoredAssignmentResolver,
        build_persistent_runtime,
        register_subtask_tool,
    )

    resolved_artifact_root = (
        Path(observation_artifact_root).expanduser().resolve()
        if observation_artifact_root is not None
        else None
    )
    if (
        understanding_provider is None
        and (
            understanding_inference is not None
            or (understanding_inference_registry is not None and understanding_inference_id is not None)
        )
        and understanding_artifact_resolver is None
    ):
        if resolved_artifact_root is None:
            raise ValueError(
                "observation_artifact_root is required when composing local artifact understanding"
            )
        from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver

        resolved_artifact_root.mkdir(parents=True, exist_ok=True)
        understanding_artifact_resolver = LocalFilesystemArtifactResolver(
            {"labutopia": resolved_artifact_root}
        )
    selected_engine = engine or IsaacSimLabEngine(
        profile, observation_artifact_root=resolved_artifact_root
    )
    owns_assignment_store = assignment_store is None
    if assignment_store is None:
        from pick_place_workflow.persistent_runtime import SQLiteAssignmentArtifactStore

        assignment_db = profile.lab_root / "outputs" / "paos" / "assignment-artifacts.sqlite3"
        assignment_db.parent.mkdir(parents=True, exist_ok=True)
        assignment_store = SQLiteAssignmentArtifactStore(assignment_db)
    provider = LabUtopiaCycleProvider(selected_engine, target_resolver=target_resolver)
    held_route_resolver = provider.resolve
    if assignment_store is not None:
        route_validator = (
            resolve_preparation
            if callable(getattr(resolve_preparation, "resolve_stored", None))
            else None
        )
        held_route_resolver = StoredAssignmentResolver(
            assignment_store, route_validator=route_validator
        )
    # A measured target resolver opts the standard PAOS preparation Query into
    # the LabUtopia provider.  Without it, the caller-supplied provider remains
    # the generic readiness implementation and legacy cycle compatibility is
    # unchanged.
    selected_preparation_provider = (
        provider
        if target_resolver is not None and callable(getattr(provider, "prepare", None))
        else preparation_provider
    )
    client = LabUtopiaCycleClient(
        selected_engine,
        allow_live=allow_live,
        preparation_provider=provider,
        assignment_store=assignment_store,
        owns_assignment_store=owns_assignment_store,
    )
    runtime = build_persistent_runtime(
        client=client,
        understanding_provider=understanding_provider,
        understanding_artifact_resolver=understanding_artifact_resolver,
        understanding_inference=understanding_inference,
        understanding_inference_registry=understanding_inference_registry,
        understanding_inference_id=understanding_inference_id,
        understanding_inference_configuration=understanding_inference_configuration,
        grasp_provider=grasp_provider,
        preparation_provider=selected_preparation_provider,
        capability_provider=capability_provider,
        observation_source=observation_source,
        resolve_preparation=None if assignment_store is not None else resolve_preparation,
        tool_context_provider=tool_context_provider,
        possession=possession,
        held_preparation_provider=provider,
        resolve_held_preparation=held_route_resolver,
        register_legacy_actions=False,
        register_legacy_held_operations=False,
        register_internal_subtask_tools=True,
        register_legacy_cycles=False,
        assignment_store=assignment_store,
    )
    bound_adapter = None
    observation_provider = observation_source if observation_source is not None else client
    understanding_ready = callable(getattr(understanding_provider, "understand", None)) or (
        understanding_artifact_resolver is not None
        and (
            understanding_inference is not None
            or (understanding_inference_registry is not None and understanding_inference_id is not None)
        )
    )
    query_providers_ready = understanding_ready and all(
        callable(getattr(provider, method, None))
        for provider, method in (
            (grasp_provider, "propose"),
            (capability_provider, "describe"),
            (selected_preparation_provider, "prepare"),
        )
    )
    observation_provider_ready = (
        callable(getattr(observation_provider, "capture", None))
        or callable(getattr(observation_provider, "query", None))
    )
    if (
        perception_adapter is not None
        and getattr(perception_adapter, "ready", False)
        and query_providers_ready
        and observation_provider_ready
    ):
        with_query_invoker = getattr(perception_adapter, "with_query_invoker", None)
        refresh_binding = getattr(perception_adapter, "refresh_binding", None)
        if callable(with_query_invoker) and callable(refresh_binding):
            bound_adapter = with_query_invoker(runtime)
            if subtask_context_resolver is not None:
                register_subtask_tool(
                    runtime,
                    bound_adapter.refresh_binding,
                    tool_context_provider,
                    subtask_context_resolver,
                    assignment_store,
                )
    transport = CapabilityRuntimeTransport(runtime, gateway_identity=gateway_identity)
    return LabUtopiaPAOSRuntime(runtime, transport, selected_engine, provider, client, bound_adapter)


__all__ = [
    "LabUtopiaActionDriver",
    "LabUtopiaCycleClient",
    "LabUtopiaCycleProvider",
    "LabUtopiaPAOSClientError",
    "LabUtopiaPAOSRuntime",
    "build_labutopia_runtime",
]
