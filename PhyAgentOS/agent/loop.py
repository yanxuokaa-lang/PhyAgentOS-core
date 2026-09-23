"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections.abc import Mapping, MutableSet
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from loguru import logger

from PhyAgentOS.agent.context import ContextBuilder
from PhyAgentOS.agent.memory import MemoryConsolidator
from PhyAgentOS.agent.prompt_context import (
    AgentPromptContextManager,
    PromptBudgetExceededError,
)
from PhyAgentOS.agent.subagent import SubagentManager
from PhyAgentOS.agent.tools.agent import AgentModeTool
from PhyAgentOS.agent.tools.cron import CronTool
from PhyAgentOS.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from PhyAgentOS.agent.tools.image import ImageTool
from PhyAgentOS.agent.tools.message import MessageTool
from PhyAgentOS.agent.tools.registry import ToolRegistry
from PhyAgentOS.agent.tools.scene_graph import SceneGraphQueryTool
from PhyAgentOS.agent.tools.shell import ExecTool
from PhyAgentOS.agent.tools.spawn import SpawnTool
from PhyAgentOS.agent.tools.web import WebFetchTool, WebSearchTool
from PhyAgentOS.bus.events import InboundMessage, OutboundMessage
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.embodiment_registry import EmbodimentRegistry
from PhyAgentOS.forge.task import AgentTaskError
from PhyAgentOS.providers.base import LLMProvider
from PhyAgentOS.providers.providers_manager import ProvidersManager
from PhyAgentOS.session.manager import Session, SessionManager
from PhyAgentOS.utils.helpers import estimate_prompt_tokens_chain

if TYPE_CHECKING:
    from PhyAgentOS.agent.experience.coordinator import EpisodeClosedHook
    from PhyAgentOS.agent.long_horizon import LongHorizonTaskController
    from PhyAgentOS.agent.planner_plugin import PlannerPlugin
    from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
    from PhyAgentOS.config.schema import AgentEvolutionConfig, ChannelsConfig, ExecToolConfig
    from PhyAgentOS.cron.service import CronService
    from PhyAgentOS.forge.task import AgentTaskCoordinator
    from PhyAgentOS.forge.tool_client import ForgeToolClient
    from PhyAgentOS.planning import AdmissionContext


@dataclass(frozen=True)
class AgentLoopRunResult:
    """One bounded model/tool loop result with explicit provider-failure state."""

    content: str | None
    tools_used: list[str]
    messages: list[dict[str, Any]]
    turn_failure_code: str | None = None
    model_failure_code: str | None = None

    def __iter__(self):
        """Preserve the historical private-loop tuple unpacking contract."""

        yield self.content
        yield self.tools_used
        yield self.messages


_NODE_TURN_ALLOWED_TOOLS = frozenset({
    "forge_plan_ready",
    "forge_plan_select",
    "forge_tool_context",
    "forge_tool_query",
    "forge_tool_start_action",
    "forge_tool_start_session",
})

_NODE_TURN_EXECUTION_TOOLS = frozenset({
    "forge_tool_query",
    "forge_tool_start_action",
    "forge_tool_start_session",
})


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _TOOL_RESULT_MAX_CHARS = 16_000

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        turn_timeout_s: float = 300.0,
        context_window_tokens: int = 272_000,
        context_compaction_trigger_tokens: int | None = None,
        brave_api_key: str | None = None,
        web_proxy: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        channels_config: ChannelsConfig | None = None,
        embodiment_registry: EmbodimentRegistry | None = None,
        forge_tool_client: ForgeToolClient | None = None,
        forge_tool_invocation_ids: MutableSet[str] | None = None,
        forge_task_coordinator: AgentTaskCoordinator | None = None,
        runtime_availability_provider: Callable[[str], bool] | None = None,
        evolution_config: AgentEvolutionConfig | None = None,
        evolution_provider: LLMProvider | None = None,
        evolution_model: str | None = None,
        evolution_extension: EpisodeClosedHook | None = None,
        planning_dispatch: AgentComposedDispatch | None = None,
        planning_context_provider: Callable[[str], AdmissionContext] | None = None,
        planner_plugin: PlannerPlugin | None = None,
    ):
        from PhyAgentOS.config.schema import ExecToolConfig

        self.bus = bus
        self.channels_config = channels_config
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.turn_timeout_s = max(1.0, float(turn_timeout_s))
        self.context_window_tokens = context_window_tokens
        self.context_compaction_trigger_tokens = (
            int(context_compaction_trigger_tokens)
            if context_compaction_trigger_tokens is not None
            else max(1, int(context_window_tokens * 0.95))
        )
        self.brave_api_key = brave_api_key
        self.web_proxy = web_proxy
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self.forge_tool_client = forge_tool_client
        self.forge_tool_invocation_ids = forge_tool_invocation_ids
        self.forge_task_coordinator = forge_task_coordinator
        self._planning_dispatch = planning_dispatch
        self._planning_context_provider = planning_context_provider
        self._planner_plugin = planner_plugin
        self.long_horizon_controller: LongHorizonTaskController | None = None
        binding_resolver = (
            forge_task_coordinator.binding_resolver if forge_task_coordinator is not None else None
        )

        self.experience = None
        if evolution_config is not None and evolution_config.enabled:
            try:
                from PhyAgentOS.agent.experience.analyzer import ModelExperienceAnalyzer
                from PhyAgentOS.agent.experience.coordinator import ExperienceCoordinator
                from PhyAgentOS.agent.experience.evolution_composition import (
                    compose_evolution_extension,
                )

                self.experience = ExperienceCoordinator(
                    workspace=workspace,
                    analyzer=ModelExperienceAnalyzer(
                        provider=evolution_provider or provider,
                        model=evolution_model or model or provider.get_default_model(),
                    ),
                    task_coordinator=forge_task_coordinator,
                    runtime_availability_provider=runtime_availability_provider,
                    binding_resolver=binding_resolver,
                    min_successful_episodes=evolution_config.min_successful_episodes,
                    min_lesson_episodes=evolution_config.min_lesson_episodes,
                    max_lessons_per_skill=evolution_config.max_lessons_per_skill,
                    max_calls=evolution_config.max_evolution_calls_per_run,
                    evolution_extension=None,
                )
                compose_evolution_extension(self.experience, extension=evolution_extension)
            except Exception as exc:
                logger.warning(
                    "Experience evolution initialization failed open: error_type={}",
                    type(exc).__name__,
                )

        if self.experience is not None:
            self.skill_activation = self.experience.activation
        else:
            from PhyAgentOS.agent.experience.activation import SkillActivationManager
            from PhyAgentOS.agent.experience.store import ExperienceStore

            self.skill_activation = SkillActivationManager(
                workspace=workspace,
                store=ExperienceStore(workspace),
                runtime_availability_provider=runtime_availability_provider,
                binding_resolver=binding_resolver,
            )

        self.context = ContextBuilder(
            workspace,
            forge_context_provider=(
                forge_task_coordinator.capabilities_summary
                if forge_task_coordinator is not None
                else None
            ),
            evolution_enabled=(
                self.experience is not None or self.forge_task_coordinator is not None
            ),
            runtime_availability_provider=runtime_availability_provider,
        )
        if self.forge_task_coordinator is not None:
            self.forge_task_coordinator.set_experience(self.experience)
            self.forge_task_coordinator.set_activation_manager(self.skill_activation)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.embodiment_registry = embodiment_registry
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
            web_proxy=web_proxy,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._forge_reconciled = False
        self._active_tasks: dict[str, list[asyncio.Task]] = {}  # session_key -> tasks
        self._processing_lock = asyncio.Lock()
        self.memory_consolidator = MemoryConsolidator(
            workspace=workspace,
            provider=provider,
            model=self.model,
            sessions=self.sessions,
            context_window_tokens=context_window_tokens,
            compaction_trigger_tokens=self.context_compaction_trigger_tokens,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_definitions,
        )
        self.prompt_context = AgentPromptContextManager(
            context_window_tokens=context_window_tokens,
            compaction_trigger_tokens=self.context_compaction_trigger_tokens,
            reserved_output_tokens=provider.generation.max_tokens,
        )
        self._register_default_tools()
        # Load env variables
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=self.workspace / ".env")
        except Exception:
            logger.warning("Failed to load .env file, ignore using env variables")

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(
            ExecTool(
                working_dir=str(self.workspace),
                timeout=self.exec_config.timeout,
                restrict_to_workspace=self.restrict_to_workspace,
                path_append=self.exec_config.path_append,
            )
        )
        self.tools.register(WebSearchTool(api_key=self.brave_api_key, proxy=self.web_proxy))
        self.tools.register(WebFetchTool(proxy=self.web_proxy))
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents))
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))
        if isinstance(self.provider, ProvidersManager):
            self.tools.register(AgentModeTool(self.provider))
            self.tools.register(ImageTool(self.provider, send_callback=self.bus.publish_outbound))

        self.tools.register(SceneGraphQueryTool(workspace=self.workspace))
        from PhyAgentOS.agent.tools.skill_activation import ActivateSkillTool

        self.tools.register(ActivateSkillTool(self.skill_activation))
        if self.forge_task_coordinator is not None:
            from PhyAgentOS.agent.tools.forge_task import build_forge_task_tools
            from PhyAgentOS.agent.tools.planning import ForgePlanActivateTool, ForgePlanSelectTool

            for tool in build_forge_task_tools(self.forge_task_coordinator):
                self.tools.register(tool)
            self.tools.register(
                ForgePlanActivateTool(
                    self.forge_task_coordinator,
                    self.set_planning_dispatch,
                    self._planning_context_provider,
                )
            )
            self.tools.register(
                ForgePlanSelectTool(
                    self.forge_task_coordinator,
                    lambda: self._planning_dispatch,
                )
            )
        if self.forge_tool_client is not None:
            from PhyAgentOS.agent.tools.forge_tool_api import build_forge_tool_api_tools

            for tool in build_forge_tool_api_tools(
                self.forge_tool_client,
                invocation_ids=self.forge_tool_invocation_ids,
                coordinator=self.forge_task_coordinator,
            ):
                self.tools.register(tool)
        if self._planning_dispatch is not None:
            from PhyAgentOS.agent.tools.planning import ForgePlanReadyTool

            self.tools.register(ForgePlanReadyTool(self._planning_dispatch, self.forge_task_coordinator))
            self.tools.set_execution_guard(self._planning_guard)

    def set_planning_dispatch(self, dispatch: AgentComposedDispatch | None) -> None:
        """Attach or detach an agent-composed planning bridge at runtime.

        This changes only the AgentLoop adapter surface.  It does not create a
        task, mutate a PlanRevision, or execute a Gateway call.
        """
        self._planning_dispatch = dispatch
        self.tools.unregister("forge_plan_ready")
        self.tools.set_execution_guard(self._planning_guard if dispatch is not None else None)
        if dispatch is not None:
            from PhyAgentOS.agent.tools.planning import ForgePlanReadyTool

            self.tools.register(ForgePlanReadyTool(dispatch, self.forge_task_coordinator))

    def set_long_horizon_controller(self, controller: Any | None) -> None:
        """Attach the host-owned long-horizon lifecycle seam to this AgentLoop."""
        self.long_horizon_controller = controller

    def activate_planning_task(self, task_id: str) -> None:
        """Activate admission for one task immediately before a node turn.

        Node execution must never rely on a stale dispatch left by a previous
        chat turn.  The dispatch remains a pure admission facade; lifecycle and
        execution facts stay owned by their existing components.
        """
        if self.forge_task_coordinator is None:
            raise RuntimeError("planning activation requires a Forge task coordinator")
        if self._planning_context_provider is None:
            raise RuntimeError("planning activation requires a trusted planning context provider")
        from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch

        task = self.forge_task_coordinator.get_task(task_id)
        self.set_planning_dispatch(
            AgentComposedDispatch.from_task(
                task,
                context_provider=self._planning_context_provider,
            )
        )

    def start_ready_long_horizon_tasks(self, session_key: str) -> tuple[str, ...]:
        """Start materialized tasks created by the current user turn."""
        controller = self.long_horizon_controller
        coordinator = self.forge_task_coordinator
        if controller is None or coordinator is None:
            return ()
        started: list[str] = []
        for task in coordinator.store.find_by_origin_session_key(session_key):
            if task.terminal or task.active_revision.plan_graph is None:
                continue
            controller.start(task.task_id)
            started.append(task.task_id)
        return tuple(started)

    async def wait_for_long_horizon_tasks(self, session_key: str) -> tuple[Any, ...]:
        """Wait for tasks started by one direct/one-shot turn.

        Interactive transports keep the existing background behavior; callers
        that own the process lifetime (the one-shot CLI) use this explicit join
        before closing MCP/Gateway clients.
        """
        controller = self.long_horizon_controller
        coordinator = self.forge_task_coordinator
        if controller is None or coordinator is None or not callable(getattr(controller, "wait", None)):
            return ()
        results = []
        for task in coordinator.store.find_by_origin_session_key(session_key):
            if task.terminal or task.active_revision.plan_graph is None:
                continue
            results.append(await controller.wait(task.task_id))
        return tuple(results)

    def build_long_horizon_controller(self, *, on_result=None, on_progress=None):
        """Build the thin outer controller when a trusted context provider exists.

        The provider is deliberately required for execution: fabricating a
        scene revision in the TUI would turn a chat convenience into an
        authority bypass.  Without it callers still receive the control facade.
        """
        from PhyAgentOS.agent.long_horizon import LongHorizonTaskController

        if self.forge_task_coordinator is None:
            return None
        if self._planning_context_provider is None:
            return LongHorizonTaskController.for_control(self.forge_task_coordinator)
        from PhyAgentOS.agent.planning_loop import (
            AgentLoopNodeExecutor,
            NodeContextProvider,
            PlanningLoopAdapter,
        )

        planner = self._planner_plugin
        replan_proposer = None
        recovery_policy = None
        if planner is not None:
            def propose_replan(graph, settlement, delta, context):
                return planner.propose_replan(
                    graph=graph,
                    settlement=settlement,
                    delta=delta,
                    context=context,
                )

            replan_proposer = propose_replan
            select_recovery = getattr(planner, "select_recovery", None)
            if callable(select_recovery):
                def choose_recovery(graph, settlement, delta, context):
                    return select_recovery(
                        graph=graph,
                        settlement=settlement,
                        delta=delta,
                        context=context,
                    )

                recovery_policy = choose_recovery

        adapter = PlanningLoopAdapter(
            self.forge_task_coordinator,
            context_provider=NodeContextProvider(self.forge_task_coordinator.get_task),
            node_executor=AgentLoopNodeExecutor(
                self,
                self.forge_task_coordinator,
                on_progress=on_progress,
            ),
            admission_context_provider=self._planning_context_provider,
            replan_proposer=replan_proposer,
            recovery_policy=recovery_policy,
            finalize_completed_graph=False,
        )
        return LongHorizonTaskController(
            self.forge_task_coordinator,
            adapter,
            scene_revision_provider=lambda task_id: (
                self._planning_context_provider(task_id).scene_revision
            ),
            on_result=on_result,
            segment_continuation=lambda task_id: self.run_segment_continuation_turn(
                task_id=task_id,
                on_progress=on_progress,
            ),
        )

    def _planning_guard(self, name: str, arguments: dict) -> str | None:
        if self._planning_dispatch is None:
            return None
        if self._allows_pre_graph_discovery_query(name, arguments):
            return None
        try:
            semantics = {
                "forge_tool_query": "query", "forge_tool_start_action": "action",
                "forge_tool_start_session": "session",
            }.get(name)
            task_id = arguments.get("task_id")
            task = (
                self.forge_task_coordinator.get_task(task_id)
                if semantics and task_id is not None else None
            )
            active_graph = getattr(getattr(task, "active_revision", None), "plan_graph", None)
            if semantics and active_graph is not None and (
                semantics in {"action", "session"}
                or arguments.get("use_selected_arguments") is True
            ):
                binding = self.forge_task_coordinator.selected_execution_binding(
                    arguments.get("task_id"),
                    arguments.get("tool_id"),
                    semantics,
                    arguments.get("planning_binding"),
                )
                arguments = {
                    **arguments,
                    "planning_binding": binding.model_dump(mode="json"),
                    "arguments": self.forge_task_coordinator.selected_execution_arguments(
                        arguments.get("task_id"), arguments.get("tool_id"), semantics,
                        {}, binding.model_dump(mode="json"),
                    ),
                }
            decision = self._planning_dispatch.admit_forge_tool(name, arguments)
        except Exception as exc:
            return json.dumps(
                {
                    "ok": False,
                    "error": {
                        "type": "planning_admission",
                        "code": "context_unavailable",
                        "detail": str(exc),
                        "motion_authorized": False,
                    },
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if decision is None or decision.allowed:
            return None
        return json.dumps(
            {
                "ok": False,
                "error": {
                    "type": "planning_admission",
                    "code": decision.code,
                    "detail": decision.detail,
                    "node_id": decision.node_id,
                    "tool_id": decision.tool_id,
                    "motion_authorized": False,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _allows_pre_graph_discovery_query(self, name: str, arguments: dict) -> bool:
        """Allow the governed first observation when an old dispatch is stale.

        A planning dispatch is installed for the active task and can outlive
        that task until the next explicit activation.  Discovery intentionally
        happens before a semantic PlanGraph exists, so a stale dispatch must
        not turn the first read-only ``scene.observe`` into a cross-task
        identity failure.  This exception is deliberately narrow: it applies
        only to a non-terminal task with no graph, the declared observation
        Query, and no planning binding.  Actions and graph-bound calls still
        flow through normal admission.
        """
        if name != "forge_tool_query" or self.forge_task_coordinator is None:
            return False
        if arguments.get("tool_id") != "scene.observe":
            return False
        task_id = arguments.get("task_id")
        if not isinstance(task_id, str) or arguments.get("planning_binding") is not None:
            return False
        dispatch_task_id = getattr(getattr(self._planning_dispatch, "graph", None), "task_id", None)
        if not isinstance(dispatch_task_id, str) or task_id == dispatch_task_id:
            return False
        try:
            task = self.forge_task_coordinator.get_task(task_id)
        except Exception:
            return False
        revision = getattr(task, "active_revision", None)
        return (
            getattr(task, "terminal", False) is False
            and revision is not None
            and getattr(revision, "plan_graph", None) is None
        )

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if not self._forge_reconciled and self.forge_task_coordinator is not None:
            await self.forge_task_coordinator.reconcile_nonterminal()
            self._forge_reconciled = True
        if self.experience is not None:
            await self.experience.start()
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from PhyAgentOS.agent.tools.mcp import connect_mcp_servers

        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(
        self,
        channel: str,
        chat_id: str,
        message_id: str | None = None,
        session_key: str | None = None,
    ) -> None:
        """Update context for all tools that need routing info."""
        for name in ("message", "spawn", "cron"):
            if tool := self.tools.get(name):
                if hasattr(tool, "set_context"):
                    tool.set_context(channel, chat_id, *([message_id] if name == "message" else []))
        if tool := self.tools.get("forge_task_create"):
            tool.set_context(session_key or f"{channel}:{chat_id}")
        if tool := self.tools.get("activate_skill"):
            tool.set_context(session_key or f"{channel}:{chat_id}")

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""

        def _fmt(tc):
            args = (tc.arguments[0] if isinstance(tc.arguments, list) else tc.arguments) or {}
            val = next(iter(args.values()), None) if isinstance(args, dict) else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'

        return ", ".join(_fmt(tc) for tc in tool_calls)

    def _task_for_session(
        self, session_key: str | None, *, include_terminal: bool = True
    ) -> Any | None:
        if self.forge_task_coordinator is None or session_key is None:
            return None
        tasks = self.forge_task_coordinator.store.find_by_origin_session_key(
            session_key
        )
        nonterminal = [task for task in tasks if not task.terminal]
        if nonterminal:
            return nonterminal[-1]
        if include_terminal and tasks:
            return tasks[-1]
        legacy = self._legacy_task_for_session(session_key)
        if legacy is not None and (include_terminal or not legacy.terminal):
            return legacy
        return None

    def _legacy_task_for_session(self, session_key: str) -> Any | None:
        """Resolve only a legacy task explicitly referenced by this session."""
        history = self.sessions.get_or_create(session_key).get_history(max_messages=0)
        for message in reversed(history):
            if message.get("role") != "assistant":
                continue
            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            for call in reversed(tool_calls):
                if not isinstance(call, Mapping):
                    continue
                function = call.get("function")
                if not isinstance(function, Mapping) or function.get("name") != "forge_task_get":
                    continue
                arguments = function.get("arguments")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        continue
                if not isinstance(arguments, Mapping):
                    continue
                task_id = arguments.get("task_id")
                if not isinstance(task_id, str) or not task_id:
                    continue
                try:
                    task = self.forge_task_coordinator.store.get(task_id)
                except AgentTaskError:
                    continue
                if task.origin_session_key is None:
                    return task
        return None

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., Awaitable[None]] | None = None,
        experience_session_key: str | None = None,
        active_task_id: str | None = None,
        projection_scope: str = "task",
        projection_node_id: str | None = None,
        allowed_tool_names: frozenset[str] | None = None,
        yield_after_tools: frozenset[str] = frozenset(),
        decision_timeout_s: float | None = None,
    ) -> AgentLoopRunResult:
        """Run the agent iteration loop."""
        messages = initial_messages
        turn_start_index = max(
            (index for index, message in enumerate(messages) if message.get("role") == "user"),
            default=max(0, len(messages) - 1),
        )
        iteration = 0
        final_content = None
        turn_failure_code = None
        model_failure_code = None
        tools_used: list[str] = []
        decision_deadline = (
            monotonic() + decision_timeout_s if decision_timeout_s is not None else None
        )

        async def bounded_decision(operation):
            if decision_deadline is None:
                return await operation
            return await asyncio.wait_for(operation, timeout=max(0, decision_deadline - monotonic()))

        def decision_timeout_result():
            return AgentLoopRunResult(
                content="Node decision turn timed out; persisted execution facts remain authoritative.",
                tools_used=tools_used, messages=messages, turn_failure_code="turn_timeout",
            )

        while iteration < self.max_iterations:
            iteration += 1

            prompt_tool_names = self.tools.tool_names
            if allowed_tool_names is not None:
                prompt_tool_names = tuple(
                    name for name in prompt_tool_names if name in allowed_tool_names
                )

            active_task = (
                self.forge_task_coordinator.get_task(active_task_id)
                if active_task_id is not None and self.forge_task_coordinator is not None
                else self._task_for_session(experience_session_key)
            )

            def estimate(request_messages, visible_names):
                definitions = self.tools.get_definitions(set(visible_names))
                return estimate_prompt_tokens_chain(
                    self.provider, self.model, request_messages, definitions
                )[0]

            try:
                request_view = self.prompt_context.build(
                    messages=messages,
                    turn_start_index=turn_start_index,
                    all_tool_names=prompt_tool_names,
                    task=active_task,
                    estimate_tokens=estimate,
                    projection_scope=projection_scope,
                    projection_node_id=projection_node_id,
                )
            except PromptBudgetExceededError as exc:
                logger.error("Agent prompt budget exceeded: {}", exc)
                turn_failure_code = "prompt_budget_exceeded"
                final_content = str(exc)
                break
            visible_tool_names = request_view.visible_tool_names
            if allowed_tool_names is not None:
                visible_tool_names = tuple(
                    name for name in visible_tool_names if name in allowed_tool_names
                )
            tool_defs = self.tools.get_definitions(set(visible_tool_names))
            estimated_tokens, token_source = estimate_prompt_tokens_chain(
                self.provider, self.model, request_view.messages, tool_defs
            )
            logger.info(
                "Agent prompt context session={} iteration={} phase={} tokens={}/{} "
                "window={} trigger={} output_reserve={} source={} tools={} compacted={}",
                experience_session_key,
                iteration,
                request_view.phase,
                estimated_tokens,
                self.prompt_context.prompt_token_limit,
                self.context_window_tokens,
                self.context_compaction_trigger_tokens,
                self.prompt_context.reserved_output_tokens,
                token_source,
                len(tool_defs),
                request_view.compacted,
            )

            started = monotonic()
            logger.info("Agent model start session={} iteration={}", experience_session_key, iteration)
            if on_progress:
                await on_progress(
                    f"Model request started: phase={request_view.phase}, "
                    f"prompt≈{estimated_tokens} tokens, iteration={iteration}.",
                    tool_hint=False,
                )
            try:
                response = await bounded_decision(self.provider.chat_with_retry(
                    messages=request_view.messages,
                    tools=tool_defs,
                    model=self.model,
                ))
            except asyncio.TimeoutError:
                return decision_timeout_result()
            except asyncio.CancelledError:
                logger.warning("Agent model cancelled session={} iteration={}", experience_session_key, iteration)
                raise
            finally:
                logger.info("Agent model exit session={} iteration={} elapsed_s={:.3f}",
                            experience_session_key, iteration, monotonic() - started)

            timing = response.timing
            if timing is not None:
                headers = (
                    f"{timing.request_to_headers_s:.3f}s"
                    if timing.request_to_headers_s is not None
                    else "unavailable"
                )
                first_token = (
                    f"{timing.time_to_first_token_s:.3f}s"
                    if timing.time_to_first_token_s is not None
                    else "unavailable"
                )
                logger.info(
                    "Agent model timing session={} iteration={} "
                    "request_to_headers={} first_token={} complete_s={:.3f} mode={}",
                    experience_session_key,
                    iteration,
                    headers,
                    first_token,
                    timing.complete_response_s,
                    timing.observation_mode,
                )
                if on_progress:
                    await on_progress(
                        "Model request timing: "
                        f"headers={headers}, first_token={first_token}, "
                        f"complete={timing.complete_response_s:.3f}s.",
                        tool_hint=False,
                    )

            if response.has_tool_calls:
                if on_progress:
                    thought = self._strip_think(response.content)
                    if thought:
                        await on_progress(thought)
                    await on_progress(self._tool_hint(response.tool_calls), tool_hint=True)

                tool_call_dicts = [tc.to_openai_tool_call() for tc in response.tool_calls]
                messages = self.context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )

                yield_to_host = False
                for call_index, tool_call in enumerate(response.tool_calls):
                    if (
                        projection_scope == "node"
                        and tool_call.name == "forge_plan_ready"
                        and tool_call.arguments.get("source_record_id") is not None
                        and tool_call.arguments.get("node_id") != projection_node_id
                    ):
                        messages = self.context.add_tool_result(
                            messages, tool_call.id, tool_call.name,
                            json.dumps({"ok": False, "error": {
                                "code": "source_node_out_of_scope",
                                "message": "Browse sources only for the current node: " + str(projection_node_id),
                            }, "motion_authorized": False}),
                        )
                        continue
                    if (
                        allowed_tool_names is not None
                        and tool_call.name not in allowed_tool_names
                    ):
                        messages = self.context.add_tool_result(
                            messages,
                            tool_call.id,
                            tool_call.name,
                            json.dumps(
                                {
                                    "ok": False,
                                    "error": {
                                        "type": "tool_not_available_in_turn",
                                        "message": (
                                            f"{tool_call.name} is not available in this "
                                            "bounded Agent turn."
                                        ),
                                    },
                                    "motion_authorized": False,
                                },
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        )
                        continue
                    tools_used.append(tool_call.name)
                    if experience_session_key is not None:
                        self.skill_activation.record_tool(
                            experience_session_key, tool_call.name, tool_call.arguments
                        )
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
                    started = monotonic()
                    logger.info("Agent tool start session={} iteration={} call_id={} tool={}",
                                experience_session_key, iteration, tool_call.id, tool_call.name)
                    try:
                        if tool_call.name in yield_after_tools:
                            # A governed execution has its own Tool budget and is
                            # reconciled from durable facts by the node executor.
                            if decision_deadline is not None and monotonic() >= decision_deadline:
                                return decision_timeout_result()
                            result = await self.tools.execute(tool_call.name, tool_call.arguments)
                        else:
                            result = await bounded_decision(self.tools.execute(tool_call.name, tool_call.arguments))
                    except asyncio.TimeoutError:
                        return decision_timeout_result()
                    except asyncio.CancelledError:
                        logger.warning("Agent tool cancelled session={} iteration={} call_id={} tool={}",
                                       experience_session_key, iteration, tool_call.id, tool_call.name)
                        raise
                    finally:
                        logger.info("Agent tool exit session={} iteration={} call_id={} elapsed_s={:.3f}",
                                    experience_session_key, iteration, tool_call.id, monotonic() - started)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                    if (
                        projection_scope == "node"
                        and tool_call.name == "forge_plan_select"
                        and self._tool_result_requires_replan(result)
                    ):
                        for deferred in response.tool_calls[call_index + 1 :]:
                            messages = self.context.add_tool_result(
                                messages,
                                deferred.id,
                                deferred.name,
                                json.dumps(
                                    {
                                        "ok": False,
                                        "status": "deferred_to_replan",
                                        "error": {
                                            "type": "control_handoff",
                                            "message": (
                                                "Tool was not executed because the persisted "
                                                "recovery lifecycle now owns the next step."
                                            ),
                                        },
                                        "motion_authorized": False,
                                    },
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                            )
                        final_content = (
                            "Planning selection requires a replacement plan segment; "
                            "returning control to the persisted recovery lifecycle."
                        )
                        yield_to_host = True
                        break
                    if (
                        tool_call.name in yield_after_tools
                        and self._tool_result_succeeded(result)
                    ):
                        for deferred in response.tool_calls[call_index + 1 :]:
                            messages = self.context.add_tool_result(
                                messages,
                                deferred.id,
                                deferred.name,
                                json.dumps(
                                    {
                                        "ok": False,
                                        "status": "deferred_to_long_horizon",
                                        "error": {
                                            "type": "control_handoff",
                                            "message": (
                                                "Tool was not executed because the persisted "
                                                "planning lifecycle now owns the next step."
                                            ),
                                        },
                                        "motion_authorized": False,
                                    },
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                            )
                        final_content = (
                            f"{tool_call.name} succeeded; continuing through the "
                            "persisted long-horizon planning loop."
                        )
                        yield_to_host = True
                        break
                if yield_to_host:
                    break
            else:
                clean = self._strip_think(response.content)
                # Don't persist error responses to session history — they can
                # poison the context and cause permanent 400 loops (#1303).
                if response.finish_reason == "error":
                    logger.error("LLM returned error: {}", (clean or "")[:200])
                    model_failure_code = self.provider.classify_error(clean)
                    turn_failure_code = model_failure_code
                    if on_progress:
                        await on_progress(
                            f"Model request stopped: {model_failure_code}.",
                            tool_hint=False,
                        )
                    final_content = clean or "Sorry, I encountered an error calling the AI model."
                    break
                messages = self.context.add_assistant_message(
                    messages,
                    clean,
                    reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )
                final_content = clean
                break

        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            final_content = (
                f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                "without completing the task. You can try breaking the task into smaller steps."
            )

        return AgentLoopRunResult(
            content=final_content,
            tools_used=tools_used,
            messages=messages,
            turn_failure_code=turn_failure_code,
            model_failure_code=model_failure_code,
        )

    @staticmethod
    def _tool_result_succeeded(result: str) -> bool:
        try:
            payload = json.loads(result)
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(payload, dict) and payload.get("ok") is True

    @staticmethod
    def _tool_result_requires_replan(result: str) -> bool:
        """Recognize an explicit selection handoff without another model request."""
        try:
            payload = json.loads(result)
        except (TypeError, json.JSONDecodeError):
            return False
        error = payload.get("error") if isinstance(payload, dict) else None
        return isinstance(error, dict) and error.get("requires_replan") is True

    async def run_node_turn(
        self,
        *,
        task_id: str,
        revision_id: str,
        node_id: str,
        prompt: str,
        on_progress: Callable[..., Awaitable[None]] | None = None,
    ) -> AgentLoopRunResult:
        """Run one semantic-node turn through the existing AgentLoop.

        The caller supplies a bounded prompt projection (including any
        predecessor context). Tool execution remains governed by the normal
        registry and optional ``AgentComposedDispatch`` guard.
        """
        if not all(
            isinstance(value, str) and value.strip()
            for value in (task_id, revision_id, node_id, prompt)
        ):
            raise ValueError(
                "node turn requires non-empty task, revision, node, and prompt identities"
            )
        node_session_key = f"agent_task:{task_id}"
        if self.forge_task_coordinator is not None:
            task = self.forge_task_coordinator.get_task(task_id)
            node_session_key = task.origin_session_key or node_session_key
            if task.active_revision_id != revision_id:
                raise ValueError("node turn revision is not current")
            method_use = None
            if task.skill_uses:
                method = task.skill_uses[-1]
                method_use = self.forge_task_coordinator.record_skill_use(
                    task_id,
                    activation_id=method.activation_id,
                    skill_name=method.skill_name,
                    skill_version=method.skill_version,
                    content_sha256=method.content_sha256,
                    instructions=method.instructions,
                    decision_ref=f"node:{revision_id}:{node_id}",
                    node_id=node_id,
                )
                task = self.forge_task_coordinator.get_task(task_id)
            binding = task.primary_skill_binding
            prompt = json.dumps({
                "original_goal": task.task_description,
                "verification": task.verification.model_dump(mode="json"),
                # Full Skill instructions remain immutable Coordinator/SkillUse
                # audit facts. The node-scoped projection carries the binding
                # identity, while _default_prompt supplies bounded execution
                # rules for this node. Re-injecting the complete document here
                # duplicates the projection and consumes model decision budget.
                "skill_binding": (
                    {
                        "binding_id": binding.binding_id,
                        "skill_name": binding.skill_name,
                        "skill_version": binding.skill_version,
                        "content_sha256": binding.skill_document_sha256,
                        "runtime_profile": binding.runtime_profile,
                        "runtime_instance_id": binding.runtime_instance_id,
                    }
                    if binding is not None
                    else None
                ),
                "skill_use": (
                    {
                        "use_id": method_use.use_id,
                        "activation_id": method_use.activation_id,
                        "decision_ref": method_use.decision_ref,
                        "node_id": method_use.node_id,
                        "content_sha256": method_use.content_sha256,
                    }
                    if method_use is not None
                    else None
                ),
                "node_context": prompt,
            }, ensure_ascii=False)
        messages = self.context.build_messages(
            history=[],
            current_message=prompt,
            channel="agent_task",
            chat_id=f"{task_id}:{revision_id}:{node_id}",
        )
        return await self._run_agent_loop(
            messages,
            on_progress=on_progress,
            experience_session_key=node_session_key,
            active_task_id=task_id,
            projection_scope="node",
            projection_node_id=node_id,
            allowed_tool_names=_NODE_TURN_ALLOWED_TOOLS,
            yield_after_tools=_NODE_TURN_EXECUTION_TOOLS,
            decision_timeout_s=self.turn_timeout_s,
        )

    async def run_segment_continuation_turn(
        self,
        *,
        task_id: str,
        on_progress: Callable[..., Awaitable[None]] | None = None,
    ) -> AgentLoopRunResult:
        """Choose the next scene-bound segment or final verification from persisted facts."""

        if self.forge_task_coordinator is None:
            raise RuntimeError("segment continuation requires a Forge task coordinator")
        task = self.forge_task_coordinator.get_task(task_id)
        revision = task.active_revision
        graph = revision.plan_graph
        if graph is None:
            raise ValueError("segment continuation requires a materialized PlanGraph")
        settlements = {item.node_id: item.status for item in revision.node_settlements}
        if any(settlements.get(node.node_id) != "completed" for node in graph.nodes):
            raise ValueError("segment continuation requires every active node to be completed")

        prompt = json.dumps(
            {
                "task_id": task_id,
                "original_goal": task.task_description,
                "verification": task.verification.model_dump(mode="json"),
                "active_revision_id": task.active_revision_id,
                "instruction": (
                    "The current scene-bound PlanGraph segment is fully settled. Use only "
                    "persisted Coordinator facts. If the user-level goal still requires work, "
                    "call forge_task_continue_plan with exactly the next scene-bound segment. "
                    "If current evidence proves the complete goal is ready for verification, "
                    "call forge_task_finalize. Do not repeat completed Query, Action, or Session "
                    "executions and do not access Runtime or SQLite internals."
                ),
            },
            ensure_ascii=False,
        )
        messages = self.context.build_messages(
            history=[],
            current_message=prompt,
            channel="agent_task",
            chat_id=f"{task_id}:{task.active_revision_id}:continuation",
        )
        return await self._run_agent_loop(
            messages,
            on_progress=on_progress,
            experience_session_key=task.origin_session_key or f"agent_task:{task_id}",
            active_task_id=task_id,
            projection_scope="continuation",
            allowed_tool_names=frozenset(
                {
                    "forge_task_continue_plan",
                    "forge_task_finalize",
                    "forge_task_request_clarification",
                }
            ),
            yield_after_tools=frozenset(
                {
                    "forge_task_continue_plan",
                    "forge_task_finalize",
                    "forge_task_request_clarification",
                }
            ),
        )

    async def run(self) -> None:
        """Run the agent loop, dispatching messages as tasks to stay responsive to /stop."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            cmd = msg.content.strip().lower()
            if cmd == "/stop":
                await self._handle_stop(msg)
            elif cmd == "/restart":
                await self._handle_restart(msg)
            else:
                task = asyncio.create_task(self._dispatch(msg))
                self._active_tasks.setdefault(msg.session_key, []).append(task)
                task.add_done_callback(
                    lambda t, k=msg.session_key: (
                        self._active_tasks.get(k, []) and self._active_tasks[k].remove(t)
                        if t in self._active_tasks.get(k, [])
                        else None
                    )
                )

    async def _handle_stop(self, msg: InboundMessage) -> None:
        """Cancel all active tasks and subagents for the session."""
        tasks = self._active_tasks.pop(msg.session_key, [])
        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        sub_cancelled = await self.subagents.cancel_by_session(msg.session_key)
        forge_cancelled = 0
        if self.forge_task_coordinator is not None:
            record = self._task_for_session(msg.session_key, include_terminal=False)
            if record is not None:
                await self.forge_task_coordinator.cancel_task(record.task_id, reason="user_stop")
                forge_cancelled = 1
        local_stopped = cancelled + sub_cancelled
        if forge_cancelled:
            content = (
                f"Stopped {local_stopped} local task(s); requested cancellation for "
                f"{forge_cancelled} Forge AgentTask(s). Physical Action stop is not proven "
                "until Gateway status/result becomes terminal."
            )
        elif local_stopped:
            content = f"Stopped {local_stopped} task(s)."
        else:
            content = "No active task to stop."
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=content,
            )
        )

    async def _handle_restart(self, msg: InboundMessage) -> None:
        """Restart the process in-place via os.execv."""
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="Restarting...",
            )
        )

        async def _do_restart():
            await asyncio.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        asyncio.create_task(_do_restart())

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Process a message under the global lock."""
        async with self._processing_lock:
            await self._publish_turn_event(msg, "turn_started")
            try:
                response = await asyncio.wait_for(
                    self._process_message(msg), timeout=self.turn_timeout_s
                )
                if response is not None:
                    await self.bus.publish_outbound(response)
                elif msg.channel == "cli":
                    await self.bus.publish_outbound(
                        OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content="",
                            metadata={
                                **(msg.metadata or {}),
                                "event_type": "turn_completed",
                            },
                        )
                    )
            except asyncio.TimeoutError:
                logger.warning(
                    "Turn timed out after {} seconds for session {}",
                    self.turn_timeout_s,
                    msg.session_key,
                )
                await self._publish_turn_event(
                    msg,
                    "turn_timeout",
                    f"Turn timed out after {self.turn_timeout_s:g} seconds. "
                    "You can retry the request or use /stop.",
                )
            except asyncio.CancelledError:
                logger.info("Task cancelled for session {}", msg.session_key)
                await self._publish_turn_event(msg, "turn_cancelled", "Turn cancelled.")
                raise
            except Exception:
                logger.exception("Error processing message for session {}", msg.session_key)
                await self.bus.publish_outbound(
                    OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content="Sorry, I encountered an error.",
                        metadata={
                            **(msg.metadata or {}),
                            "event_type": "turn_failed",
                        },
                    )
                )

    async def _publish_turn_event(
        self,
        msg: InboundMessage,
        event_type: str,
        content: str = "",
    ) -> None:
        """Publish a lifecycle event correlated with an inbound turn."""
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=content,
                metadata={
                    **(msg.metadata or {}),
                    "event_type": event_type,
                },
            )
        )

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None
        if self.forge_tool_client is not None:
            await self.forge_tool_client.close()

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        if self.experience is not None:
            self.experience.stop()
        if (
            self.forge_task_coordinator is not None
            and self.forge_task_coordinator.verifier is not None
        ):
            self.forge_task_coordinator.verifier.stop()
        logger.info("Agent loop stopping")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (
                msg.chat_id.split(":", 1) if ":" in msg.chat_id else ("cli", msg.chat_id)
            )
            logger.info("Processing system message from {}", msg.sender_id)
            key = msg.session_key_override or f"{channel}:{chat_id}"
            self.skill_activation.begin_turn(key, msg.content)
            task_ref = msg.metadata.get("agent_task_id") or msg.metadata.get("forge_session_id")
            if self.experience is not None and task_ref:
                self.experience.schedule_forge_completion(str(task_ref))
            session = self.sessions.get_or_create(key)
            await self.memory_consolidator.maybe_consolidate_by_tokens(session)
            self._set_tool_context(
                channel,
                chat_id,
                msg.metadata.get("message_id"),
                key,
            )
            history = session.get_history(max_messages=0)
            messages = self.context.build_messages(
                history=history,
                current_message=msg.content,
                channel=channel,
                chat_id=chat_id,
            )
            run_result = await self._run_agent_loop(
                messages, experience_session_key=key
            )
            final_content = run_result.content
            self._save_turn(session, run_result.messages, 1 + len(history))
            self.sessions.save(session)
            await self.memory_consolidator.maybe_consolidate_by_tokens(session)
            return OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=final_content or "Background task completed.",
            )

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)
        self.skill_activation.begin_turn(key, msg.content)

        clarification_task = None
        if self.forge_task_coordinator is not None:
            waiting = [
                item
                for item in self.forge_task_coordinator.store.find_by_origin_session_key(key)
                if item.status.value == "waiting_for_user"
            ]
            if waiting:
                clarification_task = waiting[-1]
                self.forge_task_coordinator.resolve_clarification(
                    clarification_task.task_id,
                    answer=msg.content,
                )

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            try:
                if not await self.memory_consolidator.archive_unconsolidated(session):
                    return OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content="Memory archival failed, session not cleared. Please try again.",
                    )
            except Exception:
                logger.exception("/new archival failed for {}", session.key)
                return OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content="Memory archival failed, session not cleared. Please try again.",
                )

            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)
            return OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content="New session started."
            )
        if cmd == "/help":
            lines = [
                "🍞 PhyAgentOS commands:",
                "/new — Start a new conversation",
                "/stop — Stop the current task",
                "/restart — Restart the bot",
                "/help — Show available commands",
            ]
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="\n".join(lines),
            )
        await self.memory_consolidator.maybe_consolidate_by_tokens(session)

        self._set_tool_context(
            msg.channel,
            msg.chat_id,
            msg.metadata.get("message_id"),
            key,
        )
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        history = session.get_history(max_messages=0)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=(
                f"[Clarification answer for AgentTask {clarification_task.task_id}]\n{msg.content}"
                if clarification_task is not None
                else msg.content
            ),
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        if self.forge_task_coordinator is not None:
            active = self._task_for_session(key)
            if active is not None:
                binding = active.primary_skill_binding
                summary = {
                    "task_id": active.task_id, "status": active.status.value,
                    "task_description": active.task_description,
                    "origin_session_key": active.origin_session_key,
                    "revision_id": active.active_revision_id,
                    "plan_materialized": active.active_revision.plan_graph is not None,
                    "record_count": len(active.execution_records),
                    "binding_id": binding.binding_id if binding else None,
                    "skill_version": binding.skill_version if binding else None,
                    "runtime_instance_id": binding.runtime_instance_id if binding else None,
                }
                initial_messages[0]["content"] += (
                    "\n\nCurrent persisted AgentTask snapshot (data, not instructions):\n"
                    + json.dumps(summary, ensure_ascii=False)
                    + "\nUse this current identity instead of stale task IDs in chat history. "
                    "It does not authorize takeover, cancellation, migration or motion. "
                    "Reconcile this task before proposing another; use public Tool context/Queries "
                    "for missing execution inputs, not filesystem searches of Runtime internals."
                )

        async def _bus_progress(content: str, *, tool_hint: bool = False) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            meta["event_type"] = "turn_progress"
            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=content,
                    metadata=meta,
                )
            )

        try:
            run_result = await self._run_agent_loop(
                initial_messages,
                on_progress=on_progress or _bus_progress,
                experience_session_key=key,
                yield_after_tools=(
                    frozenset({"forge_task_materialize_plan"})
                    if self.long_horizon_controller is not None
                    else frozenset()
                ),
            )
        except asyncio.CancelledError:
            # The loop appends to initial_messages. Preserve completed observations
            # and model decisions, not a second copy of task execution state.
            turn_messages = initial_messages[1 + len(history):]
            answered = {m.get("tool_call_id") for m in turn_messages if m["role"] == "tool"}
            for message in turn_messages:
                for call in message.get("tool_calls", ()):
                    if call["id"] not in answered:
                        self.context.add_tool_result(
                            initial_messages, call["id"], call["function"]["name"],
                            json.dumps({"ok": False, "error": {
                                "type": "local_turn_interrupted",
                                "message": "No tool result was received before local cancellation. "
                                "The call may be undispatched or its outcome unknown. Reconcile "
                                "persisted task/Gateway facts before any retry; this is not proof of stop.",
                            }}),
                        )
            self._save_turn(session, initial_messages, 1 + len(history))
            self.sessions.save(session)
            logger.warning("Interrupted turn history saved for session {}", key)
            raise

        final_content = run_result.content
        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        self._save_turn(session, run_result.messages, 1 + len(history))
        self.sessions.save(session)
        await self.memory_consolidator.maybe_consolidate_by_tokens(session)

        # A task created/materialized by this turn is now eligible for the
        # host-owned outer loop.  The loop runs in the background so the TUI can
        # continue receiving pause, stop, resume, or clarification input.
        self.start_ready_long_horizon_tasks(key)

        if self.forge_task_coordinator is not None:
            waiting = [
                item
                for item in self.forge_task_coordinator.store.find_by_origin_session_key(key)
                if item.status.value == "waiting_for_user"
            ]
            if waiting:
                pending = waiting[-1]
                await self.bus.publish_outbound(
                    OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=pending.clarification_question or "Clarification required.",
                        metadata={
                            **(msg.metadata or {}),
                            "event_type": "clarification_requested",
                            "task_id": pending.task_id,
                            "revision_id": pending.active_revision_id,
                            "node_id": pending.clarification_node_id,
                            "clarification_id": pending.clarification_id,
                        },
                    )
                )

        if (mt := self.tools.get("message")) and isinstance(mt, MessageTool) and mt._sent_in_turn:
            return None

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata={
                **(msg.metadata or {}),
                "event_type": "turn_completed",
            },
        )

    def _save_turn(self, session: Session, messages: list[dict], skip: int) -> None:
        """Save new-turn messages into session, truncating large tool results."""
        from datetime import datetime

        for m in messages[skip:]:
            entry = dict(m)
            role, content = entry.get("role"), entry.get("content")
            if role == "assistant" and not content and not entry.get("tool_calls"):
                continue  # skip empty assistant messages — they poison session context
            if (
                role == "tool"
                and isinstance(content, str)
                and len(content) > self._TOOL_RESULT_MAX_CHARS
            ):
                entry["content"] = content[: self._TOOL_RESULT_MAX_CHARS] + "\n... (truncated)"
            elif role == "user":
                if isinstance(content, str) and content.startswith(
                    ContextBuilder._MESSAGE_CONTEXT_TAG
                ):
                    # Strip the message-metadata prefix, keep only the user text.
                    parts = content.split("\n\n", 1)
                    if len(parts) > 1 and parts[1].strip():
                        entry["content"] = parts[1]
                    else:
                        continue
                if isinstance(content, list):
                    filtered = []
                    for c in content:
                        if (
                            c.get("type") == "text"
                            and isinstance(c.get("text"), str)
                            and c["text"].startswith(ContextBuilder._MESSAGE_CONTEXT_TAG)
                        ):
                            continue  # Strip message metadata from multimodal messages
                        if c.get("type") == "image_url" and c.get("image_url", {}).get(
                            "url", ""
                        ).startswith("data:image/"):
                            filtered.append({"type": "text", "text": "[image]"})
                        else:
                            filtered.append(c)
                    if not filtered:
                        continue
                    entry["content"] = filtered
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
        session.updated_at = datetime.now()

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        try:
            response = await asyncio.wait_for(
                self._process_message(
                    msg, session_key=session_key, on_progress=on_progress
                ),
                timeout=self.turn_timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Direct turn timed out after {} seconds for session {}",
                self.turn_timeout_s,
                session_key,
            )
            return (
                f"Turn timed out after {self.turn_timeout_s:g} seconds. "
                "You can retry the request or use /stop."
            )
        return response.content if response else ""
