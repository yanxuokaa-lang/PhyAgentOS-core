"""Private child-process entry point for Isaac Sim lifecycle isolation."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

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
                        _write_response(connection, request_id, {"closed": True})
                        return
                    if method == "observe":
                        result = backend.observe_in_session(app, payload.get("arguments", {}))
                    elif method == "execute_cycle":
                        arguments = payload.get("arguments")
                        if not isinstance(arguments, dict):
                            raise ValueError("arguments must be an object")
                        cancel = _FileCancelEvent(payload.get("cancel_path"))
                        result_path = profile.lab_root / "outputs" / "paos-session" / f"{request_id}.json"
                        result_path.parent.mkdir(parents=True, exist_ok=True)
                        result = backend._run_session_cycle(
                            app, arguments, cancel, result_path.with_suffix(".mp4")
                        )
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
    connection.sendall(json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")


if __name__ == "__main__":
    raise SystemExit(main())
