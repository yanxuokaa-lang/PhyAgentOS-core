"""Thin process boundary for persistent manipulation; no PAOS imports."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from .process_worker import JsonlProcessWorkerClient, ProcessWorkerProtocolLimitError


class PersistentWorkerError(RuntimeError):
    """A worker rejection, distinct from a lost process connection."""

    def __init__(self, error):
        super().__init__(str(error))
        self.code = error.get("code") if isinstance(error, dict) else None


class PersistentWorkerClient:
    def __init__(self, worker: JsonlProcessWorkerClient) -> None:
        self.worker = worker
        self._transport_lost = False
        self._transport_failure_code: str | None = None
        self._transport_failure_detail: str | None = None

    @property
    def transport_failure_code(self) -> str | None:
        if not self._transport_lost:
            return None
        return self._transport_failure_code or "persistent_world_connection_lost"

    def _request(self, *, timeout_s: float | None = None, **payload) -> dict[str, Any]:
        if self._transport_lost:
            raise RuntimeError("persistent world connection lost; start a new runtime explicitly")
        try:
            request = {"request_id": uuid4().hex, **payload}
            result = dict(
                self.worker.request(request)
                if timeout_s is None
                else self.worker.request(request, timeout_s=timeout_s)
            )
        except Exception as exc:
            if (
                isinstance(exc, ProcessWorkerProtocolLimitError)
                and exc.code == "worker_request_too_large"
            ):
                raise
            self._transport_lost = True
            code = getattr(exc, "code", None)
            self._transport_failure_code = (
                code if isinstance(code, str) and code else "persistent_world_connection_lost"
            )
            self._transport_failure_detail = str(exc)[:2000]
            raise
        if result.get("ok") is not True:
            raise PersistentWorkerError(result.get("error", "persistent provider unavailable"))
        return result

    def query(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        return self._request(
            command="query",
            operation=operation,
            arguments=dict(arguments),
            timeout_s=timeout_s,
        )

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
            return {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": None,
                "failure_owner": "infrastructure",
                "failure_code": (
                    self.client._transport_failure_code
                    or "persistent_world_connection_lost"
                ),
                "error_detail": self.client._transport_failure_detail,
                "retryable_in_revision": False,
                "requires_replan": False,
                "recommended_action": "stop",
            }
        return self.client._request(command="poll", invocation_id=self.invocation_id).get("result")

    def cancel(self) -> None:
        self.client._request(command="cancel", invocation_id=self.invocation_id)

    def stop(self) -> None:
        self.cancel()


class PersistentRouteReadinessTransport:
    """Use the existing readiness validator over the live world connection."""

    def __init__(self, client: PersistentWorkerClient) -> None:
        self.client = client

    def request(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> Mapping[str, Any]:
        response = (
            self.client.query("route_readiness", payload)
            if timeout_s is None
            else self.client.query("route_readiness", payload, timeout_s=timeout_s)
        )
        return {**response, "request_id": payload["request_id"]}


def build_persistent_route_readiness(client: PersistentWorkerClient):
    from .route_readiness import RouteReadinessClient

    return RouteReadinessClient(PersistentRouteReadinessTransport(client), worker_id="persistent-route-readiness")
