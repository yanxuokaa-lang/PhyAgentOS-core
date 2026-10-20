"""PAOS lifecycle adapters for LabUtopia cycle execution.

The module deliberately keeps scene execution in :mod:`isaacsim_lab.engine`.
It only supplies the async client/provider shape consumed by the existing PAOS
complete-cycle endpoint.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from threading import Event, RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from .engine import IsaacSimLabEngine
from .profile import LabUtopiaProfile


class LabUtopiaPAOSClientError(RuntimeError):
    """The LabUtopia client cannot safely start or observe a cycle."""


class LabUtopiaCycleProvider:
    """Own no-motion cycle preparation and task-owned assignment projection."""

    def __init__(self, engine: Any):
        self.engine = engine
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
        try:
            prepare = getattr(self.engine, "prepare_cycle", None)
            if not callable(prepare):
                raise LabUtopiaPAOSClientError("engine does not expose prepare_cycle")
            result = prepare(deepcopy(dict(arguments)))
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
    ):
        if isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")
        self.engine = engine
        self.allow_live = bool(allow_live)
        self._preparation_provider = preparation_provider or LabUtopiaCycleProvider(engine)
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

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._preparation_provider.prepare_cycle(arguments)

    def start(self, operation: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]):
        del owner
        if not self.allow_live:
            raise LabUtopiaPAOSClientError("live LabUtopia execution is disabled")
        if not operation or not invocation_id:
            raise LabUtopiaPAOSClientError("cycle invocation identity is required")
        with self._lock:
            if self._closed:
                raise LabUtopiaPAOSClientError("LabUtopia client is closed")
        cancel = Event()
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
        if callable(close):
            close()


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
    subtask_context_resolver: Callable[[str], Mapping[str, Any]] | None = None,
) -> LabUtopiaPAOSRuntime:
    """Compose LabUtopia behind PAOS without owning perception orchestration.

    ``perception_adapter`` is the provider-neutral PAOS adapter.  LabUtopia
    only supplies its observation/understanding/grasp/preparation providers;
    when the complete chain is absent, the Agent-facing subtask Tool is not
    registered.
    """

    from PhyAgentOS.forge.capability_runtime import CapabilityRuntimeTransport
    from pick_place_workflow.persistent_runtime import (
        build_persistent_runtime,
        register_subtask_tool,
    )

    selected_engine = engine or IsaacSimLabEngine(profile)
    provider = LabUtopiaCycleProvider(selected_engine)
    client = LabUtopiaCycleClient(
        selected_engine, allow_live=allow_live, preparation_provider=provider
    )
    runtime = build_persistent_runtime(
        client=client,
        understanding_provider=understanding_provider,
        grasp_provider=grasp_provider,
        preparation_provider=preparation_provider,
        capability_provider=capability_provider,
        observation_source=observation_source,
        resolve_preparation=resolve_preparation,
        tool_context_provider=tool_context_provider,
        possession=possession,
        held_preparation_provider=provider,
        resolve_held_preparation=provider.resolve,
        register_legacy_actions=False,
        register_legacy_held_operations=False,
    )
    bound_adapter = None
    if perception_adapter is not None and getattr(perception_adapter, "ready", False):
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
