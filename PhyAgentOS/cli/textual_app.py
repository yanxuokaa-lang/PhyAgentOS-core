"""Optional Textual presentation layer for the PAOS Agent loop.

The dashboard is intentionally a view/controller adapter: task facts remain
owned by ``AgentTaskCoordinator`` and execution remains owned by AgentLoop and
LongHorizonTaskController.  Importing this module does not require Textual;
the dependency is loaded only when the dashboard is launched.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from PhyAgentOS.bus.events import InboundMessage


class TextualUnavailableError(RuntimeError):
    """Raised when the optional dashboard dependency is unavailable."""


def _task_rows(coordinator: Any, session_key: str) -> list[dict[str, Any]]:
    """Project persisted task/revision facts into bounded dashboard rows."""
    rows: list[dict[str, Any]] = []
    normalized_session_key = _session_identity(session_key)[2]
    for task in coordinator.store.find_by_origin_session_key(normalized_session_key):
        revision = task.active_revision
        settlements = {item.node_id: item.status for item in revision.node_settlements}
        persisted_status = task.status.value
        display_status = (
            "paused"
            if task.pause_requested and not task.terminal
            else persisted_status
        )
        rows.append({
            "task_id": task.task_id,
            "description": task.task_description,
            "status": display_status,
            "revision_id": task.active_revision_id,
            "revision_number": revision.number,
            "revision_count": len(task.revisions),
            "completed_count": sum(
                status == "completed" for status in settlements.values()
            ),
            "node_count": len(revision.plan_graph.nodes) if revision.plan_graph else 0,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "capability": node.capability,
                    "dependencies": list(node.dependencies),
                    # An un-settled node is pending until the authoritative
                    # reducer/admission path marks it ready. The view must not
                    # infer execution readiness from graph order alone.
                    "status": settlements.get(node.node_id, "pending"),
                }
                for node in (revision.plan_graph.nodes if revision.plan_graph else ())
            ],
            "clarification": (
                task.clarification_question
                if persisted_status == "waiting_for_user"
                else None
            ),
        })
    return rows


def _task_event_lines(coordinator: Any, session_key: str) -> list[str]:
    """Project persisted Coordinator events for the dashboard event pane."""
    lines: list[str] = []
    for row in _tasks_for_session(coordinator, _session_identity(session_key)[2]):
        task_id = row.task_id
        for event in coordinator.store.events(task_id, limit=100):
            payload = event.get("payload") or {}
            detail = " ".join(
                f"{key}={payload[key]}"
                for key in ("revision_id", "node_id", "status", "reason")
                if key in payload
            )
            suffix = f" {detail}" if detail else ""
            created_at = event.get("created_at")
            prefix = f"{created_at} " if created_at else ""
            lines.append(f"{prefix}{task_id} {event['event_type']}{suffix}")
    return lines


def _tasks_for_session(coordinator: Any, session_key: str) -> list[Any]:
    return list(coordinator.store.find_by_origin_session_key(session_key))


def _chat_id(session_key: str) -> str:
    return _session_identity(session_key)[1]


def _session_identity(session_key: str) -> tuple[str, str, str]:
    if ":" in session_key:
        channel, chat_id = session_key.split(":", 1)
    else:
        channel, chat_id = "cli", session_key
    return channel, chat_id, f"{channel}:{chat_id}"


def _require_textual():
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Footer, Header, Input, RichLog, Static
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise TextualUnavailableError(
            "Textual dashboard is optional; install PAOS with the 'tui' extra"
        ) from exc
    return App, ComposeResult, Horizontal, Vertical, Footer, Header, Input, RichLog, Static


def build_textual_app(*, agent_loop: Any, bus: Any, controller: Any, coordinator: Any, session_key: str):
    """Construct a Textual App around already-created PAOS runtime objects."""
    channel, chat_id, normalized_session_key = _session_identity(session_key)
    (
        app_type,
        _compose_result_type,
        horizontal_type,
        vertical_type,
        footer_type,
        header_type,
        input_type,
        rich_log_type,
        static_type,
    ) = _require_textual()

    class PAOSTextualApp(app_type):
        TITLE = "PhyAgentOS"
        BINDINGS = [("ctrl+c", "quit", "Quit")]
        CSS = """
        Screen { layout: vertical; }
        #conversation-pane, #task-pane { height: 1fr; border: round $primary; padding: 0 1; }
        #conversation-pane { width: 2fr; }
        #task-pane { width: 1fr; }
        #conversation, #events { height: 1fr; }
        .panel-title { height: 1; text-style: bold; color: $accent; }
        #input { dock: bottom; margin: 1 0; }
        """

        def compose(self):
            yield header_type()
            with horizontal_type():
                with vertical_type(id="conversation-pane"):
                    yield static_type("Conversation", classes="panel-title")
                    yield rich_log_type(id="conversation", markup=False, wrap=True)
                with vertical_type(id="task-pane"):
                    yield static_type("Tasks / DAG", classes="panel-title")
                    yield static_type("No AgentTask", id="tasks", markup=False)
            yield static_type("Events", classes="panel-title")
            yield rich_log_type(id="events", markup=False, wrap=True)
            yield input_type(
                placeholder="Message or /task status|start|pause|resume|stop|replay TASK_ID",
                id="input",
            )
            yield footer_type()

        async def on_mount(self) -> None:
            self._agent_task = asyncio.create_task(agent_loop.run())
            self._agent_task.add_done_callback(self._agent_finished)
            self._outbound_task = asyncio.create_task(self._consume_outbound())
            self._event_lines: set[str] = set()
            self._shutdown_started = False
            self.set_interval(1.0, self._refresh_tasks)
            self._refresh_tasks()
            self.query_one("#input", input_type).focus()

        def _agent_finished(self, task: asyncio.Task[Any]) -> None:
            if task.cancelled() or self._shutdown_started:
                return
            try:
                task.result()
            except Exception as exc:
                self.query_one("#events", rich_log_type).write(
                    f"agent loop error: {type(exc).__name__}: {exc}"
                )

        async def _consume_outbound(self) -> None:
            while True:
                try:
                    message = await bus.consume_outbound()
                except asyncio.CancelledError:
                    return
                if message.channel != channel or message.chat_id != chat_id:
                    continue
                metadata = message.metadata or {}
                event_type = metadata.get("event_type", "turn_completed")
                turn_id = metadata.get("turn_id")
                turn_prefix = f"[{turn_id}] " if turn_id else ""
                text = message.content or ""
                if metadata.get("_progress"):
                    self.query_one("#events", rich_log_type).write(
                        f"{turn_prefix}progress: {text}"
                    )
                elif event_type == "clarification_requested":
                    self.query_one("#conversation", rich_log_type).write(
                        f"PhyAgentOS clarification: {text}"
                    )
                    self.query_one("#events", rich_log_type).write(
                        f"{turn_prefix}waiting_for_user"
                    )
                elif text:
                    self.query_one("#conversation", rich_log_type).write(
                        f"PhyAgentOS: {text}"
                    )
                    self.query_one("#events", rich_log_type).write(
                        f"{turn_prefix}{event_type}"
                    )
                if metadata.get("task_id") or metadata.get("_long_horizon"):
                    self._refresh_tasks()

        def _refresh_tasks(self) -> None:
            rows = _task_rows(coordinator, normalized_session_key)
            if not rows:
                self.query_one("#tasks", static_type).update("No AgentTask")
            else:
                lines: list[str] = []
                for row in rows:
                    lines.append(f"{row['task_id']}  {row['status']}")
                    lines.append(f"  {row['description']}")
                    lines.append(
                        f"  revision {row['revision_number']}/{row['revision_count']} "
                        f"({row['revision_id']})  progress "
                        f"{row['completed_count']}/{row['node_count']}"
                    )
                    for node in row["nodes"]:
                        dependency_text = (
                            " <- " + ", ".join(node["dependencies"])
                            if node["dependencies"]
                            else ""
                        )
                        lines.append(
                            f"  [{node['status']}] {node['node_id']} "
                            f"({node['capability']}){dependency_text}"
                        )
                    if row["clarification"]:
                        lines.append(f"  ? {row['clarification']}")
                self.query_one("#tasks", static_type).update("\n".join(lines))

            event_log = self.query_one("#events", rich_log_type)
            for line in _task_event_lines(coordinator, normalized_session_key):
                if line not in self._event_lines:
                    event_log.write(line)
                    self._event_lines.add(line)

        async def on_input_submitted(self, event) -> None:
            value = event.value.strip()
            event.input.value = ""
            if not value:
                return
            if value in {"exit", "quit", "/exit", "/quit"}:
                await self._shutdown()
                self.exit()
                return
            if value.startswith("/task ") and controller is not None:
                await self._task_command(value)
                return
            turn_id = uuid4().hex
            self.query_one("#conversation", rich_log_type).write(f"You: {value}")
            self.query_one("#events", rich_log_type).write(f"[{turn_id}] thinking")
            await bus.publish_inbound(InboundMessage(
                channel=channel,
                sender_id="user",
                chat_id=chat_id,
                content=value,
                metadata={"turn_id": turn_id, "event_type": "turn_submitted"},
            ))

        async def _task_command(self, value: str) -> None:
            parts = value.split()
            if len(parts) != 3:
                self.query_one("#events", rich_log_type).write(
                    "usage: /task status|start|pause|resume|stop|replay TASK_ID"
                )
                return
            operation, task_id = parts[1].lower(), parts[2]
            try:
                if operation == "stop":
                    result = await controller.cancel(task_id, reason="textual_stop")
                elif operation in {"status", "start", "pause", "resume"}:
                    result = getattr(controller, operation)(task_id)
                elif operation == "replay":
                    result = controller.replay(task_id)
                else:
                    raise ValueError("unsupported task command")
                detail = result.status if hasattr(result, "status") else result
                self.query_one("#events", rich_log_type).write(f"{operation}: {detail}")
                self._refresh_tasks()
            except Exception as exc:
                self.query_one("#events", rich_log_type).write(f"task error: {exc}")

        async def _shutdown(self) -> None:
            if self._shutdown_started:
                return
            self._shutdown_started = True
            agent_loop.stop()
            tasks = [
                task for task in (
                    getattr(self, "_outbound_task", None),
                    getattr(self, "_agent_task", None),
                ) if task is not None and not task.done()
            ]
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await agent_loop.close_mcp()

        async def action_quit(self) -> None:
            await self._shutdown()
            self.exit()

        async def on_unmount(self) -> None:
            await self._shutdown()

    return PAOSTextualApp()


def run_textual_app(**kwargs: Any) -> None:
    """Run the optional dashboard; raises a clear install error if unavailable."""
    app = build_textual_app(**kwargs)
    app.run()


__all__ = [
    "TextualUnavailableError",
    "build_textual_app",
    "run_textual_app",
    "_task_rows",
    "_task_event_lines",
]
