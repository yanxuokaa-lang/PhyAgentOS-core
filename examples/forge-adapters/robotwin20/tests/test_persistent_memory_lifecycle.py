from types import SimpleNamespace

import pytest
import robotwin_persistent_engine as engine_module


@pytest.mark.parametrize("operation", ["observe", "contact_qualification", "route_readiness"])
@pytest.mark.parametrize("fails", [False, True])
def test_query_reclaims_unused_cache_after_success_and_failure(monkeypatch, operation, fails):
    calls = []
    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
    world = object()
    engine.backend = world
    result = {"status": "available"}

    def query(name, arguments):
        calls.append(name)
        if fails:
            raise ValueError("qualification failed")
        return result

    cuda = SimpleNamespace(is_initialized=lambda: True, memory_reserved=lambda: 100,
        memory_allocated=lambda: 50, empty_cache=lambda: calls.append("empty_cache"))
    monkeypatch.setitem(engine_module.sys.modules, "torch", SimpleNamespace(cuda=cuda))
    monkeypatch.setattr(engine_module.gc, "collect", lambda: calls.append("collect"))
    engine._query = query
    if fails:
        with pytest.raises(ValueError, match="qualification failed"):
            engine.query(operation, {})
    else:
        assert engine.query(operation, {}) is result
    assert calls == [operation, "collect", "empty_cache"]
    assert engine.backend is world


def test_query_does_not_initialize_cuda_or_reclaim_during_status(monkeypatch):
    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
    engine._query = lambda operation, arguments: {"status": "available"}
    monkeypatch.setitem(engine_module.sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        is_initialized=lambda: False, empty_cache=lambda: pytest.fail("must not initialize CUDA"))))
    assert engine.query("observe", {}) == {"status": "available"}
    monkeypatch.delitem(engine_module.sys.modules, "torch")
    assert engine.query("observe", {}) == {"status": "available"}
    assert engine.query("snapshot", {}) == {"status": "available"}
