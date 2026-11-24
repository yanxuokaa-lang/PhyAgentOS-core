"""Compose fresh lab subtask plans from persisted Query and Action receipts."""

from PhyAgentOS.agent.plan_proposal import compile_task_plan
from PhyAgentOS.agent.planner_plugin import MethodOption, ReplanProposal
from PhyAgentOS.agent.planning_context import current_scene_query_records
from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.agent.recovery_decisions import (
    AgentRecoveryDecisions,
    _fresh_observation_recovery_record,
    _scene_refresh_bootstrap_node_id,
)
from PhyAgentOS.planning import PlanNode, reconcile_replan_delta
from PhyAgentOS.planning.input_schema import materialize_tool_arguments
from pick_place_workflow.agent_planning import compose_subtask_plan
from pick_place_workflow.perception_binding import (
    BindingRequest,
    PerceptionBindingAdapter,
    PerceptionBindingError,
)
from pick_place_workflow.subtask_executor import SubtaskSpec


_SUBTASK = "manipulation.execute_subtask"
_PREPARATION_QUERIES = {
    "manipulation.process_features",
    "manipulation.prepare_process_features",
    "manipulation.grasp_task_affordances",
    "manipulation.prepare_grasp_task_affordance",
}


class LabSubtaskContinuation(AgentRecoveryDecisions):
    """Propose read-only recovery and fresh fragments through the existing AgentLoop."""

    def __init__(self, provider, model, coordinator, *, sensor_ref, **kwargs):
        super().__init__(provider, model, coordinator, **kwargs)
        self.sensor_ref = sensor_ref

    def _refresh_spec(self, task, graph, settlement, context):
        if settlement.status not in {"failed", "stale"}:
            return None
        pending = self._pending_subtask(task)
        if pending is None:
            return None
        _original_graph, spec = pending
        node = next((item for item in graph.nodes if item.node_id == settlement.node_id), None)
        if node is None:
            return None
        if (
            _fresh_observation_recovery_record(task, graph, settlement) is not None
            or (node.capability in _PREPARATION_QUERIES
                and node.input_bindings.get("scene_revision") not in {None, context.scene_revision})
        ):
            return spec
        return None

    async def select_recovery(self, *, graph, settlement, delta, context):
        task = self.coordinator.get_task(graph.task_id)
        if self._refresh_spec(task, graph, settlement, context) is not None:
            self.coordinator.store.update(
                graph.task_id, lambda current: None, event_type="agent_recovery_decided",
                payload={"revision_id": graph.revision_id, "node_id": settlement.node_id,
                         "decision": "replan", "reason": "Refresh the scene for the next unfinished lab subtask."},
            )
            return "replan"
        return await super().select_recovery(graph=graph, settlement=settlement, delta=delta, context=context)

    async def propose_replan(self, *, graph, settlement, delta, context):
        task = self.coordinator.get_task(graph.task_id)
        spec = self._refresh_spec(task, graph, settlement, context)
        if spec is None:
            return await super().propose_replan(graph=graph, settlement=settlement, delta=delta, context=context)
        reason = "Refresh the scene before binding the next unfinished lab subtask."
        node = PlanNode(
            node_id=_scene_refresh_bootstrap_node_id(graph),
            obligation_id="refresh_scene_for_pending_subtask",
            capability="scene.observe",
            input_bindings={"sensor_refs": [self.sensor_ref], "max_age_ms": spec.binding.max_age_ms},
        )
        replacement = compile_task_plan(task, [node.model_dump(mode="json")], reason=reason)
        return ReplanProposal(
            delta=reconcile_replan_delta(graph, delta, replacement),
            plan_graph=replacement,
            plan_graph_ref=f"artifact://plans/{task.task_id}/{replacement.revision_id}",
            reason=reason,
        )

    def _pending_subtask(self, task):
        original_graph = task.revisions[0].plan_graph
        if original_graph is None:
            return None
        original_nodes = {node.node_id: node for node in original_graph.nodes if node.capability == _SUBTASK}
        revisions = {revision.revision_id: revision for revision in task.revisions}
        completed = set()
        for record in task.execution_records:
            if record.semantics not in {"action", "session"}:
                continue
            if record.tool_id != _SUBTASK or not record.terminal or record.node_id not in original_nodes:
                return None
            revision = revisions[record.revision_id]
            original = original_nodes[record.node_id].input_bindings
            supplied = record.arguments
            if any(supplied.get(key) != original.get(key) for key in
                   ("subtask_id", "operation", "parameters", "return_destination_ref", "tool_sequence")):
                return None
            settlement = next((
                item for item in self.coordinator.effective_node_settlements(task.task_id, record.revision_id)
                if item.node_id == record.node_id
            ), None)
            facts = response_facts(record.response)
            if (settlement is not None and settlement.status == "completed"
                    and facts.get("status") == "succeeded" and facts.get("outcome_known") is True
                    and facts.get("possession_state") == "empty"):
                completed.add(record.node_id)
            elif (settlement is None or revision.plan_graph is None
                  or _fresh_observation_recovery_record(task, revision.plan_graph, settlement) != record
                  or facts.get("subtask_result", {}).get("completed_tool_ids") != ["manipulation.prepare"]):
                return None
        for node in original_nodes.values():
            if node.node_id in completed:
                continue
            bindings = dict(node.input_bindings)
            # A graph marks its Action as task-qualified before future Queries supply those references.
            bindings.pop("affordance_selection", None)
            spec = SubtaskSpec.model_validate(bindings)
            if set(spec.depends_on).issubset(completed):
                return original_graph, spec
            return None
        return None

    def propose_method_options(self, *, request):
        task = self.coordinator.get_task(request.task_id)
        if task.active_revision_id != request.revision_id:
            return ()
        pending = self._pending_subtask(task)
        if pending is None:
            return ()
        graph, spec = pending
        previous = spec.binding
        records = current_scene_query_records(task)
        trusted = set(request.evidence_refs)
        used = []
        missing = None

        def from_receipts(tool_id, arguments):
            nonlocal missing
            schema = PerceptionBindingAdapter._QUERY_SPECS[tool_id]["input_schema"]
            expected = materialize_tool_arguments(schema, arguments)
            for record in reversed(records):
                if record.tool_id != tool_id or not trusted.intersection(record.evidence_refs):
                    continue
                actual = materialize_tool_arguments(schema, record.arguments)
                facts = response_facts(record.response)
                if tool_id == "scene.observe":
                    if "sensor_ref" in actual:
                        actual["sensor_refs"] = [actual.pop("sensor_ref")]
                    if actual.get("requested_frame") == facts.get("frame", {}).get("frame_id"):
                        actual.pop("requested_frame", None)
                elif tool_id == "grasp.propose":
                    actual["targets"] = [
                        {"geometry_artifacts": [], **target} for target in actual.get("targets", [])
                    ]
                if actual == expected:
                    used.append(record)
                    return facts
            missing = tool_id, arguments
            raise PerceptionBindingError(f"current task has no {tool_id} receipt for these arguments")

        adapter = PerceptionBindingAdapter(from_receipts, BindingRequest(
            sensor_refs=(self.sensor_ref,),
            source_category=previous.category,
            destination_category=previous.destination_category,
            max_age_ms=previous.max_age_ms,
            process_frame=previous.process_frame if previous.process_frame != previous.frame_id else None,
            source_selector=lambda entity: self._label(entity) == previous.semantic_label,
            destination_selector=lambda entity: self._label(entity) == previous.destination_semantic_label,
        ))
        try:
            binding = adapter.bind()
        except PerceptionBindingError:
            if missing is None:
                return ()
            capability, arguments = missing
            if capability not in request.available_capabilities:
                return ()
            if capability == "grasp.propose":
                # The real ToolSpec projects targets from the current understanding record.
                arguments = dict(arguments)
                target, = arguments.pop("targets")
                arguments["entity_ref"] = target["entity_ref"]
            evidence = self._evidence(used, trusted)
            node = PlanNode(
                node_id=f"{spec.subtask_id}.discover.{capability}",
                obligation_id=f"{spec.subtask_id}-discover-{capability}",
                capability=capability,
                required_evidence=evidence,
                input_bindings=arguments,
            )
            active_graph = task.active_revision.plan_graph
            if active_graph is not None and any(item.node_id == node.node_id for item in active_graph.nodes):
                return ()
            return self._option(spec, (node,), evidence, f"Collect current {capability} evidence.")
        if binding.scene_revision != request.scene_revision:
            return ()
        rebound = spec.model_copy(update={"binding": binding, "depends_on": ()})
        composed = compose_subtask_plan(
            graph.task_id, task.active_revision_id, (rebound,),
            planner_decision_digest=graph.planner_decision_digest,
            policy_snapshot_digest=graph.policy_snapshot_digest,
        )
        evidence = self._evidence(used, trusted)
        nodes = tuple(
            node.model_copy(update={
                "required_evidence": evidence,
                **({"produced_evidence": ()} if not node.dependencies and node.capability != _SUBTASK else {}),
            })
            for node in composed.graph.nodes
            if node.capability != "task.verify"
        )
        return self._option(spec, nodes, evidence, "Prepare the next unfinished lab subtask from current perception.")

    @staticmethod
    def _label(entity):
        return entity.get("semantic_label") or entity.get("label") or entity.get("category")

    @staticmethod
    def _evidence(records, trusted):
        return tuple(dict.fromkeys(ref for rec in records for ref in rec.evidence_refs if ref in trusted))

    @staticmethod
    def _option(spec, nodes, evidence, reason):
        return (MethodOption(
            method_id=f"lab-{spec.subtask_id}",
            description=f"Continue lab subtask {spec.subtask_id}",
            applicable_obligations=tuple(node.obligation_id for node in nodes),
            nodes=nodes,
            evidence_refs=evidence,
            reason=reason,
        ),)
