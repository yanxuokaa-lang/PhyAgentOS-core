"""Task-state-driven outer loop over the PAOS planning adapter.

This module owns no task facts and no execution transport.  It coordinates
checkpointed calls to ``PlanningLoopAdapter`` so a UI can pause, resume, or
inspect a long-running AgentTask without creating a second scheduler.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from loguru import logger

from PhyAgentOS.agent.planning_context import PlanningContextUnavailableError
from PhyAgentOS.agent.planning_loop import PlanningLoopAdapter, PlanningLoopResult
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskStatus
from PhyAgentOS.planning import derive_ready_nodes


@dataclass(frozen=True)
class LongHorizonTaskResult:
    task_id: str
    status: str
    revision_id: str
    completed_nodes: tuple[str, ...] = ()
    revisions: int = 0
    replans: int = 0
    last_failure: str | None = None


class LongHorizonTaskController:
    """Drive one persisted AgentTask through checkpointed planning turns.

    The controller is deliberately a thin outer seam.  ``AgentTaskCoordinator``
    remains the lifecycle authority and ``PlanningLoopAdapter`` remains the
    only DAG executor.  ``pause()`` takes effect between semantic nodes; an
    in-flight Gateway Action is not cancelled by this method.
    """

    def __init__(
        self,
        coordinator: AgentTaskCoordinator,
        adapter: PlanningLoopAdapter | None = None,
        *,
        scene_revision_provider: Callable[[str], str],
        on_result: Callable[[LongHorizonTaskResult], Awaitable[None] | None] | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.adapter = adapter
        self.scene_revision_provider = scene_revision_provider
        self._locks: dict[str, asyncio.Lock] = {}
        self._runs: dict[str, asyncio.Task[LongHorizonTaskResult]] = {}
        self._on_result = on_result

    @classmethod
    def for_control(cls, coordinator: AgentTaskCoordinator) -> "LongHorizonTaskController":
        """Create a control-only facade for a UI process.

        Status and checkpoint controls do not need an execution adapter.  Keeping
        this seam on the same controller prevents a CLI/TUI from reaching into
        SQLite or creating a parallel task-control implementation.
        """
        return cls(coordinator, None, scene_revision_provider=lambda _task_id: "")

    def pause(self, task_id: str) -> LongHorizonTaskResult:
        """Request a pause at the next node checkpoint."""
        task = self.coordinator.request_pause(task_id)
        if task.terminal:
            return self._snapshot(task_id)
        return self._snapshot(task_id, status="paused")

    def resume(self, task_id: str) -> LongHorizonTaskResult:
        """Clear a pause request and wake an in-process runner when available."""
        self.coordinator.resume_task(task_id)
        self._ensure_started(task_id)
        return self._snapshot(task_id)

    def start(self, task_id: str) -> LongHorizonTaskResult:
        """Start one persisted task in the current event loop.

        This is only a lifecycle handle.  All task facts and node execution stay
        in the Coordinator and PlanningLoopAdapter respectively.
        """
        if self.adapter is None:
            raise RuntimeError("this controller is control-only; execution adapter is not configured")
        task = self.coordinator.get_task(task_id)
        if task.terminal:
            return self._snapshot(task_id)
        self._ensure_started(task_id)
        return self._snapshot(task_id)

    def stop(self, task_id: str, *, reason: str = "user_stop") -> LongHorizonTaskResult:
        """Request cancellation without pretending an in-flight Action stopped."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("task stop requires an active async event loop") from None
        loop.create_task(self.cancel(task_id, reason=reason))
        return self._snapshot(task_id, status="cancelling")

    async def cancel(self, task_id: str, *, reason: str = "user_stop") -> LongHorizonTaskResult:
        """Reconcile cancellation through the existing Coordinator authority."""
        await self.coordinator.cancel_task(task_id, reason=reason)
        run = self._runs.get(task_id)
        if run is not None and not run.done():
            # The adapter checkpoint observes the persisted cancellation state;
            # cancelling the asyncio task itself would hide in-flight outcomes.
            await asyncio.sleep(0)
        return self._snapshot(task_id)

    def replay(self, task_id: str) -> dict[str, tuple[str, ...]]:
        """Reducer-only replay; never invokes a Tool or Gateway transport."""
        task = self.coordinator.get_task(task_id)
        replay: dict[str, tuple[str, ...]] = {}
        for revision in task.revisions:
            graph = revision.plan_graph
            if graph is None:
                replay[revision.revision_id] = ()
                continue
            evidence = {
                ref
                for record in revision.execution_records
                for ref in record.evidence_refs
                if isinstance(ref, str)
            }
            for record in revision.execution_records:
                response = record.response
                payload = (
                    response.get("data")
                    if isinstance(response, dict) and isinstance(response.get("data"), dict)
                    else response
                )
                if isinstance(payload, dict) and isinstance(payload.get("evidence_refs"), (list, tuple, set)):
                    evidence.update(ref for ref in payload["evidence_refs"] if isinstance(ref, str))
            replay[revision.revision_id] = derive_ready_nodes(
                graph,
                {item.node_id: item.status for item in revision.node_settlements},
                evidence,
                {},
            )
        return replay

    def status(self, task_id: str) -> LongHorizonTaskResult:
        """Return persisted task/revision status without invoking a Tool."""
        return self._snapshot(task_id)

    async def run(self, task_id: str) -> LongHorizonTaskResult:
        """Run until a terminal, blocked, awaiting-replan, or paused state."""
        if self.adapter is None:
            raise RuntimeError("this controller is control-only; execution adapter is not configured")
        lock = self._locks.setdefault(task_id, asyncio.Lock())
        async with lock:
            task = self.coordinator.get_task(task_id)
            if task.terminal:
                return self._snapshot(task_id)
            if task.status == AgentTaskStatus.AWAITING_REPLAN:
                return self._snapshot(task_id, status="awaiting_replan")
            if task.pause_requested:
                return self._snapshot(task_id, status="paused")

            def checkpoint(current: str) -> bool:
                task = self.coordinator.get_task(current)
                return not task.pause_requested and not task.cancellation_requested
            try:
                scene_revision = self.scene_revision_provider(task_id)
                if not isinstance(scene_revision, str) or not scene_revision.strip():
                    raise ValueError("scene revision provider returned an empty value")
            except (PlanningContextUnavailableError, ValueError) as exc:
                # Missing trusted scene facts are a planning block, not a
                # runner crash.  The Agent can obtain observation evidence and
                # the user can resume the persisted task afterward.
                snapshot = self._snapshot(task_id)
                return LongHorizonTaskResult(
                    task_id=task_id,
                    status="blocked",
                    revision_id=snapshot.revision_id,
                    completed_nodes=snapshot.completed_nodes,
                    revisions=snapshot.revisions,
                    replans=snapshot.replans,
                    last_failure=str(exc),
                )
            result = await self.adapter.run(
                task_id,
                scene_revision=scene_revision,
                checkpoint=checkpoint,
            )
            final = self._from_planning_result(result)
            if self.coordinator.get_task(task_id).cancellation_requested:
                final = LongHorizonTaskResult(
                    task_id=final.task_id,
                    status=self.coordinator.get_task(task_id).status.value,
                    revision_id=final.revision_id,
                    completed_nodes=final.completed_nodes,
                    revisions=final.revisions,
                    replans=final.replans,
                    last_failure=final.last_failure,
                )
            return final

    def _ensure_started(self, task_id: str) -> None:
        if self.adapter is None:
            return
        existing = self._runs.get(task_id)
        if existing is not None and not existing.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # CLI control commands can clear a pause outside the runner process;
            # a later TUI/worker start will resume the persisted task.
            return
        run = loop.create_task(self.run(task_id), name=f"paos-long-horizon:{task_id}")
        self._runs[task_id] = run

        def completed(done: asyncio.Task[LongHorizonTaskResult]) -> None:
            self._runs.pop(task_id, None)
            if done.cancelled():
                return
            try:
                result = done.result()
            except Exception as exc:
                if self._on_result is not None:
                    snapshot = self._snapshot(task_id)
                    callback = self._on_result(LongHorizonTaskResult(
                        task_id=task_id,
                        status="failed",
                        revision_id=snapshot.revision_id,
                        completed_nodes=snapshot.completed_nodes,
                        revisions=snapshot.revisions,
                        replans=snapshot.replans,
                        last_failure=f"{type(exc).__name__}: {exc}",
                    ))
                    if hasattr(callback, "__await__"):
                        loop.create_task(callback)  # type: ignore[arg-type]
                else:
                    logger.error(
                        "Long-horizon runner failed without result callback: task_id={} error={}",
                        task_id,
                        exc,
                    )
                return
            if self._on_result is None:
                return
            callback = self._on_result(result)
            if hasattr(callback, "__await__"):
                loop.create_task(callback)  # type: ignore[arg-type]

        run.add_done_callback(completed)

    def _from_planning_result(self, result: PlanningLoopResult) -> LongHorizonTaskResult:
        return LongHorizonTaskResult(
            task_id=result.task_id,
            status=result.status,
            revision_id=self.coordinator.get_task(result.task_id).active_revision_id,
            completed_nodes=result.completed_nodes,
            revisions=result.revisions,
            replans=result.replans,
            last_failure=result.last_failure,
        )

    def _snapshot(self, task_id: str, *, status: str | None = None) -> LongHorizonTaskResult:
        task = self.coordinator.get_task(task_id)
        return LongHorizonTaskResult(
            task_id=task_id,
            status=status or ("paused" if task.pause_requested else task.status.value),
            revision_id=task.active_revision_id,
            completed_nodes=tuple(
                item.node_id for item in task.active_revision.node_settlements
                if item.status == "completed"
            ),
            revisions=len(task.revisions),
            replans=max(0, sum(item.counts_toward_replan_budget for item in task.revisions) - 1),
        )


__all__ = ["LongHorizonTaskController", "LongHorizonTaskResult"]
