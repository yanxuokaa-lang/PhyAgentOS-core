"""Parent-side client for one reusable Isaac worker session."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from threading import Event, RLock
from typing import Any, Mapping
from uuid import uuid4


class IsaacWorkerSessionError(RuntimeError):
    """The Isaac worker session could not serve a request reliably."""


class IsaacWorkerSession:
    """Own a child process and serialize requests to its live SimulationApp."""

    def __init__(
        self,
        profile_path: Path,
        *,
        startup_timeout_s: float = 120.0,
        request_timeout_s: float = 900.0,
        observation_artifact_root: str | Path | None = None,
        process_factory: Any = subprocess.Popen,
    ) -> None:
        self.profile_path = Path(profile_path)
        self.startup_timeout_s = float(startup_timeout_s)
        self.request_timeout_s = float(request_timeout_s)
        self.observation_artifact_root = (
            Path(observation_artifact_root).expanduser().resolve()
            if observation_artifact_root is not None
            else None
        )
        self._process_factory = process_factory
        self._lock = RLock()
        self._process: Any | None = None
        self._socket_path: Path | None = None
        self._session_dir: Path | None = None
        self._closed = False

    def request(
        self,
        method: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        cancel: Event | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if method not in {"execute_cycle", "observe", "scene_revision"}:
            raise ValueError(f"unsupported Isaac worker method: {method}")
        timeout = self.request_timeout_s if timeout_s is None else float(timeout_s)
        request_id = uuid4().hex
        cancel_path = self._session_dir / f"cancel-{request_id}" if self._session_dir else None
        with self._lock:
            self._ensure_started()
            assert self._socket_path is not None and self._session_dir is not None
            cancel_path = self._session_dir / f"cancel-{request_id}"
            deadline = time.monotonic() + timeout
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    self._connect(connection, self._socket_path, deadline)
                    connection.settimeout(0.2)
                    payload = {
                        "request_id": request_id,
                        "method": method,
                        "arguments": dict(arguments or {}),
                        "cancel_path": str(cancel_path),
                    }
                    connection.sendall(json.dumps(payload, allow_nan=False).encode("utf-8") + b"\n")
                    response = self._receive(connection, request_id, cancel, cancel_path, deadline)
            except (OSError, json.JSONDecodeError, IsaacWorkerSessionError):
                self._discard_worker()
                raise
            finally:
                cancel_path.unlink(missing_ok=True)
        result = response.get("result")
        if not isinstance(result, Mapping):
            raise IsaacWorkerSessionError("Isaac worker returned an invalid result")
        return dict(result)

    def observe(self, request: Mapping[str, Any], *, timeout_s: float | None = None) -> dict[str, Any]:
        return self.request("observe", request, timeout_s=timeout_s)

    def scene_revision(self, *, timeout_s: float | None = None) -> dict[str, Any]:
        return self.request("scene_revision", timeout_s=timeout_s)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            process = self._process
            socket_path = self._socket_path
            if process is not None and process.poll() is None and socket_path is not None:
                try:
                    self._send_close(socket_path)
                except (OSError, IsaacWorkerSessionError):
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            self._process = None
            self._remove_session_dir()

    def _ensure_started(self) -> None:
        if self._closed:
            raise IsaacWorkerSessionError("Isaac worker session is closed")
        if self._process is not None and self._process.poll() is None:
            return
        self._remove_session_dir()
        session_dir = Path(tempfile.mkdtemp(prefix="paos-isaac-session-"))
        socket_path = session_dir / "worker.sock"
        env = dict(os.environ)
        env.update({
            "PAOS_ISAAC_WORKER": "1",
            "PAOS_ISAAC_PROFILE": str(self.profile_path),
            "PAOS_ISAAC_SOCKET_PATH": str(socket_path),
        })
        if self.observation_artifact_root is not None:
            env["PAOS_ISAAC_OBSERVATION_ARTIFACT_ROOT"] = str(self.observation_artifact_root)
        process = self._process_factory(
            [sys.executable, "-m", "isaacsim_lab.worker"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._session_dir = session_dir
        self._socket_path = socket_path
        self._process = process
        deadline = time.monotonic() + self.startup_timeout_s
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self._discard_worker()
                raise IsaacWorkerSessionError("Isaac worker exited before opening its session socket")
            if socket_path.exists():
                return
            time.sleep(0.05)
        self._discard_worker()
        raise IsaacWorkerSessionError("Isaac worker session startup timed out")

    @staticmethod
    def _connect(connection: socket.socket, socket_path: Path, deadline: float) -> None:
        while True:
            try:
                connection.connect(str(socket_path))
                return
            except (FileNotFoundError, ConnectionRefusedError):
                if time.monotonic() >= deadline:
                    raise IsaacWorkerSessionError("Isaac worker session did not accept requests")
                time.sleep(0.05)

    def _receive(
        self,
        connection: socket.socket,
        request_id: str,
        cancel: Event | None,
        cancel_path: Path,
        deadline: float,
    ) -> dict[str, Any]:
        chunks = bytearray()
        cancellation_sent = False
        while time.monotonic() < deadline:
            if cancel is not None and cancel.is_set() and not cancellation_sent:
                cancel_path.touch()
                cancellation_sent = True
            try:
                chunk = connection.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise IsaacWorkerSessionError("Isaac worker closed the request connection")
            chunks.extend(chunk)
            if b"\n" not in chunks:
                continue
            line, _, _rest = chunks.partition(b"\n")
            response = json.loads(line.decode("utf-8"))
            if not isinstance(response, dict) or response.get("request_id") != request_id:
                raise IsaacWorkerSessionError("Isaac worker response does not match the request")
            if response.get("ok") is not True:
                raise IsaacWorkerSessionError(str(response.get("error", "Isaac worker request failed")))
            return response
        cancel_path.touch(exist_ok=True)
        raise IsaacWorkerSessionError("Isaac worker request timed out")

    def _send_close(self, socket_path: Path) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(socket_path))
            request_id = uuid4().hex
            connection.sendall(json.dumps({"request_id": request_id, "method": "close"}).encode() + b"\n")
            line = bytearray()
            while b"\n" not in line:
                line.extend(connection.recv(4096))
            response = json.loads(bytes(line).split(b"\n", 1)[0].decode("utf-8"))
            if response.get("request_id") != request_id or response.get("ok") is not True:
                raise IsaacWorkerSessionError("Isaac worker did not acknowledge close")

    def _discard_worker(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._remove_session_dir()

    def _remove_session_dir(self) -> None:
        directory = self._session_dir
        self._session_dir = None
        self._socket_path = None
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)


__all__ = ["IsaacWorkerSession", "IsaacWorkerSessionError"]
