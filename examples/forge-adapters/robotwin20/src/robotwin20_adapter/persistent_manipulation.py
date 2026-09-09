"""Provider-owned holding lifecycle, independent of PAOS and simulator imports."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from threading import Event, RLock
from typing import Any, Callable, Mapping


class ManipulationStateError(RuntimeError):
    pass


class PersistentManipulationProvider:
    """Serialize one physical world and retain possession across bounded Actions.

    The engine is constructed and used on a single thread, including sensor
    queries. Gateway invocation identities are supplied by the caller.
    """

    def __init__(self, engine_factory: Callable[[], Any]) -> None:
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="robotwin-world")
        self._lock = RLock()
        try:
            self._engine = self._pool.submit(engine_factory).result()
        except Exception:
            self._pool.shutdown(wait=True)
            raise
        self._state = "empty"
        self._owner: str | None = None
        self._acquire_id: str | None = None
        self._entity: str | None = None
        self._operations: dict[str, tuple[Future, Event]] = {}
        self._closed = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"holding_state": self._state, "owner": self._owner,
                    "acquire_invocation_id": self._acquire_id, "entity_ref": self._entity}

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._state in {"acquiring", "placing"}:
                raise ManipulationStateError("world query unavailable during motion or shutdown")
            future = self._pool.submit(self._engine.query, operation, deepcopy(dict(arguments)))
            return {**dict(future.result()), **self.snapshot()}

    def start(self, phase: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]) -> None:
        if phase not in {"acquire", "place"} or not invocation_id or not owner:
            raise ManipulationStateError("invalid manipulation identity")
        arguments = deepcopy(dict(arguments))
        with self._lock:
            if self._closed:
                raise ManipulationStateError("provider is closed")
            if invocation_id in self._operations:
                raise ManipulationStateError("invocation already exists; poll its result")
            if phase == "acquire":
                if self._state != "empty":
                    raise ManipulationStateError("acquire requires an empty provider")
                if not isinstance(arguments.get("entity_ref"), str) or not arguments["entity_ref"]:
                    raise ManipulationStateError("acquire requires entity_ref")
                self._owner, self._acquire_id, self._entity = owner, invocation_id, arguments["entity_ref"]
            elif (self._state != "holding" or self._owner != owner
                  or arguments.get("acquire_invocation_id") != self._acquire_id
                  or arguments.get("entity_ref") != self._entity):
                raise ManipulationStateError("place does not match the owned held object")
            self._state = "acquiring" if phase == "acquire" else "placing"
            cancel = Event()
            self._operations[invocation_id] = (self._pool.submit(self._execute, phase, invocation_id, arguments, cancel), cancel)

    def _execute(self, phase: str, invocation_id: str, arguments: dict[str, Any], cancel: Event) -> dict[str, Any]:
        try:
            result = dict(self._engine.execute(phase, arguments, cancel))
        except Exception as exc:
            # An exception is not evidence that nothing happened.
            result = {"status": "unknown", "outcome_known": False,
                      "failure_owner": "execution", "failure_code": type(exc).__name__}
        with self._lock:
            status = result.get("status")
            if status == "succeeded" and result.get("outcome_known") is True:
                self._state = "holding" if phase == "acquire" else "empty"
            elif result.get("world_change_started") is False and result.get("continuation_valid") is not False:
                self._state = "empty" if phase == "acquire" else "holding"
            else:
                self._state = "uncertain"
            if self._state == "empty":
                self._owner = self._acquire_id = self._entity = None
            result.update(self.snapshot())
            result["invocation_id"] = invocation_id
            return result

    def poll(self, invocation_id: str) -> dict[str, Any] | None:
        with self._lock:
            operation = self._operations.get(invocation_id)
            if operation is None:
                raise ManipulationStateError("unknown provider invocation; reconcile the world")
            return deepcopy(operation[0].result()) if operation[0].done() else None

    def cancel(self, invocation_id: str) -> None:
        with self._lock:
            if invocation_id not in self._operations:
                raise ManipulationStateError("unknown provider invocation")
            self._operations[invocation_id][1].set()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for future, cancel in self._operations.values():
                if not future.done():
                    cancel.set()
            final = self._pool.submit(self._engine.close)
        try:
            final.result()
        finally:
            self._pool.shutdown(wait=True)
            with self._lock:
                if self._state != "empty":
                    self._state = "uncertain"


__all__ = ["ManipulationStateError", "PersistentManipulationProvider"]
