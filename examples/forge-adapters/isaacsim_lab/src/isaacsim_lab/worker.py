"""Private child-process entry point for Isaac Sim lifecycle isolation."""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from isaacsim_lab.engine import LabUtopiaBackend
    from isaacsim_lab.profile import LabUtopiaProfile
else:
    from .engine import LabUtopiaBackend
    from .profile import LabUtopiaProfile


def main() -> int:
    profile = LabUtopiaProfile.from_json(Path(os.environ["PAOS_ISAAC_PROFILE"]))
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": profile.headless})
    backend = LabUtopiaBackend(profile)
    socket_path = Path(os.environ["PAOS_ISAAC_SOCKET_PATH"])
    try:
        serve_session(socket_path, app, backend, profile)
    finally:
        app.close()
    return 0


def serve_session(socket_path: Path, app, backend, profile) -> None:
    """Serve sequential observation/action requests from one Isaac owner."""
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    context = WorkerSessionContext(app)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(socket_path))
            server.listen(1)
            while True:
                connection, _ = server.accept()
                with connection:
                    payload = _read_request(connection)
                    request_id = payload.get("request_id")
                    method = payload.get("method")
                    try:
                        if method == "close":
                            close_session = getattr(backend, "close_session", None)
                            if callable(close_session):
                                close_session(context)
                            context.close()
                            _write_response(connection, request_id, {"closed": True})
                            return
                        if method == "observe":
                            result = backend.observe_in_session(context, payload.get("arguments", {}))
                        elif method == "scene_revision":
                            result = backend.scene_revision_in_session(context)
                        elif method == "execute_cycle":
                            arguments = payload.get("arguments")
                            if not isinstance(arguments, dict):
                                raise ValueError("arguments must be an object")
                            cancel = _FileCancelEvent(payload.get("cancel_path"))
                            result_path = profile.lab_root / "outputs" / "paos-session" / f"{request_id}.json"
                            result_path.parent.mkdir(parents=True, exist_ok=True)
                            ensure_action_scene = getattr(backend, "ensure_action_scene", None)
                            if callable(ensure_action_scene):
                                ensure_action_scene(context)
                            current_revision = context.current_scene_revision()
                            if current_revision is None or arguments.get("scene_revision") != current_revision:
                                result = {
                                    "status": "invalid",
                                    "outcome_known": False,
                                    "world_change_started": False,
                                    "motion_authorized": False,
                                    "failure_code": "stale_scene_revision",
                                    "current_scene_revision": current_revision,
                                }
                            else:
                                result = backend._run_session_cycle(
                                    context, arguments, cancel, result_path.with_suffix(".mp4")
                                )
                                if result.get("world_change_started") is True:
                                    result = dict(result)
                                    result["new_scene_revision"] = context.advance_scene_revision()
                            result_path.write_text(
                                json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8"
                            )
                        else:
                            raise ValueError("unsupported worker request method")
                        _write_response(connection, request_id, dict(result))
                    except Exception as exc:
                        _write_response(connection, request_id, {
                            "status": "unknown",
                            "outcome_known": False,
                            "failure_owner": "isaacsim_adapter",
                            "failure_code": type(exc).__name__,
                            "error_detail": str(exc)[:512],
                        }, ok=False)
    finally:
        context.close()


class WorkerSessionContext:
    """Own the resources shared by all RPCs handled by one Isaac worker."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._resources: dict[str, Any] = {}
        self._closed = False
        self._scene_revision_base: str | None = None
        self._scene_revision_session = uuid4().hex
        self._scene_revision_sequence = 0

    def register(self, name: str, resource: Any) -> None:
        if self._closed:
            raise RuntimeError("Isaac worker session is closed")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("worker resource name must be non-empty")
        self._resources[name] = resource

    def resolve(self, name: str) -> Any | None:
        if self._closed:
            return None
        return self._resources.get(name)

    def initialize_scene_revision(self, base_revision: str) -> str:
        if not isinstance(base_revision, str) or not base_revision.strip():
            raise ValueError("scene revision base must be non-empty")
        if self._scene_revision_base is None:
            self._scene_revision_base = base_revision
        elif self._scene_revision_base != base_revision:
            raise ValueError("worker session cannot change its scene revision base")
        return self.current_scene_revision()

    def current_scene_revision(self) -> str | None:
        if self._closed or self._scene_revision_base is None:
            return None
        return f"{self._scene_revision_base}:{self._scene_revision_session}:{self._scene_revision_sequence}"

    def advance_scene_revision(self) -> str:
        if self.current_scene_revision() is None:
            raise RuntimeError("scene revision is unavailable before scene initialization")
        self._scene_revision_sequence += 1
        return self.current_scene_revision()

    def close(self) -> None:
        self._resources.clear()
        self._closed = True


class _FileCancelEvent:
    def __init__(self, path):
        self._path = Path(path) if isinstance(path, str) and path else None

    def is_set(self) -> bool:
        return self._path is not None and self._path.exists()


def _read_request(connection: socket.socket) -> dict:
    data = bytearray()
    while b"\n" not in data:
        chunk = connection.recv(65536)
        if not chunk:
            raise ConnectionError("request ended before newline")
        data.extend(chunk)
    value = json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("request_id"), str):
        raise ValueError("worker request must contain request_id")
    return value


def _write_response(connection: socket.socket, request_id: str, result: dict, *, ok: bool = True) -> None:
    response = {"request_id": request_id, "ok": ok, "result": result}
    connection.sendall(json.dumps(
        response, ensure_ascii=False, allow_nan=False, default=_json_default
    ).encode("utf-8") + b"\n")


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    raise TypeError(f"worker response contains unsupported value: {type(value).__name__}")


if __name__ == "__main__":
    raise SystemExit(main())
