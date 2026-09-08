from __future__ import annotations

import asyncio
import builtins
from types import SimpleNamespace

import pytest

from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.cli.textual_app import (
    TextualUnavailableError,
    _require_textual,
    _task_event_lines,
    _task_rows,
    build_textual_app,
)


class _Store:
    def __init__(self, tasks: list[object], events: dict[str, list[dict[str, object]]]):
        self._tasks = tasks
        self._events = events

    def find_by_origin_session_key(self, session_key: str) -> list[object]:
        return [task for task in self._tasks if task.origin_session_key == session_key]

    def events(self, task_id: str, *, limit: int = 200) -> list[dict[str, object]]:
        return self._events.get(task_id, [])[:limit]


def _coordinator() -> SimpleNamespace:
    graph = SimpleNamespace(
        nodes=(
            SimpleNamespace(
                node_id="observe", capability="scene.observe", dependencies=()
            ),
            SimpleNamespace(
                node_id="arrange",
                capability="object.arrange",
                dependencies=("observe",),
            ),
        )
    )
    task = SimpleNamespace(
        task_id="task-rgb",
        task_description="Arrange blocks by RGB color",
        origin_session_key="cli:direct",
        status=SimpleNamespace(value="waiting_for_user"),
        pause_requested=False,
        terminal=False,
        active_revision_id="revision-1",
        active_revision=SimpleNamespace(
            number=1,
            plan_graph=graph,
            node_settlements=(
                SimpleNamespace(node_id="observe", status="completed"),
            ),
        ),
        clarification_question="Choose the target direction",
        revisions=[SimpleNamespace()],
    )
    return SimpleNamespace(
        store=_Store(
            [task],
            {
                "task-rgb": [
                    {
                        "event_type": "node_settled",
                        "payload": {"node_id": "observe", "status": "completed"},
                    }
                ]
            },
        )
    )


def test_task_projection_preserves_authoritative_settlement_and_pending_nodes():
    rows = _task_rows(_coordinator(), "cli:direct")

    assert rows == [
        {
            "task_id": "task-rgb",
            "description": "Arrange blocks by RGB color",
            "status": "waiting_for_user",
            "revision_id": "revision-1",
            "revision_number": 1,
            "revision_count": 1,
            "completed_count": 1,
            "node_count": 2,
            "nodes": [
                {
                    "node_id": "observe",
                    "capability": "scene.observe",
                    "dependencies": [],
                    "status": "completed",
                },
                {
                    "node_id": "arrange",
                    "capability": "object.arrange",
                    "dependencies": ["observe"],
                    "status": "pending",
                },
            ],
            "clarification": "Choose the target direction",
        }
    ]


def test_textual_dashboard_normalizes_bare_cli_session_identity():
    from PhyAgentOS.cli.textual_app import _session_identity

    assert _session_identity("direct") == ("cli", "direct", "cli:direct")
    assert _session_identity("cli:direct") == ("cli", "direct", "cli:direct")


def test_task_projection_renders_pause_without_mutating_persisted_status():
    coordinator = _coordinator()
    task = coordinator.store._tasks[0]
    task.status.value = "executing"
    task.pause_requested = True

    row = _task_rows(coordinator, "cli:direct")[0]

    assert row["status"] == "paused"
    assert row["clarification"] is None


def test_event_projection_reads_coordinator_events_without_execution_side_effects():
    lines = _task_event_lines(_coordinator(), "cli:direct")

    assert lines == ["task-rgb node_settled node_id=observe status=completed"]


def test_textual_is_optional_and_missing_dependency_is_explicit(monkeypatch):
    real_import = builtins.__import__

    def reject_textual(name, *args, **kwargs):
        if name == "textual" or name.startswith("textual."):
            raise ImportError("simulated missing optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_textual)
    with pytest.raises(TextualUnavailableError, match="install PAOS with the 'tui' extra"):
        _require_textual()


def test_textual_dashboard_routes_input_through_existing_bus_and_closes_cleanly():
    async def exercise() -> None:
        bus = MessageBus()
        stopped = asyncio.Event()
        closed: list[bool] = []
        controller_calls: list[tuple[str, str]] = []

        class AgentLoop:
            async def run(self) -> None:
                await stopped.wait()

            def stop(self) -> None:
                stopped.set()

            async def close_mcp(self) -> None:
                closed.append(True)

        class Controller:
            def status(self, task_id: str) -> SimpleNamespace:
                controller_calls.append(("status", task_id))
                return SimpleNamespace(status="executing")

        app = build_textual_app(
            agent_loop=AgentLoop(),
            bus=bus,
            controller=Controller(),
            coordinator=_coordinator(),
            session_key="cli:direct",
        )
        async with app.run_test() as pilot:
            assert "task-rgb" in str(app.query_one("#tasks").render())
            assert app.query_one("#conversation") is not None
            assert app.query_one("#events") is not None
            await pilot.click("#input")
            await pilot.press("h", "e", "l", "l", "o", "enter")
            inbound = await asyncio.wait_for(bus.consume_inbound(), timeout=1)
            assert inbound.content == "hello"
            assert inbound.session_key == "cli:direct"
            assert inbound.metadata["event_type"] == "turn_submitted"
            await pilot.press(*"/task status task-rgb", "enter")
            assert controller_calls == [("status", "task-rgb")]
            await pilot.press("ctrl+c")

        assert closed == [True]

    asyncio.run(exercise())
