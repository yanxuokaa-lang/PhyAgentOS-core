import threading
import time
from datetime import datetime, timezone
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
        self.closed = False

    def observe_in_session(self, session, request):
        self.methods.append(("observe", session))
        session.initialize_scene_revision("scene-1")
        session.register("shared_scene", {"revision": "scene-1"})
        if request.get("capture"):
            return {"status": "available", "captured_at": datetime(2026, 10, 22, tzinfo=timezone.utc)}
        return {"status": "unavailable", "failure_code": "camera_registry_missing"}

    def _run_session_cycle(self, session, arguments, cancel, video_path):
        self.methods.append(("execute_cycle", session))
        if arguments.get("require_shared_scene"):
            assert session.resolve("shared_scene") == {"revision": "scene-1"}
        while arguments.get("wait_for_cancel") and not cancel.is_set():
            time.sleep(0.005)
        return {
            "status": "unknown" if cancel.is_set() else "completed",
            "outcome_known": not cancel.is_set(),
            "world_change_started": not cancel.is_set(),
            "video_path": str(video_path),
        }

    def prepare_manipulation_in_session(self, session, arguments):
        self.methods.append(("prepare_manipulation", session))
        return {"status": "unavailable", "motion_authorized": False,
                "failure_code": "test_route_unavailable"}

    def execute_phase_in_session(self, session, arguments, cancel):
        self.methods.append(("execute_phase", session))
        return {"status": "unavailable", "outcome_known": False,
                "world_change_started": False, "motion_authorized": False,
                "failure_code": "test_phase_unavailable"}

    def bind_observed_entities_in_session(self, session, arguments):
        self.methods.append(("bind_observed_entities", session))
        return {"status": "unavailable", "failure_code": "visual_body_association_ambiguous"}

    def scene_revision_in_session(self, session):
        revision = session.current_scene_revision()
        if revision is None:
            return {"status": "unavailable"}
        return {"status": "available", "scene_revision": revision}

    def close_session(self, session):
        self.closed = session.resolve("shared_scene") is not None


def make_session(tmp_path, monkeypatch, backend=None, observation_artifact_root=None):
    profile = SimpleNamespace(lab_root=tmp_path)
    fake_backend = backend or FakeBackend()
    process_count = []
    child_environment = []

    def process_factory(*_args, env, **_kwargs):
        process_count.append(1)
        child_environment.append(dict(env))
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
        observation_artifact_root=observation_artifact_root,
        process_factory=process_factory,
    )
    return session, fake_backend, process_count, child_environment


def test_worker_session_reuses_one_owner_for_observation_and_action(tmp_path, monkeypatch):
    session, backend, process_count, _child_environment = make_session(tmp_path, monkeypatch)
    try:
        observed = session.observe({"sensor_ref": "sensor://front"})
        revision = session.scene_revision()
        executed = session.request("execute_cycle", {
            "operation": "pour_cycle", "require_shared_scene": True,
            "scene_revision": revision["scene_revision"],
        })
        after = session.scene_revision()
    finally:
        session.close()

    assert process_count == [1]
    assert [method for method, _app in backend.methods] == ["observe", "execute_cycle"]
    assert backend.methods[0][1] is backend.methods[1][1]
    assert backend.methods[0][1].app is not None
    assert backend.closed is True
    assert backend.methods[0][1].resolve("shared_scene") is None
    assert observed == {"status": "unavailable", "failure_code": "camera_registry_missing"}
    assert executed["status"] == "completed"
    assert after["scene_revision"] != revision["scene_revision"]
    assert executed["new_scene_revision"] == after["scene_revision"]


def test_worker_rejects_stale_scene_revision_before_action_dispatch(tmp_path, monkeypatch):
    session, backend, _process_count, _child_environment = make_session(tmp_path, monkeypatch)
    try:
        session.observe({"sensor_ref": "sensor://front"})
        stale = session.request("execute_cycle", {
            "operation": "pour_cycle", "scene_revision": "scene-1:old-session:0",
        })
    finally:
        session.close()

    assert stale["status"] == "invalid"
    assert stale["failure_code"] == "stale_scene_revision"
    assert stale["world_change_started"] is False
    assert [method for method, _session in backend.methods] == ["observe"]


def test_worker_routes_preparation_and_phase_calls_in_the_same_session(tmp_path, monkeypatch):
    session, backend, process_count, _environment = make_session(tmp_path, monkeypatch)
    try:
        session.observe({"sensor_ref": "sensor://front"})
        revision = session.scene_revision()["scene_revision"]
        prepared = session.request("prepare_manipulation", {"scene_revision": revision})
        phase = session.request("execute_phase", {
            "operation": "acquire", "scene_revision": revision,
        })
    finally:
        session.close()

    assert process_count == [1]
    assert prepared["failure_code"] == "test_route_unavailable"
    assert phase["failure_code"] == "test_phase_unavailable"
    assert [method for method, _session in backend.methods] == [
        "observe", "prepare_manipulation", "execute_phase",
    ]
    assert backend.methods[0][1] is backend.methods[1][1] is backend.methods[2][1]


def test_worker_session_serializes_observation_artifact_metadata(tmp_path, monkeypatch):
    session, _backend, _process_count, _child_environment = make_session(tmp_path, monkeypatch)
    try:
        observed = session.observe({"sensor_ref": "sensor://front", "capture": True})
    finally:
        session.close()

    assert observed == {
        "status": "available",
        "captured_at": "2026-10-22T00:00:00+00:00",
    }


def test_worker_session_propagates_cancellation_without_faking_success(tmp_path, monkeypatch):
    session, _backend, process_count, _child_environment = make_session(tmp_path, monkeypatch)
    cancel = threading.Event()
    result = []
    request = threading.Thread(
        target=lambda: (
            session.observe({"sensor_ref": "sensor://front"}),
            result.append(session.request(
                "execute_cycle", {
                    "wait_for_cancel": True,
                    "scene_revision": session.scene_revision()["scene_revision"],
                }, cancel=cancel
            )),
        ),
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
    session, _backend, _process_count, _child_environment = make_session(tmp_path, monkeypatch)
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


def test_worker_session_passes_deployment_artifact_root_to_child(tmp_path, monkeypatch):
    artifact_root = tmp_path / "shared-observations"
    session, _backend, _process_count, child_environment = make_session(
        tmp_path, monkeypatch, observation_artifact_root=artifact_root
    )
    try:
        session.observe({"sensor_ref": "sensor://front"})
    finally:
        session.close()

    assert child_environment[0]["PAOS_ISAAC_OBSERVATION_ARTIFACT_ROOT"] == str(
        artifact_root.resolve()
    )


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


def test_worker_uses_configured_interpreter_without_changing_session_protocol(tmp_path, monkeypatch):
    session, _, processes, _ = make_session(tmp_path, monkeypatch)
    session.python_executable = "/configured/isaac/python"
    factory = session._process_factory
    commands = []
    def process_factory(command, **kwargs):
        commands.append(command)
        return factory(command, **kwargs)
    session._process_factory = process_factory
    try:
        session.observe({"sensor_ref": "sensor://front"})
    finally:
        session.close()
    assert commands == [["/configured/isaac/python", "-m", "isaacsim_lab.worker"]]
    assert processes == [1]


def test_visual_association_rejection_keeps_the_same_worker_scene(tmp_path, monkeypatch):
    session, backend, process_count, _ = make_session(tmp_path, monkeypatch)
    try:
        session.observe({"sensor_ref": "sensor://front"})
        before = session.scene_revision()
        response = session.request("bind_observed_entities", {"claims": []})
        after = session.scene_revision()
    finally:
        session.close()
    assert response["failure_code"] == "visual_body_association_ambiguous"
    assert before == after
    assert process_count == [1]
    assert backend.methods[0][1] is backend.methods[1][1]
