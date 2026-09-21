from __future__ import annotations

from threading import Event, Thread

import pytest

from robotwin20_adapter.qwen3_vl_vllm_lifecycle import (
    LifecycleManagedSceneUnderstandingInference,
    Qwen3VLVLLMLifecycleConfig,
    Qwen3VLVLLMLifecycleError,
    Qwen3VLVLLMLifecycleManager,
)


class _Response:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class _Client:
    def __init__(self, *, sleeping=False, status_error=None, **_kwargs):
        self.sleeping = sleeping
        self.status_error = status_error
        self.calls = []
        self.closed = False
        self.slept = Event()

    def get(self, path):
        self.calls.append(("GET", path, None))
        return _Response(self.sleeping, self.status_error)

    def post(self, path, *, params=None):
        self.calls.append(("POST", path, params))
        if path == "/wake_up":
            self.sleeping = False
        elif path == "/sleep":
            self.sleeping = True
            self.slept.set()
        return _Response({"ok": True})

    def close(self):
        self.closed = True


def _manager(client, *, idle=60):
    return Qwen3VLVLLMLifecycleManager(
        Qwen3VLVLLMLifecycleConfig(idle_timeout_s=idle),
        client_factory=lambda **_kwargs: client,
    )


def test_lifecycle_control_bypasses_environment_proxy_for_local_endpoint():
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return _Client()

    manager = Qwen3VLVLLMLifecycleManager(
        Qwen3VLVLLMLifecycleConfig(), client_factory=factory
    )

    assert captured["base_url"] == "http://127.0.0.1:8012"
    assert captured["trust_env"] is False
    manager.close()


def test_sleeping_request_wakes_before_inference_and_arms_idle_sleep():
    client = _Client(sleeping=True)
    manager = _manager(client)
    seen = []
    provider = LifecycleManagedSceneUnderstandingInference(
        type("Provider", (), {"infer": lambda _self, request: seen.append(request) or {"ok": True}})(),
        manager,
    )

    assert provider.infer({"scene": 1}) == {"ok": True}
    assert seen == [{"scene": 1}]
    assert ("POST", "/wake_up", None) in client.calls
    assert manager.active_requests == 0
    manager.close()


def test_awake_request_does_not_repeat_wake():
    client = _Client(sleeping=False)
    manager = _manager(client)
    with manager.request():
        assert manager.active_requests == 1
    assert not any(call[1] == "/wake_up" for call in client.calls)
    manager.close()


def test_provider_release_sleeps_synchronously_for_gpu_handoff():
    client = _Client(sleeping=False)
    manager = _manager(client)
    provider = LifecycleManagedSceneUnderstandingInference(
        type("Provider", (), {"infer": lambda _self, _request: {"ok": True}})(),
        manager,
    )

    assert provider.infer({"scene": 1}) == {"ok": True}
    provider.release()

    assert client.sleeping is True
    assert manager.last_state == "sleeping"
    assert ("POST", "/sleep", {"level": 1}) in client.calls
    manager.close()


def test_gpu_handoff_refuses_to_sleep_with_active_request():
    client = _Client(sleeping=False)
    manager = _manager(client)

    with manager.request():
        with pytest.raises(Qwen3VLVLLMLifecycleError, match="requests are active"):
            manager.sleep_for_handoff()

    assert client.sleeping is False
    manager.close()


def test_manager_sleeps_after_startup_idle_without_a_request():
    client = _Client(sleeping=False)
    manager = _manager(client, idle=0.01)

    assert client.slept.wait(1)
    assert manager.last_state == "sleeping"
    manager.close()


def test_concurrent_requests_exclude_idle_sleep_until_last_request_finishes():
    client = _Client(sleeping=False)
    manager = _manager(client)
    first_entered = Event()
    release = Event()

    def hold():
        with manager.request():
            first_entered.set()
            release.wait(2)

    thread = Thread(target=hold)
    thread.start()
    assert first_entered.wait(1)
    with manager.request():
        manager._sleep_if_idle()
        assert not any(call[1] == "/sleep" for call in client.calls)
    release.set()
    thread.join(2)
    manager._sleep_if_idle()
    assert ("POST", "/sleep", {"level": 1}) in client.calls
    manager.close()


def test_wake_status_failure_is_bounded_for_fallback():
    client = _Client(status_error=ConnectionError("down"))
    manager = _manager(client)
    with pytest.raises(Qwen3VLVLLMLifecycleError, match="wake/status"):
        with manager.request():
            pass
    assert manager.active_requests == 0
    assert manager.last_state == "error"
    manager.close()


def test_wake_failure_rearms_idle_check_for_recovered_server():
    client = _Client(status_error=ConnectionError("down"))
    manager = _manager(client, idle=0.01)

    with pytest.raises(Qwen3VLVLLMLifecycleError, match="wake/status"):
        with manager.request():
            pass
    client.status_error = None

    assert client.slept.wait(1)
    assert manager.last_state == "sleeping"
    manager.close()


def test_handoff_failure_rearms_idle_check_for_recovered_server():
    client = _Client(status_error=ConnectionError("down"))
    manager = _manager(client, idle=0.01)

    with pytest.raises(Qwen3VLVLLMLifecycleError, match="handoff"):
        manager.sleep_for_handoff()
    client.status_error = None

    assert client.slept.wait(1)
    assert manager.last_state == "sleeping"
    manager.close()
