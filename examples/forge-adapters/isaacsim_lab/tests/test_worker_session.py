import threading
import time
from pathlib import Path
from types import SimpleNamespace

from isaacsim_lab.paos_client import LabUtopiaCycleClient
from isaacsim_lab.worker import serve_session
from isaacsim_lab.worker_session import IsaacWorkerSession


class FakeProcess:
    def __init__(self, thread):
        self.thread = thread

    def poll(self):
        return 0 if not self.thread.is_alive() else None

    def wait(self, timeout=None):
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise TimeoutError
        return 0

    def terminate(self):
        return None

    def kill(self):
        return None


class FakeBackend:
    def __init__(self):
        self.methods = []

    def observe_in_session(self, app, request):
        self.methods.append(("observe", app))
        return {"status": "unavailable", "failure_code": "camera_registry_missing"}

    def _run_session_cycle(self, app, arguments, cancel, video_path):
        self.methods.append(("execute_cycle", app))
        while arguments.get("wait_for_cancel") and not cancel.is_set():
            time.sleep(0.005)
        return {
            "status": "unknown" if cancel.is_set() else "completed",
            "outcome_known": not cancel.is_set(),
            "video_path": str(video_path),
        }


def make_session(tmp_path, monkeypatch, backend=None):
    profile = SimpleNamespace(lab_root=tmp_path)
    fake_backend = backend or FakeBackend()
    process_count = []

    def process_factory(*_args, env, **_kwargs):
        process_count.append(1)
        socket_path = Path(env["PAOS_ISAAC_SOCKET_PATH"])
        thread = threading.Thread(
            target=serve_session,
            args=(socket_path, object(), fake_backend, profile),
            daemon=True,
        )
        thread.start()
        return FakeProcess(thread)

    monkeypatch.setenv("OMNI_KIT_ACCEPT_EULA", "YES")
    session = IsaacWorkerSession(
        Path("profile.json"), startup_timeout_s=2, request_timeout_s=3,
        process_factory=process_factory,
    )
    return session, fake_backend, process_count


def test_worker_session_reuses_one_owner_for_observation_and_action(tmp_path, monkeypatch):
    session, backend, process_count = make_session(tmp_path, monkeypatch)
    try:
        observed = session.observe({"sensor_ref": "sensor://front"})
        executed = session.request("execute_cycle", {"operation": "pour_cycle"})
    finally:
        session.close()

    assert process_count == [1]
    assert [method for method, _app in backend.methods] == ["observe", "execute_cycle"]
    assert backend.methods[0][1] is backend.methods[1][1]
    assert observed == {"status": "unavailable", "failure_code": "camera_registry_missing"}
    assert executed["status"] == "completed"


def test_worker_session_propagates_cancellation_without_faking_success(tmp_path, monkeypatch):
    session, _backend, process_count = make_session(tmp_path, monkeypatch)
    cancel = threading.Event()
    result = []
    request = threading.Thread(
        target=lambda: result.append(session.request(
            "execute_cycle", {"wait_for_cancel": True}, cancel=cancel
        )),
        daemon=True,
    )
    request.start()
    time.sleep(0.05)
    cancel.set()
    request.join(timeout=2)
    session.close()

    assert not request.is_alive()
    assert process_count == [1]
    assert result[0]["status"] == "unknown"
    assert result[0]["outcome_known"] is False


def test_worker_session_rejects_requests_after_close(tmp_path, monkeypatch):
    session, _backend, _process_count = make_session(tmp_path, monkeypatch)
    session.close()
    try:
        session.observe({"sensor_ref": "sensor://front"})
    except RuntimeError as exc:
        assert "closed" in str(exc)
    else:
        raise AssertionError("closed worker session accepted a request")


def test_worker_session_reports_child_exit_before_socket_startup(tmp_path, monkeypatch):
    def process_factory(*_args, **_kwargs):
        thread = threading.Thread(target=lambda: None)
        thread.start()
        thread.join()
        return FakeProcess(thread)

    session = IsaacWorkerSession(
        Path("profile.json"), startup_timeout_s=0.2, process_factory=process_factory
    )
    try:
        session.observe({"sensor_ref": "sensor://front"})
    except RuntimeError as exc:
        assert "exited before opening" in str(exc)
    else:
        raise AssertionError("worker startup failure was not surfaced")


def test_paos_client_does_not_advertise_or_project_unavailable_observation():
    engine = SimpleNamespace(
        observation_ready=False,
        observe=lambda _request: {"status": "unavailable", "failure_code": "camera_registry_missing"},
    )
    client = LabUtopiaCycleClient(engine)
    try:
        assert client.observation_ready is False
        assert client.capture({"sensor_ref": "sensor://front"}) is None
    finally:
        client.close()
