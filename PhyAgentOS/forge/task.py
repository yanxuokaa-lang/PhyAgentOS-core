"""Agent-owned task aggregation over the single Forge Tool API execution plane."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import (
    BoundToolSpec,
    ForgeSkillBinding,
    ForgeSkillBindingError,
    ForgeSkillBindingResolver,
    RuntimeBinding,
    canonical_sha256,
    required_preplan_queries,
)
from PhyAgentOS.forge.evidence import ForgeEvidenceWriter
from PhyAgentOS.forge.observation import ForgeObservationCollector
from PhyAgentOS.forge.tool_client import ForgeToolAPIError, ForgeToolClient
from PhyAgentOS.planning import (
    DecisionTrace,
    NodeSettlement,
    PlanGraph,
    PlanningExecutionBinding,
    ReplanDelta,
    ResumablePlanningSelection,
    ToolResultEnvelope,
    plan_node_digest,
    settle_node,
    tool_input_binding_digest,
    validate_condition_keys,
    validate_graph,
)
from PhyAgentOS.utils.atomic_file import atomic_write_text
from PhyAgentOS.verification.contracts import (
    TaskVerificationContract,
    VerificationAttempt,
    VerificationVerdict,
    utc_now,
)


class AgentTaskError(RuntimeError):
    """Raised when an AgentTask operation violates its lifecycle contract."""


class DiscoveryRequiredError(AgentTaskError):
    """Raised when Skill-declared discovery Queries are incomplete."""

    code = "discovery_required"

    def __init__(self, message: str, *, missing: tuple[str, ...] = ()) -> None:
        self.missing = missing
        super().__init__(message)


class TaskNotReadyForFinalizationError(AgentTaskError):
    """Raised when final verification prerequisites are not yet satisfied."""

    code = "task_not_ready_for_finalization"

    def __init__(self, message: str, *, reason: str) -> None:
        self.reason = reason
        super().__init__(message)


class AgentTaskBusyError(AgentTaskError):
    """Raised when the global non-terminal AgentTask slot is occupied."""

    code = "agent_task_busy"

    def __init__(self, task_id: str, owner_session_key: str | None) -> None:
        self.task_id = task_id
        self.owner_session_key = owner_session_key
        owner = owner_session_key or "unknown"
        super().__init__(
            f"AgentTask {task_id} is still non-terminal and is owned by session {owner}"
        )


class AgentTaskOriginConflictError(AgentTaskError):
    """Raised when an immutable task origin has already been compiled."""

    def __init__(self, origin_dedup_key: str, existing_task_id: str) -> None:
        self.origin_dedup_key = origin_dedup_key
        # Compatibility alias for callers that used the old exception attribute.
        self.origin_session_key = origin_dedup_key
        self.existing_task_id = existing_task_id
        super().__init__(
            f"AgentTask origin {origin_dedup_key!r} already belongs to "
            f"{existing_task_id}"
        )


class AgentTaskStatus(StrEnum):
    EXECUTING = "executing"
    WAITING_FOR_USER = "waiting_for_user"
    CANCELLING = "cancelling"
    AWAITING_REPLAN = "awaiting_replan"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATUSES = {
    AgentTaskStatus.SUCCEEDED,
    AgentTaskStatus.FAILED,
    AgentTaskStatus.CANCELLED,
}

TERMINAL_TOOL_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
    "stopped",
    "unknown",
}

class ToolExecutionRecord(BaseModel):
    """One Query execution or one Gateway-owned Action invocation reference."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["tool_execution_record_v2"] = "tool_execution_record_v2"
    record_id: str
    revision_id: str
    tool_id: str
    semantics: Literal["query", "action", "session"]
    skill_binding_id: str | None = None
    runtime_binding_id: str | None = None
    skill_use_ids: tuple[str, ...] = ()
    tool_spec_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    caller_id: str
    node_id: str | None = None
    node_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    obligation_id: str | None = None
    input_binding_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    decision_trace_ref: str | None = None
    ownership: Literal["task", "runtime", "shared"] = "task"
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal[
        "pending",
        "accepted",
        "running",
        "succeeded",
        "failed",
        "cancelled",
        "stopped",
        "unknown",
    ] = "pending"
    invocation_id: str | None = None
    attempt_id: str | None = None
    response: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_node_binding(self) -> "ToolExecutionRecord":
        planning_fields = (
            self.node_id,
            self.node_digest,
            self.obligation_id,
            self.input_binding_digest,
            self.decision_trace_ref,
        )
        if any(value is not None for value in planning_fields):
            if any(value is None for value in planning_fields):
                raise ValueError(
                    "planning-bound Tool execution records require node_id, node_digest, obligation_id, input_binding_digest, and decision_trace_ref"
                )
        return self

    @field_validator("arguments", "response", "error")
    @classmethod
    def require_finite_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Tool execution payload must contain finite JSON values") from exc
        return value

    @field_validator("record_id", "revision_id", "tool_id")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("Tool execution identifiers must be non-empty and path-safe")
        return normalized

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_TOOL_STATUSES


class SkillUseRecord(BaseModel):
    """Append-only evidence that a concrete Skill method informed a decision."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["skill_use_record_v1"] = "skill_use_record_v1"
    use_id: str
    activation_id: str
    skill_name: str
    skill_version: str | None = None
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    instructions: str = Field(min_length=1)
    decision_ref: str = Field(min_length=1)
    node_id: str | None = None
    attempt_id: str | None = None
    outcome: Literal["selected", "completed", "failed", "cancelled"] = "selected"
    created_at: datetime = Field(default_factory=utc_now)


class PlanRevision(BaseModel):
    """Append-only plan generation within one stable AgentTask identity."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["plan_revision_v2", "plan_revision_v3", "plan_revision_v4"] = "plan_revision_v4"
    revision_id: str
    number: int = Field(ge=1)
    reason: str = Field(min_length=1)
    counts_toward_replan_budget: bool = True
    skill_binding_id: str | None = None
    runtime_binding_id: str | None = None
    skill_use_ids: tuple[str, ...] = ()
    plan_graph: PlanGraph | None = None
    plan_graph_ref: str | None = None
    plan_graph_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    planner_decision_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    policy_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    execution_records: list[ToolExecutionRecord] = Field(default_factory=list)
    planning_selections: list[DecisionTrace] = Field(default_factory=list)
    node_settlements: list[NodeSettlement] = Field(default_factory=list)
    counterevidence: list[NodeSettlement] = Field(default_factory=list)
    preserved_node_ids: tuple[str, ...] = ()
    invalidated_node_ids: tuple[str, ...] = ()
    retry_parent_node_id: str | None = None
    fresh_evidence_requirements: tuple[str, ...] = ()
    discovery_evidence_refs: tuple[str, ...] = ()
    replan_evidence_refs: tuple[str, ...] = ()
    verdict: VerificationVerdict | None = None
    verification_attempts: list[VerificationAttempt] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    closed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_plan_binding(self) -> "PlanRevision":
        planning_fields = (
            self.plan_graph_ref,
            self.plan_graph_digest,
            self.planner_decision_digest,
            self.policy_snapshot_digest,
        )
        if any(value is not None for value in planning_fields) and not all(
            value is not None for value in planning_fields
        ):
            raise ValueError(
                "PlanRevision planning binding requires graph ref, graph, planner, and policy digests"
            )
        if self.plan_graph_ref is not None and not self.plan_graph_ref.startswith("artifact://"):
            raise ValueError("PlanRevision plan_graph_ref must be an artifact:// reference")
        if self.plan_graph is not None:
            if self.plan_graph_ref is None:
                raise ValueError("PlanRevision plan_graph requires plan_graph_ref")
            if self.plan_graph.graph_digest != self.plan_graph_digest:
                raise ValueError("PlanRevision graph digest does not match PlanGraph")
            if self.plan_graph.revision_id != self.revision_id:
                raise ValueError("PlanRevision PlanGraph revision identity does not match")
            if self.plan_graph.planner_decision_digest != self.planner_decision_digest:
                raise ValueError("PlanRevision planner digest does not match PlanGraph")
            if self.plan_graph.policy_snapshot_digest != self.policy_snapshot_digest:
                raise ValueError("PlanRevision policy digest does not match PlanGraph")
            known_nodes = {node.node_id for node in self.plan_graph.nodes}
            if any(item.node_id not in known_nodes for item in self.node_settlements):
                raise ValueError("NodeSettlement references an unknown PlanGraph node")
            if any(item.node_id not in known_nodes for item in self.planning_selections):
                raise ValueError("DecisionTrace references an unknown PlanGraph node")
        if any(item.revision_id != self.revision_id for item in self.node_settlements):
            raise ValueError("NodeSettlement revision_id must match its PlanRevision")
        if any(item.revision_id != self.revision_id for item in self.planning_selections):
            raise ValueError("DecisionTrace revision_id must match its PlanRevision")
        if any(item.revision_id != self.revision_id for item in self.counterevidence):
            raise ValueError("counterevidence revision_id must match its PlanRevision")
        if len({item.node_id for item in self.node_settlements}) != len(self.node_settlements):
            raise ValueError("PlanRevision cannot contain duplicate NodeSettlement node identities")
        trace_refs = [
            item.resumable_selection.planning_binding.decision_trace_ref
            for item in self.planning_selections
            if item.resumable_selection is not None
        ]
        if len(trace_refs) != len(set(trace_refs)):
            raise ValueError("PlanRevision cannot contain duplicate planning selection references")
        used_trace_refs = {
            item.decision_trace_ref
            for item in self.execution_records
            if item.decision_trace_ref is not None
        }
        pending_node_ids = [
            item.node_id
            for item in self.planning_selections
            if item.resumable_selection is not None
            and item.resumable_selection.planning_binding.decision_trace_ref
            not in used_trace_refs
        ]
        if len(pending_node_ids) != len(set(pending_node_ids)):
            raise ValueError(
                "PlanRevision cannot contain multiple unconsumed selections for one node"
            )
        return self


class AgentTaskOriginApproval(BaseModel):
    """Immutable audit receipt for a human-approved declarative task origin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["agent_task_origin_approval_v1"] = "agent_task_origin_approval_v1"
    source_kind: Literal["paos.state-file.v1/sessions"] = (
        "paos.state-file.v1/sessions"
    )
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    declaration_id: str = Field(min_length=1)
    approval_id: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    confirmed_at: datetime

    @field_validator("declaration_id", "approval_id", "approved_by")
    @classmethod
    def validate_audit_identity(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
        ):
            raise ValueError("origin approval identities must be non-empty and path-safe")
        return normalized

    @field_validator("confirmed_at")
    @classmethod
    def require_approval_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("origin approval timestamp must include a timezone")
        return value


class AgentTaskRecord(BaseModel):
    """PAOS task aggregate; never a second robot execution protocol."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["agent_task_record_v2"] = "agent_task_record_v2"
    task_id: str
    task_description: str = Field(min_length=1)
    verification: TaskVerificationContract = Field(default_factory=TaskVerificationContract)
    status: AgentTaskStatus = AgentTaskStatus.EXECUTING
    revisions: list[PlanRevision] = Field(min_length=1)
    active_revision_id: str
    primary_skill_binding: ForgeSkillBinding | None = None
    primary_skill_instructions: str | None = None
    runtime_binding: RuntimeBinding | None = None
    tool_bindings: list[BoundToolSpec] = Field(default_factory=list)
    skill_uses: list[SkillUseRecord] = Field(default_factory=list)
    supporting_skill_bindings: list[ForgeSkillBinding] = Field(default_factory=list)
    runtime_snapshot_ref: str | None = None
    verdict: VerificationVerdict | None = None
    verification_attempts: list[VerificationAttempt] = Field(default_factory=list)
    before_snapshot_ref: str | None = None
    after_snapshot_ref: str | None = None
    evidence_bundle_ref: str | None = None
    evidence_bundle_id: str | None = None
    evidence_errors: list[str] = Field(default_factory=list)
    cancellation_requested: bool = False
    pause_requested: bool = False
    clarification_id: str | None = None
    clarification_question: str | None = None
    clarification_node_id: str | None = None
    clarification_answer: str | None = None
    replan_deadline: datetime | None = None
    replan_extension_used: bool = False
    origin_session_key: str | None = None
    origin_dedup_key: str | None = None
    origin_approval: AgentTaskOriginApproval | None = None
    parent_task_id: str | None = None
    retry_limit: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    terminal_at: datetime | None = None

    @field_validator("task_id", "active_revision_id")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("AgentTask identifiers must be non-empty and path-safe")
        return normalized

    @field_validator("parent_task_id")
    @classmethod
    def validate_parent_identity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("parent_task_id must be non-empty and path-safe")
        return normalized

    @model_validator(mode="after")
    def validate_aggregate(self) -> "AgentTaskRecord":
        if self.origin_approval is not None:
            expected = (
                f"statefile+sessions://{self.origin_approval.source_sha256}/"
                f"{self.origin_approval.declaration_id}"
            )
            if self.origin_session_key != expected or self.origin_dedup_key != expected:
                raise ValueError(
                    "origin approval must match the state-file session identities"
                )
        revision_ids = [revision.revision_id for revision in self.revisions]
        if len(revision_ids) != len(set(revision_ids)):
            raise ValueError("AgentTask revision identities must be unique")
        revision_numbers = [revision.number for revision in self.revisions]
        if len(revision_numbers) != len(set(revision_numbers)):
            raise ValueError("AgentTask revision numbers must be unique")
        if self.active_revision_id not in set(revision_ids):
            raise ValueError("active_revision_id must identify an AgentTask revision")
        execution_ids: set[str] = set()
        skill_use_ids = {item.use_id for item in self.skill_uses}
        if len(skill_use_ids) != len(self.skill_uses):
            raise ValueError("Skill-use identities must be unique")
        for revision in self.revisions:
            expected_runtime = (
                self.runtime_binding.binding_id if self.runtime_binding is not None else None
            )
            if revision.runtime_binding_id != expected_runtime:
                raise ValueError("PlanRevision Runtime binding must match AgentTask binding")
            for execution in revision.execution_records:
                if execution.revision_id != revision.revision_id:
                    raise ValueError(
                        "ToolExecutionRecord revision_id must match its PlanRevision"
                    )
                if execution.record_id in execution_ids:
                    raise ValueError("Tool execution record identities must be unique")
                if execution.runtime_binding_id != expected_runtime:
                    raise ValueError("Tool execution Runtime binding must match AgentTask binding")
                if not set(execution.skill_use_ids).issubset(skill_use_ids):
                    raise ValueError("Tool execution references an unknown Skill-use")
                execution_ids.add(execution.record_id)
        return self

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_TASK_STATUSES

    @property
    def active_revision(self) -> PlanRevision:
        for revision in self.revisions:
            if revision.revision_id == self.active_revision_id:
                return revision
        raise AgentTaskError("active PlanRevision is missing")

    @property
    def execution_records(self) -> list[ToolExecutionRecord]:
        return [item for revision in self.revisions for item in revision.execution_records]


class AgentTaskStore:
    """Transactional SQLite store enforcing one global non-terminal AgentTask."""

    def __init__(self, workspace: str | Path) -> None:
        root = Path(workspace).expanduser().resolve() / ".paos" / "agent_tasks"
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "tasks.sqlite3"
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    origin_session_key TEXT,
                    origin_dedup_key TEXT
                );
                CREATE INDEX IF NOT EXISTS agent_tasks_status_idx
                    ON agent_tasks(status);
                CREATE TABLE IF NOT EXISTS agent_task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES agent_tasks(task_id)
                );
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(agent_tasks)").fetchall()
            }
            if "origin_session_key" not in columns:
                connection.execute(
                    "ALTER TABLE agent_tasks ADD COLUMN origin_session_key TEXT"
                )
            if "origin_dedup_key" not in columns:
                connection.execute(
                    "ALTER TABLE agent_tasks ADD COLUMN origin_dedup_key TEXT"
                )
            legacy_rows = connection.execute(
                "SELECT task_id, record_json FROM agent_tasks "
                "WHERE origin_session_key IS NULL"
            ).fetchall()
            for row in legacy_rows:
                try:
                    payload = json.loads(row["record_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                origin_session_key = (
                    payload.get("origin_session_key")
                    if isinstance(payload, dict)
                    else None
                )
                if isinstance(origin_session_key, str) and origin_session_key:
                    connection.execute(
                        "UPDATE agent_tasks SET origin_session_key = ? WHERE task_id = ?",
                        (origin_session_key, row["task_id"]),
                    )
            duplicate = connection.execute(
                "SELECT origin_dedup_key FROM agent_tasks "
                "WHERE origin_dedup_key IS NOT NULL "
                "GROUP BY origin_dedup_key HAVING COUNT(*) > 1 LIMIT 1"
            ).fetchone()
            if duplicate is not None:
                raise AgentTaskError(
                    "cannot enforce AgentTask origin uniqueness; duplicate origin exists: "
                    f"{duplicate['origin_dedup_key']}"
                )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS agent_tasks_origin_dedup_key_uq "
                "ON agent_tasks(origin_dedup_key) WHERE origin_dedup_key IS NOT NULL"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS agent_tasks_origin_session_key_idx "
                "ON agent_tasks(origin_session_key)"
            )
            connection.commit()

    def create(self, record: AgentTaskRecord) -> AgentTaskRecord:
        try:
            record = AgentTaskRecord.model_validate(record.model_dump(mode="python"))
        except Exception as exc:
            raise AgentTaskError(
                "AgentTask creation violates the authoritative record schema"
            ) from exc
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if record.origin_dedup_key is not None:
                existing = connection.execute(
                    "SELECT task_id FROM agent_tasks WHERE origin_dedup_key = ?",
                    (record.origin_dedup_key,),
                ).fetchone()
                if existing is not None:
                    raise AgentTaskOriginConflictError(
                        record.origin_dedup_key,
                        str(existing["task_id"]),
                    )
            active = connection.execute(
                "SELECT task_id, origin_session_key FROM agent_tasks "
                "WHERE status NOT IN (?, ?, ?) LIMIT 1",
                tuple(item.value for item in TERMINAL_TASK_STATUSES),
            ).fetchone()
            if active is not None:
                raise AgentTaskBusyError(
                    str(active["task_id"]),
                    active["origin_session_key"],
                )
            self._insert(connection, record)
            self._event(connection, record.task_id, "task_created", {})
            connection.commit()
        return record

    def get(self, task_id: str) -> AgentTaskRecord:
        with self._lock, self._connection() as connection:
            return self._get(connection, task_id)

    def record_skill_use_once(
        self,
        task_id: str,
        use: SkillUseRecord,
    ) -> SkillUseRecord:
        """Insert one semantic SkillUse and its event in the same transaction."""

        def same_decision(item: SkillUseRecord) -> bool:
            return (
                item.activation_id == use.activation_id
                and item.content_sha256 == use.content_sha256
                and item.decision_ref == use.decision_ref
                and item.node_id == use.node_id
                and item.attempt_id == use.attempt_id
            )

        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._get(connection, task_id)
            existing = next(
                (item for item in record.skill_uses if same_decision(item)),
                None,
            )
            if existing is not None:
                connection.commit()
                return existing

            record.skill_uses.append(use)
            record.active_revision.skill_use_ids = tuple(
                (*record.active_revision.skill_use_ids, use.use_id)
            )
            try:
                record = AgentTaskRecord.model_validate(
                    record.model_dump(mode="python")
                )
            except Exception as exc:
                raise AgentTaskError(
                    "SkillUse mutation violates the authoritative record schema"
                ) from exc
            record.updated_at = utc_now()
            connection.execute(
                "UPDATE agent_tasks SET status = ?, record_json = ?, updated_at = ?, "
                "origin_session_key = ?, origin_dedup_key = ? WHERE task_id = ?",
                (
                    record.status.value,
                    record.model_dump_json(),
                    record.updated_at.isoformat(),
                    record.origin_session_key,
                    record.origin_dedup_key,
                    task_id,
                ),
            )
            self._event(
                connection,
                task_id,
                "skill_use_recorded",
                {
                    "use_id": use.use_id,
                    "skill_name": use.skill_name,
                    "skill_version": use.skill_version,
                    "decision_ref": use.decision_ref,
                    "node_id": use.node_id,
                    "attempt_id": use.attempt_id,
                },
            )
            connection.commit()
            return use

    def update(
        self,
        task_id: str,
        mutate: Callable[[AgentTaskRecord], None],
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentTaskRecord:
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._get(connection, task_id)
            task_identity = (record.task_id, record.created_at, record.primary_skill_instructions)
            origin_snapshot = (
                record.origin_session_key,
                record.origin_dedup_key,
                record.origin_approval.model_dump_json()
                if record.origin_approval is not None
                else None,
            )
            mutate(record)
            try:
                record = AgentTaskRecord.model_validate(
                    record.model_dump(mode="python")
                )
            except Exception as exc:
                raise AgentTaskError(
                    "AgentTask mutation violates the authoritative record schema"
                ) from exc
            if (record.task_id, record.created_at, record.primary_skill_instructions) != task_identity:
                raise AgentTaskError("AgentTask identity is immutable")
            mutated_origin = (
                record.origin_session_key,
                record.origin_dedup_key,
                record.origin_approval.model_dump_json()
                if record.origin_approval is not None
                else None,
            )
            if mutated_origin != origin_snapshot:
                raise AgentTaskError("AgentTask origin is immutable")
            record.updated_at = utc_now()
            if record.terminal and record.terminal_at is None:
                record.terminal_at = record.updated_at
            connection.execute(
                "UPDATE agent_tasks SET status = ?, record_json = ?, updated_at = ?, "
                "origin_session_key = ?, origin_dedup_key = ? "
                "WHERE task_id = ?",
                (
                    record.status.value,
                    record.model_dump_json(),
                    record.updated_at.isoformat(),
                    record.origin_session_key,
                    record.origin_dedup_key,
                    task_id,
                ),
            )
            self._event(connection, task_id, event_type, payload or {})
            connection.commit()
            return record

    def active(self) -> AgentTaskRecord | None:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT record_json FROM agent_tasks WHERE status NOT IN (?, ?, ?) "
                "ORDER BY created_at LIMIT 1",
                tuple(item.value for item in TERMINAL_TASK_STATUSES),
            ).fetchone()
        return None if row is None else AgentTaskRecord.model_validate_json(row["record_json"])

    def find_by_origin_dedup_key(self, origin_dedup_key: str) -> list[AgentTaskRecord]:
        """Return tasks compiled from one immutable source/declaration identity."""

        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT record_json FROM agent_tasks WHERE origin_dedup_key = ? "
                "ORDER BY created_at",
                (origin_dedup_key,),
            ).fetchall()
        return [AgentTaskRecord.model_validate_json(row["record_json"]) for row in rows]

    def find_by_origin_session_key(self, origin_session_key: str) -> list[AgentTaskRecord]:
        """Return tasks associated with a conversation/session key."""

        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT record_json FROM agent_tasks WHERE origin_session_key = ? "
                "ORDER BY created_at",
                (origin_session_key,),
            ).fetchall()
        return [AgentTaskRecord.model_validate_json(row["record_json"]) for row in rows]

    def find_invocation(self, invocation_id: str) -> tuple[AgentTaskRecord, ToolExecutionRecord] | None:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT record_json FROM agent_tasks").fetchall()
        for row in rows:
            task = AgentTaskRecord.model_validate_json(row["record_json"])
            for record in task.execution_records:
                if record.invocation_id == invocation_id:
                    return task, record
        return None

    def events(self, task_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT event_type, created_at, payload_json FROM agent_task_events "
                "WHERE task_id = ? ORDER BY event_id DESC LIMIT ?",
                (task_id, max(1, int(limit))),
            ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in reversed(rows)
        ]

    @staticmethod
    def _insert(connection: sqlite3.Connection, record: AgentTaskRecord) -> None:
        connection.execute(
            "INSERT INTO agent_tasks("
            "task_id, status, record_json, created_at, updated_at, "
            "origin_session_key, origin_dedup_key"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record.task_id,
                record.status.value,
                record.model_dump_json(),
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.origin_session_key,
                record.origin_dedup_key,
            ),
        )

    @staticmethod
    def _get(connection: sqlite3.Connection, task_id: str) -> AgentTaskRecord:
        row = connection.execute(
            "SELECT record_json FROM agent_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise AgentTaskError(f"AgentTask not found: {task_id}")
        return AgentTaskRecord.model_validate_json(row["record_json"])

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        task_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            payload_json = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise AgentTaskError("AgentTask event payload must contain finite JSON values") from exc
        connection.execute(
            "INSERT INTO agent_task_events(task_id, event_type, created_at, payload_json) "
            "VALUES (?, ?, ?, ?)",
            (task_id, event_type, utc_now().isoformat(), payload_json),
        )


class AgentTaskCoordinator:
    """Aggregate Tool API facts, evidence and semantic verification by user task."""

    def __init__(
        self,
        *,
        workspace: str | Path,
        config: ForgeConfig,
        client: ForgeToolClient,
        verifier: Any | None = None,
        experience: Any | None = None,
        binding_resolver: ForgeSkillBindingResolver | None = None,
        activation_manager: Any | None = None,
        runtime_invocation_ids: Any | None = None,
        runtime_session_ids: Any | None = None,
        runtime_task_binding_ids: Any | None = None,
        store: AgentTaskStore | None = None,
        max_replans: int = 2,
        replan_timeout_s: float = 120.0,
    ) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.config = config
        self.client = client
        self.verifier = verifier
        self.experience = experience
        self.binding_resolver = binding_resolver
        self.activation_manager = activation_manager
        self.runtime_invocation_ids = runtime_invocation_ids
        self.runtime_session_ids = runtime_session_ids
        self.runtime_task_binding_ids = runtime_task_binding_ids
        self.store = store or AgentTaskStore(self.workspace)
        self.max_replans = max(0, int(max_replans))
        self.replan_timeout_s = max(0.1, float(replan_timeout_s))

    def set_experience(self, experience: Any | None) -> None:
        self.experience = experience

    def set_activation_manager(self, activation_manager: Any) -> None:
        self.activation_manager = activation_manager

    def selected_execution_arguments(
        self, task_id: str, tool_id: str, semantics: str,
        arguments: dict[str, Any], planning_binding: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Read exact durable arguments for an explicit receipt-based execution."""
        if arguments:
            raise AgentTaskError("selected execution requires empty literal arguments")
        binding = self.selected_execution_binding(
            task_id, tool_id, semantics, planning_binding
        )
        task = self.get_task(task_id)
        pending = self.pending_planning_selection(task_id, binding.node_id)
        assert pending is not None
        resolved = deepcopy(pending["arguments"])
        _validate_planning_execution_selection(
            task.active_revision, binding, tool_id=tool_id,
            semantics=semantics, arguments=resolved,
        )
        return resolved

    def selected_execution_binding(
        self,
        task_id: str,
        tool_id: str,
        semantics: str,
        planning_binding: dict[str, Any] | None,
    ) -> PlanningExecutionBinding:
        """Resolve the Coordinator-owned binding for a pending selection.

        The Agent may identify a pending selection by node, but it must not
        retype Coordinator-owned digests or trace references.  When the node
        is omitted, this method accepts a unique current selection for the
        requested tool; ambiguity remains an explicit planning error.
        """
        task = self.get_task(task_id)
        wrapper = {
            "query": "forge_tool_query",
            "action": "forge_tool_start_action",
            "session": "forge_tool_start_session",
        }.get(semantics)
        if wrapper is None:
            raise AgentTaskError("selected execution has unsupported semantics")
        supplied = _normalize_planning_binding(planning_binding)
        candidates: list[dict[str, Any]] = []
        if supplied is not None:
            if supplied.revision_id != task.active_revision_id:
                raise AgentTaskError("selected execution has a stale revision")
            pending = self.pending_planning_selection(task_id, supplied.node_id)
            if pending is not None:
                candidates.append(pending)
        else:
            graph = task.active_revision.plan_graph
            if graph is not None:
                for node in graph.nodes:
                    pending = self.pending_planning_selection(task_id, node.node_id)
                    if pending is not None:
                        candidates.append(pending)
        candidates = [
            pending for pending in candidates
            if pending["tool_id"] == tool_id
            and pending["execution_tool"] == wrapper
        ]
        if not candidates:
            raise AgentTaskError("selected execution has no matching unconsumed selection")
        if len(candidates) != 1:
            raise AgentTaskError(
                "selected execution requires a unique node selection for the requested tool"
            )
        return PlanningExecutionBinding.model_validate(candidates[0]["planning_binding"])

    def persist_planning_selection(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Persist a dispatch-approved selection and return its execution binding."""
        task = self.store.get(str(proposal.get("task_id")))
        if task.active_revision_id != proposal.get("revision_id"):
            raise AgentTaskError("planning selection is not bound to the active revision")
        if task.active_revision.plan_graph is None:
            raise AgentTaskError("planning selection requires a materialized PlanGraph")
        node = next((item for item in task.active_revision.plan_graph.nodes if item.node_id == proposal.get("node_id")), None)
        if node is None or plan_node_digest(node) != proposal.get("node_digest"):
            raise AgentTaskError("planning selection node digest does not match the active graph")
        tool_arguments = proposal.get("tool_arguments")
        if not isinstance(tool_arguments, dict):
            raise AgentTaskError("planning selection omitted final Tool arguments")
        if tool_input_binding_digest(tool_arguments) != proposal.get("input_binding_digest"):
            raise AgentTaskError("planning selection arguments do not match their digest")
        pending = self.pending_planning_selection(
            task.task_id,
            node.node_id,
            scene_revision=proposal.get("scene_revision"),
        )
        durable_trace_refs = {
            item.resumable_selection.planning_binding.decision_trace_ref
            for item in task.active_revision.planning_selections
            if item.resumable_selection is not None
        }
        pending_trace_ref = (
            pending["planning_binding"]["decision_trace_ref"]
            if pending is not None
            else None
        )
        if pending is not None and pending_trace_ref not in durable_trace_refs:
            expected_execution_tool = {
                "query": "forge_tool_query",
                "action": "forge_tool_start_action",
                "session": "forge_tool_start_session",
            }.get(proposal.get("semantics"))
            if (
                pending["tool_id"] == proposal.get("tool_id")
                and pending["arguments"] == tool_arguments
                and pending["execution_tool"] == expected_execution_tool
                and pending["scene_revision"] == proposal.get("scene_revision")
            ):
                return {
                    **pending["planning_binding"],
                    "task_id": pending["task_id"],
                    "revision_id": pending["revision_id"],
                    "scene_revision": pending["scene_revision"],
                    "tool_arguments": pending["arguments"],
                }
            raise AgentTaskError(
                "planning node already has an unconsumed selection; execute or replace its revision"
            )
        trace_id = uuid4().hex[:16]
        trace_ref = (
            f"artifact://planning-traces/{task.task_id}/"
            f"{task.active_revision_id}/{node.node_id}/{trace_id}"
        )
        binding = PlanningExecutionBinding(
            revision_id=task.active_revision_id,
            node_id=node.node_id,
            node_digest=proposal["node_digest"],
            obligation_id=node.obligation_id,
            input_binding_digest=proposal["input_binding_digest"],
            decision_trace_ref=trace_ref,
        )
        resumable = ResumablePlanningSelection(
            tool_id=proposal["tool_id"],
            semantics=proposal["semantics"],
            planning_binding=binding,
            tool_arguments=tool_arguments,
        )
        try:
            trace = DecisionTrace.model_validate({
                "schema_version": "paos-decision-trace/v1",
                "task_id": task.task_id,
                "revision_id": task.active_revision_id,
                "node_id": node.node_id,
                "candidate_tool_ids": list(proposal.get("candidate_tool_ids", ())),
                "selected_tool_id": proposal.get("tool_id"),
                "input_binding_digest": proposal.get("input_binding_digest"),
                "scene_revision": proposal.get("scene_revision"),
                "context_digest": proposal.get("context_digest"),
                "decision_reason": proposal.get("decision_reason"),
                "evidence_refs": list(proposal.get("evidence_refs", ())),
                "created_at": utc_now().isoformat(),
                "resumable_selection": resumable.model_dump(mode="json"),
            })
        except Exception as exc:
            raise AgentTaskError(f"planning DecisionTrace is invalid: {exc}") from exc

        persisted_trace: DecisionTrace | None = None
        event_payload: dict[str, Any] = {
            "revision_id": task.active_revision_id,
            "node_id": node.node_id,
            "tool_id": proposal["tool_id"],
            "decision_trace_ref": trace_ref,
        }

        def persist(current: AgentTaskRecord) -> None:
            nonlocal persisted_trace
            if current.active_revision_id != proposal.get("revision_id"):
                raise AgentTaskError("planning selection is not bound to the active revision")
            if any(
                item.node_id == node.node_id
                for item in (
                    *current.active_revision.execution_records,
                    *current.active_revision.node_settlements,
                )
            ):
                raise AgentTaskError(
                    "planning node already has an execution record or settlement"
                )
            used_trace_refs = {
                item.decision_trace_ref
                for item in current.active_revision.execution_records
                if item.decision_trace_ref is not None
            }
            for existing in current.active_revision.planning_selections:
                selection = existing.resumable_selection
                if (
                    existing.node_id == node.node_id
                    and selection is not None
                    and selection.planning_binding.decision_trace_ref not in used_trace_refs
                ):
                    if (
                        existing.scene_revision == proposal.get("scene_revision")
                        and selection.tool_id == proposal.get("tool_id")
                        and selection.semantics == proposal.get("semantics")
                        and selection.tool_arguments == tool_arguments
                    ):
                        persisted_trace = existing
                        event_payload["decision_trace_ref"] = (
                            selection.planning_binding.decision_trace_ref
                        )
                        event_payload["idempotent"] = True
                        return
                    raise AgentTaskError(
                        "planning node already has an unconsumed selection; execute or replace its revision"
                    )
            current.active_revision.planning_selections.append(trace)
            persisted_trace = trace

        self.store.update(
            task.task_id,
            persist,
            event_type="planning_selection_persisted",
            payload=event_payload,
        )
        assert persisted_trace is not None
        persisted_selection = persisted_trace.resumable_selection
        assert persisted_selection is not None
        persisted_binding = persisted_selection.planning_binding
        persisted_trace_id = persisted_binding.decision_trace_ref.rsplit("/", 1)[-1]
        relative = Path("artifacts") / "planning-traces" / task.task_id / task.active_revision_id / node.node_id
        path = (self.workspace / relative).resolve()
        if not path.is_relative_to(self.workspace):
            raise AgentTaskError("planning trace path escapes workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            path / f"{persisted_trace_id}.json",
            json.dumps(
                persisted_trace.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
        )
        return {
            **persisted_binding.model_dump(mode="json"),
            "task_id": task.task_id,
            "revision_id": task.active_revision_id,
            "scene_revision": persisted_trace.scene_revision,
            "tool_arguments": persisted_selection.tool_arguments,
        }

    def pending_planning_selection(
        self,
        task_id: str,
        node_id: str,
        *,
        scene_revision: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the latest unconsumed selection for the current node.

        A selection is consumed only when a planning-bound execution record
        references its decision trace. Reading this checkpoint never invokes a
        Tool and never changes task state.
        """
        task = self.store.get(task_id)
        revision = task.active_revision
        graph = revision.plan_graph
        if graph is None or not any(item.node_id == node_id for item in graph.nodes):
            return None
        if any(item.node_id == node_id for item in revision.node_settlements):
            return None
        used_trace_refs = {
            item.decision_trace_ref
            for item in revision.execution_records
            if item.decision_trace_ref is not None
        }
        directory = (
            self.workspace
            / "artifacts"
            / "planning-traces"
            / task_id
            / revision.revision_id
            / node_id
        )
        candidates: list[DecisionTrace] = [
            trace
            for trace in revision.planning_selections
            if trace.node_id == node_id
            and trace.resumable_selection is not None
            and trace.resumable_selection.planning_binding.decision_trace_ref
            not in used_trace_refs
            and (scene_revision is None or trace.scene_revision == scene_revision)
        ]
        known_trace_refs = {
            item.resumable_selection.planning_binding.decision_trace_ref
            for item in candidates
            if item.resumable_selection is not None
        }
        for path in directory.glob("*.json") if directory.is_dir() else ():
            try:
                trace = DecisionTrace.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            selection = trace.resumable_selection
            if selection is None:
                continue
            if selection.planning_binding.decision_trace_ref in known_trace_refs:
                continue
            if selection.planning_binding.decision_trace_ref in used_trace_refs:
                continue
            if scene_revision is not None and trace.scene_revision != scene_revision:
                continue
            candidates.append(trace)
        if not candidates:
            return None
        trace = max(candidates, key=lambda item: item.created_at)
        selection = trace.resumable_selection
        assert selection is not None
        wrapper = {
            "query": "forge_tool_query",
            "action": "forge_tool_start_action",
            "session": "forge_tool_start_session",
        }[selection.semantics]
        return {
            "task_id": task_id,
            "revision_id": revision.revision_id,
            "node_id": node_id,
            "scene_revision": trace.scene_revision,
            "execution_tool": wrapper,
            "tool_id": selection.tool_id,
            "arguments": selection.tool_arguments,
            "planning_binding": selection.planning_binding.model_dump(mode="json"),
        }

    def planning_selection_rejections(
        self, task_id: str, revision_id: str, node_id: str,
    ) -> list[dict[str, Any]]:
        """Return recent durable diagnostics for this exact node/revision."""
        return [
            event["payload"]["error"] for event in self.store.events(task_id)
            if event["event_type"] == "planning_selection_rejected"
            and event["payload"].get("revision_id") == revision_id
            and event["payload"].get("node_id") == node_id
        ][-4:]

    def record_planning_node_blocked(
        self, task_id: str, revision_id: str, node_id: str, reason: str,
    ) -> None:
        """Persist a blocked node and enter the existing bounded recovery state.

        A runner can stop before a Tool execution record exists (for example a
        deterministic planning-contract rejection or a provider timeout).  The
        task must not remain visibly ``executing`` after that runner has stopped;
        ``awaiting_replan`` is the existing recovery owner for this boundary.
        """
        def check(current: AgentTaskRecord) -> None:
            if current.active_revision_id != revision_id:
                raise AgentTaskError("blocked node is not bound to the active revision")
            if current.terminal:
                return
            current.status = AgentTaskStatus.AWAITING_REPLAN
            current.replan_deadline = utc_now() + timedelta(seconds=self.replan_timeout_s)
            current.replan_extension_used = False
            current.evidence_errors.append(
                f"planning node blocked: {node_id}: {reason.strip()}"
            )

        self.store.update(
            task_id, check, event_type="planning_node_blocked",
            payload={"revision_id": revision_id, "node_id": node_id, "reason": reason},
        )

    def record_planning_selection_rejection(
        self,
        task_id: str,
        *,
        revision_id: str | None,
        node_id: str,
        tool_id: str,
        error: Mapping[str, Any],
    ) -> AgentTaskRecord:
        """Persist a redacted control-plane rejection without creating a Tool record."""
        allowed = {
            "type",
            "code",
            "failure_owner",
            "message",
            "missing_fields",
            "retryable_in_revision",
            "requires_replan",
            "recommended_action",
        }
        redacted = {key: error[key] for key in allowed if key in error}
        requires_replan = error.get("requires_replan") is True
        payload = {
            "revision_id": revision_id,
            "node_id": node_id,
            "tool_id": tool_id,
            "error": redacted,
            "motion_authorized": False,
        }

        def mutate(current: AgentTaskRecord) -> None:
            if revision_id is not None and current.active_revision_id != revision_id:
                raise AgentTaskError(
                    "planning selection rejection is not bound to the active revision"
                )
            if not requires_replan or current.status != AgentTaskStatus.EXECUTING:
                return
            if _replan_count(current) >= self.max_replans:
                current.status = AgentTaskStatus.FAILED
                current.evidence_errors.append(
                    "planning selection requires a replacement graph but replan budget is exhausted"
                )
                return
            current.status = AgentTaskStatus.AWAITING_REPLAN
            current.replan_deadline = utc_now() + timedelta(seconds=self.replan_timeout_s)
            current.replan_extension_used = False
            current.evidence_errors.append(
                "planning selection requires replacement graph: "
                + str(error.get("code", "planning_selection_rejected"))
            )

        result = self.store.update(
            task_id,
            mutate,
            event_type="planning_selection_rejected",
            payload=payload,
        )
        if result.terminal:
            self._schedule_experience(result)
        return result

    def create_task(
        self,
        *,
        task_description: str,
        verification: TaskVerificationContract,
        activation_id: str | None = None,
        origin_session_key: str | None = None,
        origin_dedup_key: str | None = None,
        origin_approval: AgentTaskOriginApproval | None = None,
        parent_task_id: str | None = None,
        retry_limit: int = 0,
        plan_graph: PlanGraph | None = None,
        plan_graph_ref: str | None = None,
    ) -> AgentTaskRecord | Any:
        """Create synchronously only for an explicitly unbound coordinator.

        Managed Forge runtimes return an awaitable because binding freeze revalidates live
        Gateway ToolSpecs. Agent tools handle both forms; physical execution always uses the
        bound form.
        """
        if self.binding_resolver is not None:
            return self._create_task_bound(
                task_description=task_description,
                verification=verification,
                activation_id=activation_id,
                origin_session_key=origin_session_key,
                origin_dedup_key=origin_dedup_key,
                origin_approval=origin_approval,
                parent_task_id=parent_task_id,
                retry_limit=retry_limit,
                plan_graph=plan_graph,
                plan_graph_ref=plan_graph_ref,
            )
        if verification.mode != "off" and self.verifier is None:
            raise AgentTaskError(
                "non-off AgentTask verification requires the verification service"
            )
        task_id = plan_graph.task_id if plan_graph is not None else f"task_{uuid4().hex[:16]}"
        revision_id = plan_graph.revision_id if plan_graph is not None else f"revision_{uuid4().hex[:16]}"
        _validate_plan_graph_input(plan_graph, plan_graph_ref, task_id, revision_id)
        task = AgentTaskRecord(
            task_id=task_id,
            task_description=task_description.strip(),
            verification=verification,
            parent_task_id=parent_task_id,
            retry_limit=retry_limit,
            revisions=[PlanRevision(
                revision_id=revision_id,
                number=1,
                reason="initial plan",
                plan_graph=plan_graph,
                plan_graph_ref=plan_graph_ref,
                plan_graph_digest=plan_graph.graph_digest if plan_graph is not None else None,
                planner_decision_digest=plan_graph.planner_decision_digest if plan_graph is not None else None,
                policy_snapshot_digest=plan_graph.policy_snapshot_digest if plan_graph is not None else None,
            )],
            active_revision_id=revision_id,
            origin_session_key=origin_session_key,
            origin_dedup_key=origin_dedup_key,
            origin_approval=origin_approval,
        )
        self.store.create(task)
        if self.experience is not None and origin_session_key:
            self.experience.bind_forge_task(
                task_id,
                session_key=origin_session_key,
            )
        return task

    async def _create_task_bound(
        self,
        *,
        task_description: str,
        verification: TaskVerificationContract,
        activation_id: str | None = None,
        origin_session_key: str | None = None,
        origin_dedup_key: str | None = None,
        origin_approval: AgentTaskOriginApproval | None = None,
        parent_task_id: str | None = None,
        retry_limit: int = 0,
        plan_graph: PlanGraph | None = None,
        plan_graph_ref: str | None = None,
    ) -> AgentTaskRecord:
        if verification.mode != "off" and self.verifier is None:
            raise AgentTaskError(
                "non-off AgentTask verification requires the verification service"
            )
        task_id = plan_graph.task_id if plan_graph is not None else f"task_{uuid4().hex[:16]}"
        revision_id = plan_graph.revision_id if plan_graph is not None else f"revision_{uuid4().hex[:16]}"
        _validate_plan_graph_input(plan_graph, plan_graph_ref, task_id, revision_id)
        binding: ForgeSkillBinding | None = None
        runtime_binding: RuntimeBinding | None = None
        skill_instructions: str | None = None
        initial_skill_use: SkillUseRecord | None = None
        if self.binding_resolver is not None:
            if activation_id and origin_session_key:
                if self.activation_manager is None:
                    raise AgentTaskError("Skill activation manager is unavailable")
                activation = self.activation_manager.require_activation(
                    session_key=origin_session_key,
                    activation_id=activation_id,
                    role="primary",
                )
                candidate_id = activation.binding_candidate_id
                if not candidate_id:
                    raise AgentTaskError("primary Skill activation has no Forge binding candidate")
                try:
                    binding = await self.binding_resolver.freeze(candidate_id, task_id=task_id)
                except ForgeSkillBindingError as exc:
                    raise AgentTaskError(str(exc)) from exc
                if activation.content_sha256 != binding.skill_document_sha256:
                    raise AgentTaskError(
                        "activated SKILL.md does not match the installed Runtime binding"
                    )
                skill_instructions = self.activation_manager.instructions_for_activation(
                    session_key=origin_session_key, activation_id=activation_id,
                )
                initial_skill_use = SkillUseRecord(
                    use_id=f"skill_use_{uuid4().hex[:16]}",
                    activation_id=activation.activation_id,
                    skill_name=activation.skill_name,
                    skill_version=activation.skill_version,
                    content_sha256=activation.content_sha256,
                    instructions=skill_instructions,
                    decision_ref=f"task:{task_id}:create",
                )
            else:
                try:
                    runtime_binding = self.binding_resolver.freeze_runtime(task_id=task_id)
                except ForgeSkillBindingError as exc:
                    raise AgentTaskError(str(exc)) from exc
        task = AgentTaskRecord(
            task_id=task_id,
            task_description=task_description.strip(),
            verification=verification,
            parent_task_id=parent_task_id,
            retry_limit=retry_limit,
            revisions=[
                PlanRevision(
                    revision_id=revision_id,
                    number=1,
                    reason="initial plan",
                    plan_graph=plan_graph,
                    skill_binding_id=binding.binding_id if binding is not None else None,
                    runtime_binding_id=(
                        runtime_binding.binding_id if runtime_binding is not None else None
                    ),
                    skill_use_ids=(
                        (initial_skill_use.use_id,) if initial_skill_use is not None else ()
                    ),
                    plan_graph_ref=plan_graph_ref,
                    plan_graph_digest=plan_graph.graph_digest if plan_graph is not None else None,
                    planner_decision_digest=plan_graph.planner_decision_digest if plan_graph is not None else None,
                    policy_snapshot_digest=plan_graph.policy_snapshot_digest if plan_graph is not None else None,
                )
            ],
            active_revision_id=revision_id,
            primary_skill_binding=binding,
            primary_skill_instructions=skill_instructions,
            runtime_binding=runtime_binding,
            skill_uses=([initial_skill_use] if initial_skill_use is not None else []),
            runtime_snapshot_ref=(
                f"runtime:{binding.runtime_instance_id}"
                if binding is not None
                else f"runtime:{runtime_binding.runtime_instance_id}"
                if runtime_binding is not None else None
            ),
            origin_session_key=origin_session_key,
            origin_dedup_key=origin_dedup_key,
            origin_approval=origin_approval,
        )
        ownership_binding_id = (
            binding.binding_id if binding is not None
            else runtime_binding.binding_id if runtime_binding is not None
            else None
        )
        if ownership_binding_id is not None and self.runtime_task_binding_ids is not None:
            self.runtime_task_binding_ids.add(ownership_binding_id)
        try:
            self.store.create(task)
        except Exception:
            if ownership_binding_id is not None and self.runtime_task_binding_ids is not None:
                self.runtime_task_binding_ids.discard(ownership_binding_id)
            raise
        if self.experience is not None and origin_session_key:
            self.experience.bind_forge_task(
                task_id,
                session_key=origin_session_key,
                forge_binding=binding,
                skill_uses=task.skill_uses,
            )
        return task

    def get_task(self, task_id: str) -> AgentTaskRecord:
        return self.store.get(task_id)

    def record_skill_use(
        self,
        task_id: str,
        *,
        activation_id: str,
        skill_name: str,
        skill_version: str | None,
        content_sha256: str,
        instructions: str,
        decision_ref: str,
        node_id: str | None = None,
        attempt_id: str | None = None,
    ) -> SkillUseRecord:
        """Persist one actual method use; does not grant Tool or motion authority."""
        use = SkillUseRecord(
            use_id=f"skill_use_{uuid4().hex[:16]}",
            activation_id=activation_id,
            skill_name=skill_name,
            skill_version=skill_version,
            content_sha256=content_sha256,
            instructions=instructions,
            decision_ref=decision_ref,
            node_id=node_id,
            attempt_id=attempt_id,
        )
        return self.store.record_skill_use_once(task_id, use)

    def begin_revision(
        self,
        task_id: str,
        *,
        reason: str,
        plan_graph: PlanGraph | None = None,
        plan_graph_ref: str | None = None,
        preserved_node_ids: tuple[str, ...] = (),
        invalidated_node_ids: tuple[str, ...] = (),
        retry_parent_node_id: str | None = None,
        fresh_evidence_requirements: tuple[str, ...] = (),
        discovery_evidence_refs: tuple[str, ...] = (),
        replan_evidence_refs: tuple[str, ...] = (),
        node_settlements: list[NodeSettlement] | None = None,
        counterevidence: list[NodeSettlement] | None = None,
    ) -> AgentTaskRecord:
        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.AWAITING_REPLAN:
            raise AgentTaskError("a new PlanRevision requires awaiting_replan status")
        if task.replan_deadline is not None and utc_now() >= task.replan_deadline:
            failed = self.store.update(
                task_id,
                lambda current: _fail_replan(
                    current, "AgentTask replan deadline expired"
                ),
                event_type="plan_revision_expired",
            )
            self._schedule_experience(failed)
            raise AgentTaskError("AgentTask replan deadline expired")
        if _replan_count(task) >= self.max_replans:
            raise AgentTaskError(f"replan budget exhausted ({self.max_replans})")
        revision_id = plan_graph.revision_id if plan_graph is not None else f"revision_{uuid4().hex[:16]}"
        _validate_plan_graph_input(plan_graph, plan_graph_ref, task_id, revision_id)

        def mutate(current: AgentTaskRecord) -> None:
            current.active_revision.closed_at = utc_now()
            revision = PlanRevision(
                revision_id=revision_id,
                number=len(current.revisions) + 1,
                reason=reason.strip(),
                counts_toward_replan_budget=True,
                plan_graph=plan_graph,
                skill_binding_id=(
                    current.primary_skill_binding.binding_id
                    if current.primary_skill_binding is not None
                    else None
                ),
                runtime_binding_id=(
                    current.runtime_binding.binding_id
                    if current.runtime_binding is not None else None
                ),
                plan_graph_ref=plan_graph_ref,
                plan_graph_digest=plan_graph.graph_digest if plan_graph is not None else None,
                planner_decision_digest=plan_graph.planner_decision_digest if plan_graph is not None else None,
                policy_snapshot_digest=plan_graph.policy_snapshot_digest if plan_graph is not None else None,
                node_settlements=list(node_settlements or []),
                preserved_node_ids=tuple(preserved_node_ids),
                invalidated_node_ids=tuple(invalidated_node_ids),
                retry_parent_node_id=retry_parent_node_id,
                fresh_evidence_requirements=tuple(fresh_evidence_requirements),
                discovery_evidence_refs=tuple(discovery_evidence_refs),
                replan_evidence_refs=tuple(replan_evidence_refs),
                counterevidence=list(counterevidence or []),
            )
            current.revisions.append(revision)
            current.active_revision_id = revision.revision_id
            current.status = AgentTaskStatus.EXECUTING
            current.verdict = None
            current.replan_deadline = None
            current.replan_extension_used = False

        return self.store.update(task_id, mutate, event_type="plan_revision_started")

    def begin_continuation_revision(
        self,
        task_id: str,
        *,
        reason: str,
        plan_graph: PlanGraph,
        plan_graph_ref: str,
        evidence_refs: tuple[str, ...] = (),
    ) -> AgentTaskRecord:
        """Append a successful next plan segment without consuming recovery budget."""
        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.EXECUTING:
            raise AgentTaskError(
                "plan continuation requires an executing AgentTask; failure recovery uses begin_revision"
            )
        revision = task.active_revision
        if revision.plan_graph is None:
            raise AgentTaskError("plan continuation requires a materialized active PlanGraph")
        settlements = {item.node_id: item.status for item in revision.node_settlements}
        incomplete = tuple(
            node.node_id
            for node in revision.plan_graph.nodes
            if settlements.get(node.node_id) != "completed"
        )
        if incomplete:
            raise AgentTaskError(
                "plan continuation requires every active graph node to be completed; incomplete nodes: "
                + ", ".join(incomplete)
            )
        nonterminal = tuple(
            record.record_id
            for record in task.execution_records
            if record.ownership == "task"
            and record.semantics in {"action", "session"}
            and not record.terminal
        )
        if nonterminal:
            raise AgentTaskError(
                "plan continuation is blocked by non-terminal task-owned Action/Session records: "
                + ", ".join(nonterminal)
            )
        if not reason.strip():
            raise AgentTaskError("plan continuation reason must be non-empty")
        _validate_plan_graph_input(
            plan_graph,
            plan_graph_ref,
            task_id,
            plan_graph.revision_id,
        )

        source_revision_id = revision.revision_id

        def mutate(current: AgentTaskRecord) -> None:
            if current.status != AgentTaskStatus.EXECUTING:
                raise AgentTaskError("plan continuation requires an executing AgentTask")
            if current.active_revision_id != source_revision_id:
                raise AgentTaskError("plan continuation source revision is no longer active")
            current_revision = current.active_revision
            current_settlements = {
                item.node_id: item.status for item in current_revision.node_settlements
            }
            current_incomplete = tuple(
                node.node_id
                for node in current_revision.plan_graph.nodes
                if current_settlements.get(node.node_id) != "completed"
            ) if current_revision.plan_graph is not None else ("<missing-plan-graph>",)
            if current_incomplete:
                raise AgentTaskError(
                    "plan continuation requires every active graph node to be completed; "
                    "incomplete nodes: " + ", ".join(current_incomplete)
                )
            current_nonterminal = tuple(
                record.record_id
                for record in current.execution_records
                if record.ownership == "task"
                and record.semantics in {"action", "session"}
                and not record.terminal
            )
            if current_nonterminal:
                raise AgentTaskError(
                    "plan continuation is blocked by non-terminal task-owned Action/Session records: "
                    + ", ".join(current_nonterminal)
                )
            current.active_revision.closed_at = utc_now()
            current.revisions.append(
                PlanRevision(
                    revision_id=plan_graph.revision_id,
                    number=len(current.revisions) + 1,
                    reason=reason.strip(),
                    counts_toward_replan_budget=False,
                    skill_binding_id=(
                        current.primary_skill_binding.binding_id
                        if current.primary_skill_binding is not None
                        else None
                    ),
                    runtime_binding_id=(
                        current.runtime_binding.binding_id
                        if current.runtime_binding is not None
                        else None
                    ),
                    plan_graph=plan_graph,
                    plan_graph_ref=plan_graph_ref,
                    plan_graph_digest=plan_graph.graph_digest,
                    planner_decision_digest=plan_graph.planner_decision_digest,
                    policy_snapshot_digest=plan_graph.policy_snapshot_digest,
                    discovery_evidence_refs=tuple(evidence_refs),
                )
            )
            current.active_revision_id = plan_graph.revision_id
            current.verdict = None

        return self.store.update(
            task_id,
            mutate,
            event_type="plan_continuation_started",
            payload={
                "previous_revision_id": revision.revision_id,
                "revision_id": plan_graph.revision_id,
                "evidence_refs": list(evidence_refs),
            },
        )

    def claim_replan_attempt(
        self, task_id: str, *, attempt_started_at: datetime | None = None
    ) -> AgentTaskRecord:
        """Grant one bounded recovery lease when an Agent starts a revision submission."""

        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.AWAITING_REPLAN:
            raise AgentTaskError("a replan attempt requires awaiting_replan status")
        now = utc_now()
        started_at = attempt_started_at or now
        if task.replan_deadline is None or started_at >= task.replan_deadline:
            return task
        if task.replan_extension_used:
            return task

        def mutate(current: AgentTaskRecord) -> None:
            if current.replan_extension_used or current.replan_deadline is None:
                return
            current.replan_deadline = max(current.replan_deadline, now) + timedelta(
                seconds=self.replan_timeout_s
            )
            current.replan_extension_used = True

        return self.store.update(
            task_id,
            mutate,
            event_type="plan_revision_attempt_lease_claimed",
            payload={"bounded_extension_s": self.replan_timeout_s},
        )

    def expand_discovery_revision(
        self,
        task_id: str,
        *,
        plan_graph: PlanGraph,
        plan_graph_ref: str,
        discovery_evidence_refs: tuple[str, ...] = (),
        reason: str = "discovery completed; materialize semantic DAG",
    ) -> AgentTaskRecord:
        """Materialize a discovered graph under the same task identity.

        Discovery is a forward planning transition, not recovery and not a new
        task. It is allowed only while the initial revision has no graph.
        """
        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.EXECUTING:
            raise AgentTaskError("discovery expansion requires an executing AgentTask")
        existing_graph = task.active_revision.plan_graph
        if existing_graph is not None:
            revision = task.active_revision
            if (
                revision.execution_records
                or revision.node_settlements
                or revision.counterevidence
                or revision.verification_attempts
            ):
                raise AgentTaskError(
                    "discovery expansion requires an unmaterialized active revision "
                    "or a materialized revision with no execution facts"
                )
        if plan_graph.task_id != task_id:
            raise AgentTaskError("discovery PlanGraph task identity mismatch")
        required_queries = required_preplan_queries(task)
        completed_queries = {
            record.tool_id
            for record in task.active_revision.execution_records
            if record.semantics == "query" and _planning_record_status(record) == "succeeded"
        }
        missing_queries = tuple(sorted(required_queries - completed_queries))
        if missing_queries:
            raise DiscoveryRequiredError(
                "required task-bound discovery Queries are incomplete: "
                + ", ".join(missing_queries),
                missing=missing_queries,
            )
        _validate_plan_graph_input(plan_graph, plan_graph_ref, task_id, plan_graph.revision_id)

        def mutate(current: AgentTaskRecord) -> None:
            current.active_revision.closed_at = utc_now()
            current.revisions.append(PlanRevision(
                revision_id=plan_graph.revision_id,
                number=len(current.revisions) + 1,
                reason=reason.strip(),
                counts_toward_replan_budget=False,
                skill_binding_id=(
                    current.primary_skill_binding.binding_id
                    if current.primary_skill_binding is not None else None
                ),
                runtime_binding_id=(
                    current.runtime_binding.binding_id
                    if current.runtime_binding is not None else None
                ),
                plan_graph=plan_graph,
                plan_graph_ref=plan_graph_ref,
                plan_graph_digest=plan_graph.graph_digest,
                planner_decision_digest=plan_graph.planner_decision_digest,
                policy_snapshot_digest=plan_graph.policy_snapshot_digest,
                discovery_evidence_refs=tuple(discovery_evidence_refs),
            ))
            current.active_revision_id = plan_graph.revision_id

        event_type = (
            "plan_discovery_corrected"
            if existing_graph is not None
            else "plan_discovery_expanded"
        )
        return self.store.update(task_id, mutate, event_type=event_type)

    def materialize_plan_revision(
        self,
        task_id: str,
        *,
        plan_graph: PlanGraph,
        plan_graph_ref: str,
        evidence_refs: tuple[str, ...] = (),
        reason: str = "Agent selected a task-conditioned semantic DAG",
    ) -> AgentTaskRecord:
        """Materialize an Agent-selected DAG without imposing an observation phase."""
        return self.expand_discovery_revision(
            task_id,
            plan_graph=plan_graph,
            plan_graph_ref=plan_graph_ref,
            discovery_evidence_refs=evidence_refs,
            reason=reason,
        )

    def record_node_settlement(self, settlement: NodeSettlement) -> AgentTaskRecord:
        """Persist one immutable semantic-node fact in the active revision."""
        task = self.store.get(settlement.task_id)
        if settlement.revision_id != task.active_revision_id:
            raise AgentTaskError("NodeSettlement is not bound to the active revision")
        if task.active_revision.plan_graph is None or settlement.node_id not in {
            node.node_id for node in task.active_revision.plan_graph.nodes
        }:
            raise AgentTaskError("NodeSettlement references no active PlanGraph node")
        existing = next(
            (item for item in task.active_revision.node_settlements if item.node_id == settlement.node_id),
            None,
        )
        if existing is not None:
            if existing.status == settlement.status:
                return task
            raise AgentTaskError(
                "conflicting NodeSettlement already exists for this node "
                f"{settlement.node_id} ({existing.status} vs {settlement.status})"
            )

        def mutate(current: AgentTaskRecord) -> None:
            revision = current.active_revision
            existing = next(
                (item for item in revision.node_settlements if item.node_id == settlement.node_id),
                None,
            )
            if existing is not None:
                if existing.status == settlement.status:
                    return
                raise AgentTaskError(
                    "conflicting NodeSettlement already exists for this node "
                    f"{settlement.node_id} ({existing.status} vs {settlement.status})"
                )
            revision.node_settlements.append(settlement)

        return self.store.update(
            settlement.task_id,
            mutate,
            event_type="node_settled",
            payload={
                "revision_id": settlement.revision_id,
                "node_id": settlement.node_id,
                "status": settlement.status,
            },
        )

    def reconcile_terminal_settlements(self, task_id: str) -> AgentTaskRecord:
        """Persist missing settlements for already-terminal planning-bound records.

        This is a read/reconcile operation over Coordinator-owned facts.  It never
        invokes a Gateway Tool, retries an invocation, or replaces a PlanGraph.
        Repeated calls are idempotent because an existing node settlement is left
        untouched.
        """
        task = self.store.get(task_id)
        revision = task.active_revision
        graph = revision.plan_graph
        if graph is None:
            return task
        settled = {item.node_id for item in revision.node_settlements}
        for record in revision.execution_records:
            if (
                not record.terminal
                or record.node_id is None
                or record.revision_id != revision.revision_id
                or record.node_id in settled
            ):
                continue
            result = _tool_result_from_execution(task, record)
            if result is None:
                continue
            node = next(
                (item for item in graph.nodes if item.node_id == record.node_id),
                None,
            )
            if node is None:
                raise AgentTaskError(
                    f"planning-bound Tool record references unknown PlanGraph node: {record.node_id}"
                )
            settlement = settle_node(
                node,
                result,
                current_scene_revision=_task_scene_revision(
                    task, exclude_record_id=record.record_id
                ),
            )
            self.record_node_settlement(settlement)
            settled.add(record.node_id)
            task = self.store.get(task_id)
        return task

    def record_node_counterevidence(self, settlement: NodeSettlement) -> AgentTaskRecord:
        """Append postcondition counterevidence without rewriting prior success."""
        task = self.store.get(settlement.task_id)
        if settlement.revision_id != task.active_revision_id:
            raise AgentTaskError("counterevidence is not bound to the active revision")
        if task.active_revision.plan_graph is None or settlement.node_id not in {
            node.node_id for node in task.active_revision.plan_graph.nodes
        }:
            raise AgentTaskError("counterevidence references no active PlanGraph node")
        return self.store.update(
            settlement.task_id,
            lambda current: current.active_revision.counterevidence.append(settlement),
            event_type="node_counterevidence_recorded",
            payload={
                "revision_id": settlement.revision_id,
                "node_id": settlement.node_id,
                "status": settlement.status,
            },
        )

    def request_replan(self, task_id: str, *, reason: str) -> AgentTaskRecord:
        """Move a task into the existing bounded recovery state."""
        task = self.store.get(task_id)
        if task.terminal:
            raise AgentTaskError("cannot request replan for a terminal AgentTask")
        if _replan_count(task) >= self.max_replans:
            raise AgentTaskError(f"replan budget exhausted ({self.max_replans})")

        def mutate(current: AgentTaskRecord) -> None:
            current.status = AgentTaskStatus.AWAITING_REPLAN
            current.replan_deadline = utc_now() + timedelta(seconds=self.replan_timeout_s)
            current.replan_extension_used = False
            current.evidence_errors.append(f"replan requested: {reason.strip()}")

        return self.store.update(task_id, mutate, event_type="plan_replan_requested")

    def fail_replan(self, task_id: str, *, reason: str) -> AgentTaskRecord:
        """Persist a terminal recovery failure through the existing task state."""
        reason = reason.strip()
        if not reason:
            raise AgentTaskError("replan failure reason must be non-empty")
        task = self.store.get(task_id)
        if task.terminal:
            return task
        recoverable_statuses = {
            AgentTaskStatus.EXECUTING,
            AgentTaskStatus.AWAITING_REPLAN,
        }
        if task.status not in recoverable_statuses:
            raise AgentTaskError(
                f"cannot fail replan while AgentTask is {task.status.value}"
            )

        def mutate(current: AgentTaskRecord) -> None:
            if current.status not in recoverable_statuses:
                raise AgentTaskError(
                    f"cannot fail replan while AgentTask is {current.status.value}"
                )
            current.status = AgentTaskStatus.FAILED
            current.replan_deadline = None
            current.replan_extension_used = False
            current.evidence_errors.append(f"replan failed: {reason}")

        result = self.store.update(
            task_id,
            mutate,
            event_type="plan_replan_failed",
            payload={"reason": reason},
        )
        self._schedule_experience(result)
        return result

    def request_clarification(
        self,
        task_id: str,
        *,
        question: str,
        node_id: str | None = None,
    ) -> AgentTaskRecord:
        """Persist a user clarification checkpoint for the current task."""
        task = self.store.get(task_id)
        if task.terminal:
            raise AgentTaskError("cannot request clarification for a terminal AgentTask")
        question = question.strip()
        if not question:
            raise AgentTaskError("clarification question must be non-empty")
        if task.status not in {AgentTaskStatus.EXECUTING, AgentTaskStatus.WAITING_FOR_USER}:
            raise AgentTaskError("clarification requires an executing AgentTask")

        def mutate(current: AgentTaskRecord) -> None:
            current.status = AgentTaskStatus.WAITING_FOR_USER
            current.clarification_id = f"clarification_{uuid4().hex[:16]}"
            current.clarification_question = question
            current.clarification_node_id = node_id
            current.clarification_answer = None

        return self.store.update(task_id, mutate, event_type="task_clarification_requested")

    def resolve_clarification(self, task_id: str, *, answer: str) -> AgentTaskRecord:
        """Persist a user answer and make the task runnable again."""
        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.WAITING_FOR_USER:
            raise AgentTaskError("AgentTask is not waiting for clarification")
        answer = answer.strip()
        if not answer:
            raise AgentTaskError("clarification answer must be non-empty")

        def mutate(current: AgentTaskRecord) -> None:
            current.status = AgentTaskStatus.EXECUTING
            current.clarification_answer = answer

        return self.store.update(task_id, mutate, event_type="task_clarification_resolved")

    def request_pause(self, task_id: str, *, reason: str = "user_requested") -> AgentTaskRecord:
        """Persist a checkpoint pause request without cancelling in-flight Actions."""
        task = self.store.get(task_id)
        if task.terminal:
            return task

        def mutate(current: AgentTaskRecord) -> None:
            current.pause_requested = True
            current.evidence_errors.append(f"pause requested: {reason.strip()}")

        return self.store.update(task_id, mutate, event_type="task_pause_requested")

    def resume_task(self, task_id: str) -> AgentTaskRecord:
        """Clear a persisted checkpoint pause request."""
        return self.store.update(
            task_id,
            lambda current: setattr(current, "pause_requested", False),
            event_type="task_pause_resumed",
        )

    def begin_revision_from_delta(
        self,
        task_id: str,
        delta: ReplanDelta,
        *,
        plan_graph: PlanGraph,
        plan_graph_ref: str,
        reason: str | None = None,
        counterevidence_refs: tuple[str, ...] = (),
        counterevidence: NodeSettlement | None = None,
    ) -> AgentTaskRecord:
        """Adapt a pure planning replan delta into the coordinator-owned revision path."""
        task = self.store.get(task_id)
        if delta.task_id != task_id or delta.revision_id != task.active_revision_id:
            raise AgentTaskError("ReplanDelta is not bound to the active AgentTask revision")
        if plan_graph.task_id != task_id or plan_graph.revision_id == task.active_revision_id:
            raise AgentTaskError("replacement PlanGraph must target this task and a new revision")
        active_settlements = {
            item.node_id: item for item in task.active_revision.node_settlements
        }
        active_nodes = {
            node.node_id: node
            for node in (
                task.active_revision.plan_graph.nodes
                if task.active_revision.plan_graph is not None
                else ()
            )
        }
        replacement_nodes = {node.node_id: node for node in plan_graph.nodes}
        for node_id in (
            set(delta.preserve_node_ids)
            & set(active_settlements)
            & set(replacement_nodes)
        ):
            if (
                node_id not in active_nodes
                or plan_node_digest(active_nodes[node_id])
                != plan_node_digest(replacement_nodes[node_id])
            ):
                raise AgentTaskError(
                    f"cannot preserve node {node_id!r}: replacement content changed"
                )
        preserved = tuple(
            item.model_copy(update={"revision_id": plan_graph.revision_id})
            for node_id, item in active_settlements.items()
            if node_id in set(delta.preserve_node_ids)
            and node_id in {node.node_id for node in plan_graph.nodes}
        )
        return self.begin_revision(
            task_id,
            reason=reason or delta.reason,
            plan_graph=plan_graph,
            plan_graph_ref=plan_graph_ref,
            preserved_node_ids=delta.preserve_node_ids,
            invalidated_node_ids=delta.invalidate_node_ids,
            retry_parent_node_id=delta.retry_parent_node_id,
            fresh_evidence_requirements=delta.fresh_evidence_requirements,
            node_settlements=list(preserved),
            replan_evidence_refs=tuple(counterevidence_refs),
            counterevidence=(
                [counterevidence.model_copy(update={"revision_id": plan_graph.revision_id})]
                if counterevidence is not None else []
            ),
        )

    async def invoke_query(
        self,
        task_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        timeout_ms: int | None = None,
        planning_binding: PlanningExecutionBinding | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tool = await self._require_binding_tool(task_id, tool_id, "query")
        if tool.default_timeout_ms is not None:
            timeout_ms = max(timeout_ms or 0, tool.default_timeout_ms)
        record_id, caller = self._append_execution(
            task_id, tool_id, "query", arguments, tool=tool, planning_binding=planning_binding
        )
        try:
            response = await self.client.invoke_query_tool(
                tool_id, arguments, caller_id=caller, timeout_ms=timeout_ms
            )
        except Exception as exc:
            self._finish_execution(
                task_id,
                record_id,
                status="unknown",
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            raise
        self._finish_execution(task_id, record_id, status="succeeded", response=response)
        # Keep Gateway data unchanged; the coordinator owns this local receipt.
        record = _task_execution(self.store.get(task_id), record_id)
        return {
            "paos_record": {
                "task_id": task_id,
                "revision_id": record.revision_id,
                "record_id": record.record_id,
                "evidence_refs": list(record.evidence_refs),
            },
            **{key: value for key, value in response.items() if key != "paos_record"},
        }

    async def start_action(
        self,
        task_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        timeout_ms: int | None = None,
        planning_binding: PlanningExecutionBinding | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task = self._require_executable(task_id)
        binding = _normalize_planning_binding(planning_binding)
        if binding is not None:
            _validate_planning_execution_selection(
                task.active_revision,
                binding,
                tool_id=tool_id,
                semantics="action",
                arguments=arguments,
            )
        if any(
            item.semantics == "action"
            and item.tool_id == tool_id
            and item.arguments == arguments
            and item.status == "unknown"
            for item in task.execution_records
        ):
            raise AgentTaskError(
                "an identical Action has unknown remote state; reconcile it instead of resending"
            )
        tool = await self._require_binding_tool(task_id, tool_id, "action")
        if task.before_snapshot_ref is None:
            await self._capture_before(task_id)
        record_id, caller = self._append_execution(
            task_id, tool_id, "action", arguments, tool=tool, planning_binding=binding
        )
        invocation_id: str | None = None
        attempt_id: str | None = None
        try:
            response = await self.client.invoke_action(
                tool_id, arguments, caller_id=caller, timeout_ms=timeout_ms
            )
            data = _response_data(response)
            invocation_id = data.get("invocation_id")
            attempt_id = data.get("attempt_id")
            if not isinstance(invocation_id, str) or not invocation_id:
                raise AgentTaskError("Gateway Action response omitted invocation_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                raise ForgeToolAPIError(
                    "Gateway Action response omitted attempt_id for invocation "
                    f"{invocation_id}",
                    payload=response,
                )
        except Exception as exc:
            remote_invocation_id, remote_attempt_id = _remote_identity(exc)
            invocation_id = remote_invocation_id or invocation_id
            attempt_id = remote_attempt_id or attempt_id
            self._finish_execution(
                task_id,
                record_id,
                status="unknown",
                invocation_id=invocation_id,
                attempt_id=attempt_id,
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            if invocation_id and self.runtime_invocation_ids is not None:
                self._track_remote_identity(
                    task_id,
                    record_id,
                    invocation_id,
                    tracker=self.runtime_invocation_ids,
                    response={
                        "ok": False,
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    },
                    kind="Action",
                )
            raise

        def mutate(current: AgentTaskRecord) -> None:
            record = _task_execution(current, record_id)
            record.status = "accepted"
            record.invocation_id = invocation_id
            record.attempt_id = attempt_id
            record.response = response
            record.evidence_refs = [f"invocation:{invocation_id}"]
            record.updated_at = utc_now()

        self.store.update(task_id, mutate, event_type="action_accepted")
        return self._track_remote_identity(
            task_id,
            record_id,
            invocation_id,
            tracker=self.runtime_invocation_ids,
            response=response,
            kind="Action",
        )

    def observe_action(
        self,
        task_id: str,
        invocation_id: str,
        response: dict[str, Any],
        *,
        reconcile_settlement: bool = True,
    ) -> None:
        task = self.store.get(task_id)
        record = _owned_execution(task, invocation_id, semantics="action")
        if task.terminal:
            return
        observed_status = _tool_status(response, default=record.status)
        status = (
            record.status
            if not reconcile_settlement and observed_status in TERMINAL_TOOL_STATUSES
            else observed_status
        )

        def mutate(current: AgentTaskRecord) -> None:
            target = _task_execution(current, record.record_id)
            target.status = status
            target.response = response
            target.updated_at = utc_now()

        self.store.update(task.task_id, mutate, event_type="action_observed")
        if reconcile_settlement:
            self.reconcile_terminal_settlements(task_id)
        if (
            reconcile_settlement
            and status in TERMINAL_TOOL_STATUSES - {"unknown"}
            and self.runtime_invocation_ids is not None
        ):
            self.runtime_invocation_ids.discard(invocation_id)

    def mark_execution_unknown(
        self, task_id: str, record_id: str, *, code: str, message: str
    ) -> None:
        """Persist an execution with no recoverable remote identity as unknown."""
        task = self.store.get(task_id)
        _task_execution(task, record_id)
        self._finish_execution(
            task_id,
            record_id,
            status="unknown",
            error={"type": "ExecutionUnknown", "code": code, "message": message},
        )

    def require_action_invocation(
        self, task_id: str, invocation_id: str
    ) -> ToolExecutionRecord:
        return _owned_execution(
            self.store.get(task_id), invocation_id, semantics="action"
        )

    def require_session_invocation(
        self, task_id: str, invocation_id: str
    ) -> ToolExecutionRecord:
        return _owned_execution(
            self.store.get(task_id), invocation_id, semantics="session"
        )

    def record_cancel_response(
        self, task_id: str, invocation_id: str, response: dict[str, Any]
    ) -> None:
        task = self.store.get(task_id)
        record = _owned_execution(task, invocation_id, semantics="action")
        if task.terminal:
            return

        def mutate(current: AgentTaskRecord) -> None:
            target = _task_execution(current, record.record_id)
            target.response = response
            target.updated_at = utc_now()

        self.store.update(task.task_id, mutate, event_type="action_cancel_requested")

    async def start_session(
        self,
        task_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        ownership: Literal["task", "shared"] = "task",
        planning_binding: PlanningExecutionBinding | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if ownership not in {"task", "shared"}:
            raise AgentTaskError("runtime-owned Sessions may only be created by RuntimeManager")
        tool = await self._require_binding_tool(task_id, tool_id, "session")
        record_id, caller = self._append_execution(
            task_id,
            tool_id,
            "session",
            arguments,
            tool=tool,
            ownership=ownership,
            planning_binding=planning_binding,
        )
        invocation_id: str | None = None
        attempt_id: str | None = None
        try:
            response = await self.client.start_session(
                tool_id, arguments, caller_id=caller
            )
            data = _response_data(response)
            invocation_id = data.get("invocation_id")
            attempt_id = data.get("attempt_id")
            if not isinstance(invocation_id, str) or not invocation_id:
                raise AgentTaskError("Gateway Session response omitted invocation_id")
            if not isinstance(attempt_id, str):
                attempt_id = None
        except Exception as exc:
            remote_invocation_id, remote_attempt_id = _remote_identity(exc)
            invocation_id = remote_invocation_id or invocation_id
            attempt_id = remote_attempt_id or attempt_id
            self._finish_execution(
                task_id,
                record_id,
                status="unknown",
                invocation_id=invocation_id,
                attempt_id=attempt_id,
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            if invocation_id and self.runtime_session_ids is not None:
                self._track_remote_identity(
                    task_id,
                    record_id,
                    invocation_id,
                    tracker=self.runtime_session_ids,
                    response={
                        "ok": False,
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    },
                    kind="Session",
                )
            raise

        def mutate(current: AgentTaskRecord) -> None:
            record = _task_execution(current, record_id)
            record.status = "accepted"
            record.invocation_id = invocation_id
            record.attempt_id = attempt_id
            record.response = response
            record.evidence_refs = [f"session:{invocation_id}"]
            record.updated_at = utc_now()

        self.store.update(task_id, mutate, event_type="session_accepted")
        return self._track_remote_identity(
            task_id,
            record_id,
            invocation_id,
            tracker=self.runtime_session_ids,
            response=response,
            kind="Session",
        )

    def observe_session(
        self,
        task_id: str,
        invocation_id: str,
        response: dict[str, Any],
        *,
        reconcile_settlement: bool = True,
    ) -> None:
        task = self.store.get(task_id)
        record = _owned_execution(task, invocation_id, semantics="session")
        observed_status = _tool_status(response, default=record.status)
        status = (
            record.status
            if not reconcile_settlement and observed_status in TERMINAL_TOOL_STATUSES
            else observed_status
        )

        def mutate(current: AgentTaskRecord) -> None:
            target = _task_execution(current, record.record_id)
            target.status = status
            target.response = response
            target.updated_at = utc_now()

        self.store.update(task_id, mutate, event_type="session_observed")
        if reconcile_settlement:
            self.reconcile_terminal_settlements(task_id)
        if (
            reconcile_settlement
            and status in TERMINAL_TOOL_STATUSES - {"unknown"}
            and self.runtime_session_ids is not None
        ):
            self.runtime_session_ids.discard(invocation_id)

    async def stop_session(self, task_id: str, invocation_id: str) -> dict[str, Any]:
        task = self.store.get(task_id)
        record = _owned_execution(task, invocation_id, semantics="session")
        if record.ownership != "task":
            raise AgentTaskError(
                f"{record.ownership}-owned Session must be stopped by its Runtime owner"
            )
        response = await self.client.stop_session(invocation_id)

        def mutate(current: AgentTaskRecord) -> None:
            target = _task_execution(current, record.record_id)
            target.response = response
            target.updated_at = utc_now()

        self.store.update(task_id, mutate, event_type="session_stop_requested")
        return response

    async def cancel_task(self, task_id: str, *, reason: str) -> AgentTaskRecord:
        task = self.store.get(task_id)
        if task.terminal:
            self._schedule_experience(task)
            return task
        pending = [
            item
            for item in task.execution_records
            if (
                item.semantics == "action"
                or (item.semantics == "session" and item.ownership == "task")
            )
            and not item.terminal
            and item.invocation_id
        ]
        responses: dict[str, Any] = {}
        for item in pending:
            invocation_id = item.invocation_id
            assert invocation_id is not None
            try:
                responses[invocation_id] = (
                    await self.client.stop_session(invocation_id)
                    if item.semantics == "session"
                    else await self.client.cancel_invocation(invocation_id)
                )
            except Exception as exc:
                responses[invocation_id] = {
                    "ok": False,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }

        def mutate(current: AgentTaskRecord) -> None:
            current.cancellation_requested = True
            has_nonterminal_owned_execution = has_unsettled_owned_execution(current)
            current.status = (
                AgentTaskStatus.CANCELLING
                if pending or has_nonterminal_owned_execution
                else _cancel_terminal_status(current)
            )
            current.evidence_errors.append(f"task cancellation requested: {reason.strip()}")
            for invocation_id, response in responses.items():
                target = next(
                    item for item in current.execution_records if item.invocation_id == invocation_id
                )
                target.response = response
                target.updated_at = utc_now()

        result = self.store.update(
            task_id, mutate, event_type="task_cancel_requested"
        )
        if result.terminal:
            self._schedule_experience(result)
        return result

    async def finalize_task(self, task_id: str) -> AgentTaskRecord:
        task = self.store.get(task_id)
        if task.terminal:
            return task
        pending = [
            item.invocation_id or item.record_id
            for item in task.execution_records
            if (
                item.semantics == "action"
                or (item.semantics == "session" and item.ownership == "task")
            )
            and not item.terminal
        ]
        if pending:
            raise TaskNotReadyForFinalizationError(
                "cannot finalize while task-owned Action/Session invocation(s) are non-terminal: "
                + ", ".join(pending),
                reason="active_invocation",
            )
        graph = task.active_revision.plan_graph
        if graph is not None:
            settlements = {
                item.node_id: item.status
                for item in task.active_revision.node_settlements
            }
            incomplete = tuple(
                node.node_id
                for node in graph.nodes
                if settlements.get(node.node_id) != "completed"
            )
            if incomplete:
                raise TaskNotReadyForFinalizationError(
                    "cannot finalize while active PlanGraph has incomplete node settlements: "
                    + ", ".join(incomplete),
                    reason="incomplete_plan",
                )
        if not task.execution_records:
            raise TaskNotReadyForFinalizationError(
                "cannot finalize an AgentTask without Tool executions",
                reason="incomplete_plan",
            )
        await self._capture_after(task_id)
        task = self.store.get(task_id)
        if task.cancellation_requested:
            status = _cancel_terminal_status(task)
            result = self.store.update(
                task_id,
                lambda current: setattr(current, "status", status),
                event_type="task_cancelled",
            )
            self._schedule_experience(result)
            return result

        mode = task.verification.mode
        if mode == "off":
            status = (
                AgentTaskStatus.SUCCEEDED
                if _execution_facts_succeeded(task)
                else AgentTaskStatus.FAILED
            )
            result = self.store.update(
                task_id,
                lambda current: setattr(current, "status", status),
                event_type="task_finalized_from_execution",
            )
            self._schedule_experience(result)
            return result
        if self.verifier is None:
            return self._verification_error(
                task_id, "semantic verification is enabled but verifier is unavailable"
            )

        lessons = (
            self.experience.verification_lessons_for_root(task_id)
            if self.experience is not None
            else "[]"
        )
        try:
            verdict, request, attempt = await self.verifier.verify_agent_task(
                task,
                events=self.store.events(task_id),
                lessons=lessons,
                source="auto",
                mode="apply",
            )
        except Exception as exc:
            return self._verification_error(
                task_id, str(exc) or type(exc).__name__
            )

        def mutate(current: AgentTaskRecord) -> None:
            current.verdict = verdict
            current.verification_attempts.append(attempt)
            current.active_revision.verdict = verdict
            current.active_revision.verification_attempts.append(attempt)
            if current.verification.mode == "audit":
                current.status = (
                    AgentTaskStatus.SUCCEEDED
                    if _execution_facts_succeeded(current)
                    else AgentTaskStatus.FAILED
                )
            elif current.verification.mode == "recovery" and verdict.verdict == "replan_required":
                if _replan_count(current) >= self.max_replans:
                    current.status = AgentTaskStatus.FAILED
                    current.evidence_errors.append(
                        f"replan limit reached ({self.max_replans}): {verdict.reason}"
                    )
                else:
                    current.status = AgentTaskStatus.AWAITING_REPLAN
                    current.replan_deadline = utc_now() + timedelta(
                        seconds=self.replan_timeout_s
                    )
            elif verdict.verdict == "success":
                current.status = AgentTaskStatus.SUCCEEDED
            else:
                current.status = AgentTaskStatus.FAILED

        result = self.store.update(task_id, mutate, event_type="task_verified")
        result = self._apply_verifier_retention(task_id, request, result)
        if result.terminal:
            self._schedule_experience(result)
        return result

    def _apply_verifier_retention(
        self,
        task_id: str,
        request: Any,
        result: AgentTaskRecord,
    ) -> AgentTaskRecord:
        """Apply Evidence retention only after a terminal semantic outcome."""

        if not result.terminal:
            return result
        retention = getattr(self.verifier, "apply_retention", None)
        if not callable(retention):
            return result
        try:
            summary = retention(request, final_status=result.status.value)
        except Exception as exc:
            error_type = type(exc).__name__
            return self.store.update(
                task_id,
                lambda current: current.evidence_errors.append(
                    "evidence retention failed: " + error_type
                ),
                event_type="evidence_retention_failed",
                payload={"error_type": error_type},
            )
        error_count = (
            len(summary.get("errors", [])) if isinstance(summary, dict) else 0
        )
        status = summary.get("status", "unknown") if isinstance(summary, dict) else "unknown"

        def record_retention_summary(current: AgentTaskRecord) -> None:
            if error_count:
                current.evidence_errors.append(
                    f"evidence retention completed: status={status}, errors={error_count}"
                )

        return self.store.update(
            task_id,
            record_retention_summary,
            event_type="evidence_retention_applied",
            payload={"status": status, "error_count": error_count},
        )

    def _verification_error(self, task_id: str, message: str) -> AgentTaskRecord:
        task = self.store.get(task_id)
        status = (
            AgentTaskStatus.SUCCEEDED
            if task.verification.mode == "audit"
            and _execution_facts_succeeded(task)
            else AgentTaskStatus.FAILED
        )

        def mutate(current: AgentTaskRecord) -> None:
            current.status = status
            current.evidence_errors.append(f"verification failed: {message}")
            current.verification_attempts.append(
                VerificationAttempt(
                    attempt_id=f"verification_{uuid4().hex[:12]}",
                    error=message,
                )
            )
            current.active_revision.verification_attempts.append(
                current.verification_attempts[-1]
            )

        result = self.store.update(
            task_id,
            mutate,
            event_type="task_verification_failed",
        )
        self._schedule_experience(result)
        return result

    async def reconcile_nonterminal(self) -> AgentTaskRecord | None:
        """Repair local execution facts from Gateway GETs without redispatching POSTs."""
        task = self.store.active()
        if task is None:
            return None
        binding = task.primary_skill_binding
        if binding is not None and self.binding_resolver is not None:
            try:
                self.binding_resolver.validate_runtime(binding)
            except ForgeSkillBindingError:
                # Leave persisted facts untouched until their owning Runtime returns.
                # Startup must still allow status inspection and user-directed recovery.
                return task
        runtime_binding = task.runtime_binding
        if runtime_binding is not None and self.binding_resolver is not None:
            try:
                self.binding_resolver.validate_runtime_binding(runtime_binding)
            except ForgeSkillBindingError:
                return task
        ownership_binding_id = (
            binding.binding_id if binding is not None
            else runtime_binding.binding_id if runtime_binding is not None else None
        )
        if ownership_binding_id is not None and self.runtime_task_binding_ids is not None:
            self.runtime_task_binding_ids.add(ownership_binding_id)
        for record in task.execution_records:
            if record.terminal or record.semantics == "query":
                continue
            if not record.invocation_id:
                self._finish_execution(
                    task.task_id,
                    record.record_id,
                    status="unknown",
                    error={
                        "type": "RecoveryUnknown",
                        "message": (
                            "dispatch intent has no invocation identity; request was not resent"
                        ),
                    },
                )
                continue
            tracker = (
                self.runtime_session_ids
                if record.semantics == "session"
                else self.runtime_invocation_ids
            )
            if tracker is not None:
                tracker.add(record.invocation_id)
            try:
                status_response = await self.client.invocation_status(record.invocation_id)
                observer = (
                    self.observe_session
                    if record.semantics == "session"
                    else self.observe_action
                )
                observer(
                    task.task_id,
                    record.invocation_id,
                    status_response,
                    reconcile_settlement=False,
                )
                result_response = await self.client.invocation_result(record.invocation_id)
                observer(task.task_id, record.invocation_id, result_response)
            except Exception as exc:
                self._finish_execution(
                    task.task_id,
                    record.record_id,
                    status="unknown",
                    invocation_id=record.invocation_id,
                    attempt_id=record.attempt_id,
                    error={"type": type(exc).__name__, "message": str(exc)},
                )
                continue
        return self.store.get(task.task_id)

    def capabilities_summary(self) -> str:
        return (
            "Forge execution uses a frozen AgentTask Runtime binding, enrolled Tool contracts, "
            "and the Gateway Tool API; Skills are optional Agent-selected methods. Query is "
            "read-only; Action admission is not task success; "
            "task-owned Sessions must be stopped before finalization."
        )

    def _require_executable(self, task_id: str) -> AgentTaskRecord:
        task = self.store.get(task_id)
        if task.status != AgentTaskStatus.EXECUTING:
            raise AgentTaskError(
                f"AgentTask {task_id} is not accepting Tool calls: {task.status.value}"
            )
        return task

    async def _require_binding_tool(
        self,
        task_id: str,
        tool_id: str,
        semantics: Literal["query", "action", "session"],
    ) -> BoundToolSpec:
        task = self._require_executable(task_id)
        binding = task.primary_skill_binding
        if binding is None and task.runtime_binding is None and self.binding_resolver is None:
            return BoundToolSpec(
                tool_id=tool_id,
                semantics=semantics,
                spec_sha256=canonical_sha256(
                    {"tool_id": tool_id, "semantics": semantics, "unbound": True}
                ),
                ready_at_binding=True,
            )
        if self.binding_resolver is None:
            raise AgentTaskError("AgentTask has no managed Runtime binding")
        try:
            if binding is not None:
                return await self.binding_resolver.validate_tool(binding, tool_id, semantics)
            if task.runtime_binding is None:
                raise AgentTaskError("AgentTask has no Runtime binding")
            existing = next((item for item in task.tool_bindings if item.tool_id == tool_id), None)
            if existing is not None:
                if existing.semantics != semantics:
                    raise AgentTaskError(f"Forge Tool {tool_id!r} semantics changed")
                self.binding_resolver.validate_runtime_binding(task.runtime_binding)
                return existing
            enrolled = await self.binding_resolver.enroll_tool(
                task.runtime_binding, tool_id, semantics
            )
            def enroll(current: AgentTaskRecord) -> None:
                existing = next(
                    (item for item in current.tool_bindings if item.tool_id == tool_id), None
                )
                if existing is None:
                    current.tool_bindings.append(enrolled)
                elif existing != enrolled:
                    raise AgentTaskError(
                        f"Forge Tool {tool_id!r} contract changed during enrollment"
                    )

            self.store.update(
                task_id,
                enroll,
                event_type="tool_contract_enrolled",
                payload={"tool_id": tool_id, "spec_sha256": enrolled.spec_sha256},
            )
            current = self.store.get(task_id)
            return next(item for item in current.tool_bindings if item.tool_id == tool_id)
        except ForgeSkillBindingError as exc:
            raise AgentTaskError(str(exc)) from exc

    def _append_execution(
        self,
        task_id: str,
        tool_id: str,
        semantics: Literal["query", "action", "session"],
        arguments: dict[str, Any],
        *,
        tool: BoundToolSpec,
        ownership: Literal["task", "runtime", "shared"] = "task",
        planning_binding: PlanningExecutionBinding | dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        task = self._require_executable(task_id)
        binding = _normalize_planning_binding(planning_binding)
        if binding is not None and task.active_revision.plan_graph_digest is None:
            raise AgentTaskError("planning-bound Tool execution requires a PlanGraph-bound revision")
        record_id = f"tool_{uuid4().hex[:16]}"
        caller_id = f"paos:{task_id}:{task.active_revision_id}:{record_id}"

        def mutate(current: AgentTaskRecord) -> None:
            if binding is not None:
                if any(
                    item.node_id == binding.node_id
                    for item in current.active_revision.execution_records
                ):
                    raise AgentTaskError(
                        "planning node already has an execution record"
                    )
                _validate_planning_execution_selection(
                    current.active_revision,
                    binding,
                    tool_id=tool_id,
                    semantics=semantics,
                    arguments=arguments,
                )
            current.active_revision.execution_records.append(
                ToolExecutionRecord(
                    record_id=record_id,
                    revision_id=current.active_revision_id,
                    tool_id=tool_id,
                    semantics=semantics,
                    skill_binding_id=(
                        current.primary_skill_binding.binding_id
                        if current.primary_skill_binding is not None
                        else None
                    ),
                    runtime_binding_id=(
                        current.runtime_binding.binding_id
                        if current.runtime_binding is not None
                        else None
                    ),
                    skill_use_ids=tuple(current.active_revision.skill_use_ids),
                    tool_spec_sha256=tool.spec_sha256,
                    caller_id=caller_id,
                    node_id=binding.node_id if binding is not None else None,
                    node_digest=binding.node_digest if binding is not None else None,
                    obligation_id=binding.obligation_id if binding is not None else None,
                    input_binding_digest=(
                        binding.input_binding_digest if binding is not None else None
                    ),
                    decision_trace_ref=(
                        binding.decision_trace_ref if binding is not None else None
                    ),
                    ownership=ownership,
                    arguments=dict(arguments),
                    evidence_refs=[f"tool:{record_id}"],
                )
            )

        self.store.update(task_id, mutate, event_type=f"{semantics}_started")
        return record_id, caller_id

    def _finish_execution(
        self,
        task_id: str,
        record_id: str,
        *,
        status: str,
        invocation_id: str | None = None,
        attempt_id: str | None = None,
        response: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        def mutate(current: AgentTaskRecord) -> None:
            record = _task_execution(current, record_id)
            record.status = status  # type: ignore[assignment]
            record.invocation_id = invocation_id or record.invocation_id
            record.attempt_id = attempt_id or record.attempt_id
            record.response = response
            record.error = error
            record.updated_at = utc_now()

        self.store.update(task_id, mutate, event_type="tool_execution_finished")
        self.reconcile_terminal_settlements(task_id)
        self._project_query_failure_recovery(task_id, record_id)

    def _project_query_failure_recovery(self, task_id: str, record_id: str) -> None:
        """Expose a terminal planning Query failure through the recovery lifecycle.

        Pre-graph discovery remains open-ended, but an admitted read-only Query
        with an unknown transport outcome cannot make progress in its frozen
        PlanGraph.  Projecting that node to ``awaiting_replan`` gives the Agent
        a legal recovery choice without retrying or authorizing motion.
        """
        task = self.store.get(task_id)
        revision = task.active_revision
        record = next(
            (item for item in revision.execution_records if item.record_id == record_id),
            None,
        )
        if (
            record is None
            or record.node_id is None
            or record.semantics != "query"
            or not record.terminal
            or revision.plan_graph is None
            or task.status != AgentTaskStatus.EXECUTING
            or _planning_record_status(record) not in {"failed", "unknown"}
            or _replan_count(task) >= self.max_replans
        ):
            return

        def mutate(current: AgentTaskRecord) -> None:
            if current.status != AgentTaskStatus.EXECUTING:
                return
            current.status = AgentTaskStatus.AWAITING_REPLAN
            current.replan_deadline = utc_now() + timedelta(seconds=self.replan_timeout_s)
            current.replan_extension_used = False
            current.evidence_errors.append(
                f"planning Query failure requires recovery: {record.node_id}"
            )

        self.store.update(task_id, mutate, event_type="query_failure_replan_required")

    def _track_remote_identity(
        self,
        task_id: str,
        record_id: str,
        invocation_id: str,
        *,
        tracker: Any | None,
        response: dict[str, Any],
        kind: str,
    ) -> dict[str, Any]:
        """Retain an admitted remote identity even when Runtime-state tracking fails."""
        if tracker is None:
            return response
        try:
            tracker.add(invocation_id)
            return response
        except Exception as exc:
            enriched = dict(response)
            warnings = list(enriched.get("paos_warnings", []))
            warnings.append(
                {
                    "type": "local_tracking",
                    "message": (
                        f"{kind} {invocation_id} was accepted but Runtime tracking failed: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )
            enriched["paos_warnings"] = warnings

            def mutate(current: AgentTaskRecord) -> None:
                record = _task_execution(current, record_id)
                record.response = enriched
                record.updated_at = utc_now()
                current.evidence_errors.append(warnings[-1]["message"])

            self.store.update(
                task_id,
                mutate,
                event_type="runtime_tracking_failed",
                payload={"invocation_id": invocation_id, "kind": kind.lower()},
            )
            return enriched

    async def _capture_before(self, task_id: str) -> None:
        task = self.store.get(task_id)
        writer = ForgeEvidenceWriter(
            self.workspace,
            task_id,
            "agent_task",
            artifact_namespace="agent_tasks",
        )
        collector: ForgeObservationCollector | None = None
        errors: list[str] = []
        reference: str | None = None
        try:
            collector = self._collector(task)
            await collector.start()
            snapshot = await collector.wait_for_before(self.config.evidence.capture_timeout_s)
            reference = writer.write_snapshot("before", snapshot)
        except Exception as exc:
            errors.append(str(exc) or type(exc).__name__)
        finally:
            if collector is not None:
                errors.extend(collector.errors)
                await collector.close()

        def mutate(current: AgentTaskRecord) -> None:
            current.before_snapshot_ref = reference
            current.evidence_errors.extend(errors)

        self.store.update(task_id, mutate, event_type="before_evidence_captured")

    async def _capture_after(self, task_id: str) -> None:
        task = self.store.get(task_id)
        writer = ForgeEvidenceWriter(
            self.workspace,
            task_id,
            "agent_task",
            artifact_namespace="agent_tasks",
        )
        collector: ForgeObservationCollector | None = None
        errors: list[str] = []
        after_ref: str | None = None
        terminal_observed_at = max(
            (item.updated_at for item in task.execution_records), default=utc_now()
        )
        try:
            collector = self._collector(task)
            await collector.start()
            if task.before_snapshot_ref:
                before = writer.load_snapshot(task.before_snapshot_ref)
                after = await collector.wait_for_after(
                    before,
                    terminal_observed_at=terminal_observed_at,
                    timeout_s=self.config.evidence.post_capture_timeout_s,
                )
            else:
                after = await collector.wait_for_before(
                    self.config.evidence.post_capture_timeout_s
                )
            after_ref = writer.write_snapshot("after", after)
        except Exception as exc:
            errors.append(str(exc) or type(exc).__name__)
        finally:
            if collector is not None:
                errors.extend(collector.errors)
                await collector.close()
        bundle, bundle_ref = writer.write_bundle(
            before_ref=task.before_snapshot_ref,
            after_ref=after_ref,
            terminal_observed_at=terminal_observed_at,
            required_sources=list(self.config.evidence.required_image_sources),
            required_kinds=list(task.verification.evidence_policy.required_kinds),
            errors=list(task.evidence_errors) + errors,
        )

        def mutate(current: AgentTaskRecord) -> None:
            current.after_snapshot_ref = after_ref
            current.evidence_bundle_ref = bundle_ref
            current.evidence_bundle_id = bundle.bundle_id
            current.evidence_errors.extend(errors)

        self.store.update(
            task_id,
            mutate,
            event_type="after_evidence_captured",
            payload={"bundle_id": bundle.bundle_id},
        )

    def _collector(self, task: AgentTaskRecord) -> ForgeObservationCollector:
        gateway_url = (
            task.primary_skill_binding.gateway_url
            if task.primary_skill_binding is not None
            else task.runtime_binding.gateway_url
            if task.runtime_binding is not None
            else getattr(self.client, "base_url", None)
        )
        if not isinstance(gateway_url, str) or not gateway_url:
            raise AgentTaskError(
                "Forge evidence collection requires the bound Runtime Gateway URL"
            )
        return ForgeObservationCollector(
            gateway_url,
            required_image_sources=list(self.config.evidence.required_image_sources),
            max_artifact_bytes=self.config.evidence.max_artifact_bytes,
            require_state="robot_state" in task.verification.evidence_policy.required_kinds,
            connection_timeout_s=self.config.evidence.connection_timeout_s,
        )

    def _schedule_experience(self, task: AgentTaskRecord) -> None:
        if (
            task.terminal
            and (task.primary_skill_binding is not None or task.runtime_binding is not None)
            and self.runtime_task_binding_ids is not None
            and not any(
                item.semantics in {"action", "session"} and item.status == "unknown"
                for item in task.execution_records
            )
        ):
            binding_id = (
                task.primary_skill_binding.binding_id
                if task.primary_skill_binding is not None
                else task.runtime_binding.binding_id
            )
            self.runtime_task_binding_ids.discard(binding_id)
        if self.experience is not None:
            self.experience.schedule_forge_completion(task.task_id)


def _task_execution(task: AgentTaskRecord, record_id: str) -> ToolExecutionRecord:
    for record in task.execution_records:
        if record.record_id == record_id:
            return record
    raise AgentTaskError(f"Tool execution record not found: {record_id}")


def _validate_plan_graph_input(
    graph: PlanGraph | None,
    graph_ref: str | None,
    task_id: str,
    revision_id: str,
) -> None:
    if graph is None:
        if graph_ref is not None:
            raise AgentTaskError("plan_graph_ref requires a concrete PlanGraph")
        return
    if graph_ref is None or not graph_ref.startswith("artifact://"):
        raise AgentTaskError("a PlanGraph requires an artifact:// plan_graph_ref")
    if graph.task_id != task_id or graph.revision_id != revision_id:
        raise AgentTaskError("PlanGraph task/revision identity does not match the revision")
    try:
        validate_graph(graph)
        for node in graph.nodes:
            validate_condition_keys(node.conditions)
    except ValueError as exc:
        raise AgentTaskError(f"PlanGraph is not a valid DAG: {exc}") from exc


def _normalize_planning_binding(
    value: PlanningExecutionBinding | dict[str, Any] | None,
) -> PlanningExecutionBinding | None:
    if value is None:
        return None
    try:
        return (
            value
            if isinstance(value, PlanningExecutionBinding)
            else PlanningExecutionBinding.model_validate(value)
        )
    except Exception as exc:
        raise AgentTaskError(f"invalid planning execution binding: {exc}") from exc


def _validate_planning_execution_selection(
    revision: PlanRevision,
    binding: PlanningExecutionBinding,
    *,
    tool_id: str,
    semantics: Literal["query", "action", "session"],
    arguments: dict[str, Any],
) -> None:
    """Match an execution to the durable Agent selection when one exists."""
    if binding.revision_id is not None and binding.revision_id != revision.revision_id:
        raise AgentTaskError("planning execution binding targets a stale revision")
    active_selections = {
        item.resumable_selection.planning_binding.decision_trace_ref: item
        for item in revision.planning_selections
        if item.resumable_selection is not None
    }
    if not active_selections:
        if binding.revision_id is not None:
            raise AgentTaskError(
                "revision-bound planning execution has no active persisted selection"
            )
        return
    if binding.input_binding_digest != tool_input_binding_digest(arguments):
        raise AgentTaskError("planning execution arguments do not match their binding")
    selected = active_selections.get(binding.decision_trace_ref)
    selection = selected.resumable_selection if selected is not None else None
    if (
        selected is None
        or selected.node_id != binding.node_id
        or selection is None
        or selection.planning_binding != binding
        or selection.tool_id != tool_id
        or selection.semantics != semantics
        or selection.tool_arguments != arguments
    ):
        raise AgentTaskError(
            "planning execution does not match the active revision selection"
        )


def _owned_execution(
    task: AgentTaskRecord,
    invocation_id: str,
    *,
    semantics: Literal["action", "session"],
) -> ToolExecutionRecord:
    for record in task.execution_records:
        if record.invocation_id == invocation_id and record.semantics == semantics:
            return record
    raise AgentTaskError(
        f"{semantics.title()} invocation {invocation_id!r} does not belong to AgentTask "
        f"{task.task_id!r}"
    )


def _cancel_terminal_status(task: AgentTaskRecord) -> AgentTaskStatus:
    owned = [
        item
        for item in task.execution_records
        if item.semantics == "action"
        or (item.semantics == "session" and item.ownership == "task")
    ]
    if not owned or all(item.status in {"cancelled", "stopped"} for item in owned):
        return AgentTaskStatus.CANCELLED
    return AgentTaskStatus.FAILED


def has_unsettled_owned_execution(task: AgentTaskRecord) -> bool:
    """Return whether cancellation still needs the owning Runtime.

    Query records and terminal Action/Session records are durable facts that
    can be settled by the Coordinator alone. Only a non-terminal task-owned
    Action or Session may still require a Runtime-side stop/cancel request.
    """
    return any(
        (
            item.semantics == "action"
            or (item.semantics == "session" and item.ownership == "task")
        )
        and not item.terminal
        for item in task.execution_records
    )


def _execution_facts_succeeded(task: AgentTaskRecord) -> bool:
    return all(
        item.status == "succeeded"
        or (
            item.semantics == "session"
            and (
                (item.ownership == "task" and item.status == "stopped")
                or (
                    item.ownership in {"runtime", "shared"}
                    and item.status in {"accepted", "running", "succeeded", "stopped"}
                )
            )
        )
        for item in task.execution_records
    )


def _remote_identity(exc: Exception) -> tuple[str | None, str | None]:
    payload = getattr(exc, "payload", None)
    data = _response_data(payload) if isinstance(payload, dict) else {}
    invocation_id = data.get("invocation_id")
    attempt_id = data.get("attempt_id")
    return (
        invocation_id if isinstance(invocation_id, str) and invocation_id else None,
        attempt_id if isinstance(attempt_id, str) and attempt_id else None,
    )


def _fail_replan(task: AgentTaskRecord, message: str) -> None:
    task.status = AgentTaskStatus.FAILED
    task.evidence_errors.append(message)


def _replan_count(task: AgentTaskRecord) -> int:
    """Count recovery revisions while excluding discovery expansion.

    Existing records default every revision to ``True``; subtracting the
    initial revision preserves their historical ``len(revisions) - 1`` budget
    semantics. New discovery revisions explicitly opt out.
    """
    return max(
        0,
        sum(revision.counts_toward_replan_budget for revision in task.revisions) - 1,
    )


def _response_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    return data if isinstance(data, dict) else response


def _planning_response_facts(response: dict[str, Any] | None) -> dict[str, Any]:
    """Project persisted Gateway data into settlement facts without provider coupling."""
    if not isinstance(response, dict):
        return {}
    payload = response.get("data")
    payload = payload if isinstance(payload, dict) else response
    result = payload.get("result")
    if isinstance(result, dict):
        payload = {**payload, **result}
    summary = payload.get("capability_outcome_summary")
    if isinstance(summary, dict):
        payload = {**payload, **summary}
    return payload


def _planning_record_status(record: ToolExecutionRecord) -> str:
    """Normalize provider-level Query status before NodeSettlement."""
    if record.semantics != "query" or record.status != "succeeded":
        return record.status
    status = _planning_response_facts(record.response).get("status")
    if status in {"unavailable", "invalid", "stale", "empty", "failed"}:
        return "failed"
    if status == "unknown":
        return "unknown"
    return record.status


def _string_refs(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _task_scene_revision(
    task: AgentTaskRecord,
    *,
    exclude_record_id: str | None = None,
) -> str | None:
    """Read the latest scene identity emitted by a persisted Tool response."""
    scene_revision: str | None = None
    for record in task.active_revision.execution_records:
        if record.record_id == exclude_record_id:
            continue
        facts = _planning_response_facts(record.response)
        for key in ("scene_revision", "new_scene_revision"):
            value = facts.get(key)
            if isinstance(value, str) and value.strip():
                scene_revision = value.strip()
    return scene_revision


def _tool_result_from_execution(
    task: AgentTaskRecord,
    record: ToolExecutionRecord,
) -> ToolResultEnvelope | None:
    """Build the pure planning result projection from one terminal record."""
    if record.node_id is None:
        return None
    facts = _planning_response_facts(record.response)
    status = _planning_record_status(record)
    scene_write_behavior = _planning_scene_write_behavior(task, record.tool_id)
    evidence_refs = list(record.evidence_refs)
    for key in ("evidence_refs", "artifact_refs"):
        evidence_refs.extend(_string_refs(facts.get(key)))
    output_refs = _string_refs(facts.get("output_refs"))
    explicit_world_changed = facts.get("world_changed") is True
    started_facts = [facts.get("world_change_started")]
    known_facts = [facts.get("outcome_known")]
    world_change_started: bool | None
    outcome_known: bool | None
    if explicit_world_changed or any(value is True for value in started_facts):
        world_change_started = True
    elif all(value is False for value in started_facts) or record.semantics == "query":
        world_change_started = False
    else:
        world_change_started = None
    if any(value is False for value in known_facts):
        outcome_known = False
    elif all(value is True for value in known_facts) or record.semantics == "query":
        outcome_known = True
    else:
        outcome_known = None
    new_scene_revision = facts.get("new_scene_revision")
    if not isinstance(new_scene_revision, str) or not new_scene_revision.strip():
        new_scene_revision = None
    world_changed = explicit_world_changed or (
        scene_write_behavior == "new_revision"
        and status == "succeeded"
        and world_change_started is True
        and outcome_known is True
        and new_scene_revision is not None
    )
    failure_code: str | None = None
    failure_owner: str | None = None
    if isinstance(record.error, dict):
        value = record.error.get("code") or record.error.get("type")
        failure_code = value if isinstance(value, str) else None
        owner = record.error.get("owner")
        failure_owner = owner if isinstance(owner, str) else None
    if failure_code is None and isinstance(facts.get("failure_code"), str):
        failure_code = facts["failure_code"]
        owner = facts.get("failure_owner")
        failure_owner = owner if isinstance(owner, str) else failure_owner
    if failure_code is None and isinstance(facts.get("error"), dict):
        code = facts["error"].get("code")
        failure_code = code if isinstance(code, str) else None
    if failure_code is None and status != "succeeded":
        failure_code = status
    return ToolResultEnvelope(
        task_id=task.task_id,
        revision_id=record.revision_id,
        node_id=record.node_id,
        tool_id=record.tool_id,
        status=status,
        scene_write_behavior=scene_write_behavior,
        world_changed=world_changed,
        world_change_started=world_change_started,
        outcome_known=outcome_known,
        output_refs=tuple(dict.fromkeys(output_refs)),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        new_scene_revision=new_scene_revision,
        failure_code=failure_code,
        failure_owner=failure_owner,
    )


def _planning_scene_write_behavior(
    task: AgentTaskRecord,
    tool_id: str,
) -> Literal["none", "new_revision", "unknown"]:
    binding = task.primary_skill_binding
    tools = binding.required_tools if binding is not None else tuple(task.tool_bindings)
    tool = next((item for item in tools if item.tool_id == tool_id), None)
    policy = tool.planning_policy if tool is not None else None
    return policy.scene_write_behavior if policy is not None else "unknown"


def _tool_status(response: dict[str, Any], *, default: str) -> str:
    data = _response_data(response)
    phase = data.get("phase") or data.get("state") or data.get("status")
    if isinstance(phase, str):
        normalized = phase.lower()
        mapping = {
            "dispatching": "pending",
            "pending": "pending",
            "accepted": "accepted",
            "running": "running",
            "stopping": "running",
            "completed": "succeeded",
            "succeeded": "succeeded",
            "failed": "failed",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "stopped": "stopped",
            "unknown": "unknown",
        }
        if normalized in mapping:
            return mapping[normalized]
    result = data.get("result")
    if data.get("status") == "available" and isinstance(result, dict):
        result_status = result.get("status")
        if isinstance(result_status, str):
            return _tool_status({"phase": result_status}, default=default)
    return default


__all__ = [
    "AgentTaskBusyError",
    "AgentTaskCoordinator",
    "AgentTaskError",
    "AgentTaskRecord",
    "AgentTaskStatus",
    "AgentTaskStore",
    "PlanRevision",
    "TERMINAL_TASK_STATUSES",
    "ToolExecutionRecord",
]
