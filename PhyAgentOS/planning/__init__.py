"""Pure planning contracts and calculations for PAOS.

This package deliberately has no Gateway, SQLite, adapter, or motion imports.
It turns Agent proposals into validated planning decisions; callers own
execution and persistence.
"""

from .admission import AdmissionContext, AdmissionDecision, admit_tool_call
from .contracts import (
    DecisionTrace,
    NodeSettlement,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ReplanDelta,
    ResourceClaim,
    ResumablePlanningSelection,
    ToolCallEnvelope,
    ToolResultEnvelope,
    ToolSpecPolicy,
    WorkflowPolicy,
    WorkflowPolicyCandidate,
    WorkflowPolicyReplayReceipt,
    canonical_sha256,
    plan_graph_digest,
    plan_node_digest,
    tool_input_binding_digest,
    validate_condition_keys,
)
from .dag import (
    derive_ready_nodes,
    evaluate_conditions,
    explain_node_readiness,
    invalidate_stale_nodes,
    validate_graph,
)
from .input_schema import (
    ToolInputSchemaError,
    required_argument_keys,
    validate_input_schema,
    validate_tool_arguments,
)
from .policy import validate_policy_edges, workflow_policy_digest
from .projection import ToolSpecProjectionError, project_tool_spec
from .replan import build_replan_delta
from .settlement import settle_node
from .trace import make_decision_trace

__all__ = [
    "AdmissionContext",
    "AdmissionDecision",
    "DecisionTrace",
    "NodeSettlement",
    "PlanGraph",
    "PlanNode",
    "PlanningExecutionBinding",
    "ResourceClaim",
    "ReplanDelta",
    "ResumablePlanningSelection",
    "ToolCallEnvelope",
    "ToolResultEnvelope",
    "ToolInputSchemaError",
    "ToolSpecPolicy",
    "WorkflowPolicy",
    "WorkflowPolicyCandidate",
    "WorkflowPolicyReplayReceipt",
    "admit_tool_call",
    "required_argument_keys",
    "validate_input_schema",
    "validate_tool_arguments",
    "build_replan_delta",
    "canonical_sha256",
    "plan_graph_digest",
    "plan_node_digest",
    "tool_input_binding_digest",
    "validate_condition_keys",
    "derive_ready_nodes",
    "evaluate_conditions",
    "explain_node_readiness",
    "invalidate_stale_nodes",
    "settle_node",
    "validate_graph",
    "validate_policy_edges",
    "workflow_policy_digest",
    "ToolSpecProjectionError",
    "project_tool_spec",
    "make_decision_trace",
]
