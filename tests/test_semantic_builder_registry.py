from __future__ import annotations

from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.semantic_builder_registry import SemanticPlanBuilderRegistry
from PhyAgentOS.config.schema import ForgeConfig


class _Builder:
    def build(self, task_description, semantic_subtasks):
        return task_description, semantic_subtasks


class _Factory:
    builder_id = "fixture"

    def create(self, *, query_invoker):
        return query_invoker


def test_registry_loads_opt_in_entry_points(monkeypatch):
    factory = _Factory()
    entry_point = SimpleNamespace(load=lambda: lambda: factory)
    monkeypatch.setattr(
        "PhyAgentOS.agent.semantic_builder_registry.entry_points",
        lambda: SimpleNamespace(select=lambda *, group: [entry_point]),
    )
    registry = SemanticPlanBuilderRegistry()
    assert registry.discover() == ("fixture",)
    assert registry.create("fixture", query_invoker=_Builder()).build("task", []) == ("task", [])


def test_registry_rejects_missing_or_invalid_factory():
    registry = SemanticPlanBuilderRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.create("missing", query_invoker=object())

    with pytest.raises(TypeError, match="factory does not implement"):
        registry.register(object())


def test_registry_rejects_factory_that_does_not_create_a_builder():
    class InvalidFactory:
        builder_id = "invalid"

        def create(self, *, query_invoker):
            return query_invoker

    registry = SemanticPlanBuilderRegistry()
    registry.register(InvalidFactory())
    with pytest.raises(TypeError, match="must provide build"):
        registry.create("invalid", query_invoker=object())


def test_semantic_builder_selection_is_optional_host_configuration():
    assert ForgeConfig().semantic_plan_builder is None
    assert ForgeConfig(semantic_plan_builder="pick_place_workflow").semantic_plan_builder == (
        "pick_place_workflow"
    )
