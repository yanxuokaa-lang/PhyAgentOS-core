"""Thin process boundary for persistent manipulation; no PAOS imports."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from .process_worker import JsonlProcessWorkerClient


class PersistentWorkerClient:
    def __init__(self, worker: JsonlProcessWorkerClient) -> None:
        self.worker = worker
        self._transport_lost = False

    def _request(self, **payload) -> dict[str, Any]:
        if self._transport_lost:
            raise RuntimeError("persistent world connection lost; start a new runtime explicitly")
        try:
            result = dict(self.worker.request({"request_id": uuid4().hex, **payload}))
        except Exception:
            self._transport_lost = True
            raise
        if result.get("ok") is not True:
            raise RuntimeError(str(result.get("error", "persistent provider unavailable")))
        return result

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._request(command="query", operation=operation, arguments=dict(arguments))

    def start(self, phase: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]):
        try:
            self._request(command="start", phase=phase, invocation_id=invocation_id, owner=owner, arguments=dict(arguments))
        except Exception:
            if not self._transport_lost:
                raise
            # Sending may have succeeded before the acknowledgement was lost.
            # Retain the supplied invocation identity for unknown accounting.
        return PersistentActionDriver(self, invocation_id)

    def close(self) -> None:
        self.worker.release()


class PersistentActionDriver:
    def __init__(self, client: PersistentWorkerClient, invocation_id: str) -> None:
        self.client = client
        self.invocation_id = invocation_id

    def poll(self) -> Mapping[str, Any] | None:
        if self.client._transport_lost:
            return {"status": "unknown", "outcome_known": False,
                    "world_change_started": None, "failure_owner": "execution",
                    "failure_code": "persistent_world_connection_lost"}
        return self.client._request(command="poll", invocation_id=self.invocation_id).get("result")

    def cancel(self) -> None:
        self.client._request(command="cancel", invocation_id=self.invocation_id)

    def stop(self) -> None:
        self.cancel()


class PersistentRouteReadinessTransport:
    """Use the existing readiness validator over the live world connection."""

    def __init__(self, client: PersistentWorkerClient) -> None:
        self.client = client

    def request(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        response = self.client.query("route_readiness", payload)
        return {**response, "request_id": payload["request_id"]}


def build_persistent_route_readiness(client: PersistentWorkerClient):
    from .route_readiness import RouteReadinessClient

    return RouteReadinessClient(PersistentRouteReadinessTransport(client), worker_id="persistent-route-readiness")
