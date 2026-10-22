from __future__ import annotations

from types import SimpleNamespace

from PhyAgentOS.cli import commands
from PhyAgentOS.config.schema import Config


def _install_host_fakes(monkeypatch):
    active_runtime = object()
    coordinator_kwargs = None
    builder_queries = []

    class FakeStateStore:
        pass

    class FakeCatalog:
        pass

    class FakeManager:
        def __init__(self, *, catalog, state_store):
            assert isinstance(catalog, FakeCatalog)
            assert isinstance(state_store, FakeStateStore)

    class FakeRegistry:
        is_available = True

        def __init__(self, active, *, catalog, state_store, auto_refresh):
            assert active is active_runtime
            assert isinstance(catalog, FakeCatalog)
            assert isinstance(state_store, FakeStateStore)
            assert auto_refresh is True

    class FakeClient:
        def __init__(self, registry):
            assert isinstance(registry, FakeRegistry)

    class FakeRuntimeSet:
        def __init__(self, registry, name):
            assert isinstance(registry, FakeRegistry)
            assert name in {"invocation_ids", "session_ids", "task_binding_ids"}

    class FakeBindingResolver:
        def __init__(self, registry):
            assert isinstance(registry, FakeRegistry)

    class FakeCoordinator:
        def __init__(self, **kwargs):
            nonlocal coordinator_kwargs
            coordinator_kwargs = kwargs

    class FakeBuilderRegistry:
        def discover(self):
            return ("fixture",)

        def create(self, builder_id, *, query_invoker):
            assert builder_id == "fixture"
            assert isinstance(query_invoker, FakeClient)
            builder_queries.append(query_invoker)
            return SimpleNamespace(build=lambda *_args: {})

    monkeypatch.setattr("PhyAgentOS.skill_runtime.catalog.SkillCatalog", FakeCatalog)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.state.RuntimeStateStore", FakeStateStore)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.manager.RuntimeManager", FakeManager)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.integration.discover_active_runtime", lambda **_kwargs: active_runtime)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.integration.ActiveRuntimeRegistry", FakeRegistry)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.integration.DynamicForgeToolClient", FakeClient)
    monkeypatch.setattr("PhyAgentOS.skill_runtime.integration.DynamicRuntimeSet", FakeRuntimeSet)
    monkeypatch.setattr("PhyAgentOS.forge.binding.ForgeSkillBindingResolver", FakeBindingResolver)
    monkeypatch.setattr("PhyAgentOS.forge.task.AgentTaskCoordinator", FakeCoordinator)
    monkeypatch.setattr(commands, "_make_forge_verifier", lambda *_args: "verifier")
    monkeypatch.setattr("PhyAgentOS.agent.semantic_builder_registry.SemanticPlanBuilderRegistry", FakeBuilderRegistry)
    return lambda: (builder_queries, coordinator_kwargs)


def test_cli_host_selects_configured_builder_and_passes_active_query_client(monkeypatch):
    inspect = _install_host_fakes(monkeypatch)
    config = Config()
    config.forge.semantic_plan_builder = "fixture"

    components = commands._make_forge_components(config, provider=object())

    client, _invocation_ids, coordinator, runtime_available, builder = components
    builder_queries, coordinator_kwargs = inspect()
    assert builder_queries == [client]
    assert coordinator.__class__.__name__ == "FakeCoordinator"
    assert runtime_available is True
    assert callable(builder.build)
    assert coordinator_kwargs["client"] is client
    assert coordinator_kwargs["verifier"] == "verifier"


def test_cli_host_keeps_builder_optional_when_configuration_is_unset(monkeypatch):
    inspect = _install_host_fakes(monkeypatch)
    config = Config()

    components = commands._make_forge_components(config, provider=object())

    assert components[-1] is None
    assert inspect()[0] == []
