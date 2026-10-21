"""Wire the pick-place Skill to persistent providers through normal Tool endpoints."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping, Protocol

from PhyAgentOS.forge.capability_runtime import (
    CAPABILITY_TOOL_SPEC,
    GRASP_PROPOSAL_TOOL_SPEC,
    MANIPULATION_TOOL_SPEC,
    OBSERVATION_TOOL_SPEC,
    SCENE_UNDERSTANDING_TOOL_SPEC,
    ActionAdmission,
    CapabilityRuntime,
    CapabilitySnapshotEndpoint,
    GraspProposalEndpoint,
    ManipulationPreparationEndpoint,
    ObservationEndpoint,
    SceneUnderstandingEndpoint,
)

from .object_acquire import ACQUIRE_TOOL_SPEC
from .object_acquire import validate_arguments as validate_acquire
from .object_place import PLACE_TOOL_SPEC
from .object_place import validate_arguments as validate_place


@dataclass
class PersistentPossession:
    """Adapter-owned possession facts shared by acquire/place endpoints."""

    state: str = "empty"
    owner: str | None = None
    entity_ref: str | None = None
    acquire_invocation_ref: str | None = None
    cycle_invocation_ref: str | None = None
    last_invocation_ref: str | None = None
    scene_revision: str | None = None

    def validate_begin(self, phase: str, *, owner: str, entity_ref: str, acquire_ref: str | None = None,
                       cycle_ref: str | None = None) -> None:
        if phase in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            if self.state != "empty":
                raise ValueError(f"possession is {self.state}; {phase} requires empty hand")
            return
        if phase == "acquire" and self.state in {"holding", "placing", "operating", "uncertain"}:
            raise ValueError(f"possession is {self.state}; acquire is not admissible")
        if phase in {"place", "pour", "stir"}:
            if self.state != "holding":
                raise ValueError(f"possession is {self.state}; {phase} requires holding")
            if self.owner != owner or self.entity_ref != entity_ref or self.acquire_invocation_ref != acquire_ref:
                raise ValueError(f"{phase} does not match the held entity owner and acquisition")
            if self.cycle_invocation_ref != cycle_ref:
                raise ValueError(f"{phase} does not match the held cycle source")
            if phase in {"pour", "stir"} and cycle_ref is not None:
                raise ValueError("cycle-sourced possession can only be recovered with place")

    def begin(self, phase: str, *, owner: str, entity_ref: str, acquire_ref: str | None = None,
              cycle_ref: str | None = None) -> None:
        self.validate_begin(phase, owner=owner, entity_ref=entity_ref, acquire_ref=acquire_ref, cycle_ref=cycle_ref)
        if phase == "acquire":
            self.state, self.owner, self.entity_ref = "acquiring", owner, entity_ref
            self.acquire_invocation_ref = acquire_ref
            self.cycle_invocation_ref = None
            self.last_invocation_ref = acquire_ref
            self.scene_revision = None
            return
        if phase in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            self.state, self.owner, self.entity_ref = "acquiring", owner, entity_ref
            self.acquire_invocation_ref = None
            self.cycle_invocation_ref = None
            self.last_invocation_ref = None
            self.scene_revision = None
            return
        if phase == "place":
            self.state = "placing"
            return
        if phase in {"pour", "stir"}:
            self.state = "operating"
            return
        raise ValueError(f"unsupported possession phase: {phase}")

    def settle(self, phase: str, result: Mapping[str, Any]) -> None:
        status = result.get("status")
        known = result.get("outcome_known") is True
        changed = result.get("world_change_started") is True
        explicit_possession = result.get("possession_state")
        if phase in {"pour", "stir", "pour_cycle", "stir_cycle", "manipulation_cycle"} and known and status in {"succeeded", "failed", "cancelled", "stopped"} and explicit_possession in {"empty", "holding"}:
            self.state = explicit_possession
            if self.state == "empty":
                self.owner = self.entity_ref = self.acquire_invocation_ref = None
                self.cycle_invocation_ref = None
            return
        if known and status in {"succeeded", "failed"} and explicit_possession == "empty":
            self.state = "empty"
            self.owner = self.entity_ref = self.acquire_invocation_ref = None
            self.cycle_invocation_ref = None
            return
        if known and status in {"succeeded", "failed"} and explicit_possession == "holding":
            self.state = "holding"
            return
        if phase == "acquire":
            if status == "succeeded" and known:
                self.state = "holding"
            elif status in {"failed", "cancelled", "stopped"} and known and not changed:
                self.state = "empty"
            else:
                self.state = "uncertain"
        elif phase == "place":
            if status == "succeeded" and known:
                self.state = "empty"
                self.owner = self.entity_ref = self.acquire_invocation_ref = None
            elif status in {"failed", "cancelled", "stopped"} and known and not changed:
                self.state = "holding"
            else:
                self.state = "uncertain"
        elif phase in {"pour", "stir", "pour_cycle", "stir_cycle", "manipulation_cycle"}:
            # An operation never acquires or releases implicitly. Only explicit
            # measured possession, or a confirmed no-effect interruption, can hold.
            self.state = "holding" if known and not changed and status in {"failed", "cancelled", "stopped"} else "uncertain"

    def reconcile(self, snapshot: Mapping[str, Any]) -> str:
        """Reconcile after restart from explicit adapter-owned physical facts."""
        if not isinstance(snapshot, Mapping) or snapshot.get("available") is not True:
            self.state = "uncertain"
            return self.state
        holding = snapshot.get("holding_state")
        if holding == "empty":
            self.state = "empty"
            self.owner = self.entity_ref = self.acquire_invocation_ref = None
            self.cycle_invocation_ref = None
            return self.state
        if holding != "holding":
            self.state = "uncertain"
            return self.state
        source_ref = self.acquire_invocation_ref or self.cycle_invocation_ref
        if any(value is None for value in (self.owner, self.entity_ref, source_ref)):
            self.state = "uncertain"
            return self.state
        if any(snapshot.get(key) != value for key, value in (
            ("owner", self.owner),
            ("entity_ref", self.entity_ref),
            ("acquire_invocation_ref", self.acquire_invocation_ref),
            ("cycle_invocation_ref", self.cycle_invocation_ref),
        )):
            self.state = "uncertain"
            return self.state
        if self.last_invocation_ref is not None and self.last_invocation_ref != self.acquire_invocation_ref:
            if (snapshot.get("held_invocation_ref") != self.last_invocation_ref
                    or not isinstance(snapshot.get("scene_revision"), str)
                    or not snapshot["scene_revision"]):
                self.state = "uncertain"
                return self.state
            self.scene_revision = snapshot["scene_revision"]
        self.state = "holding"
        return self.state


class _ProjectedDriver:
    def __init__(self, driver, phase, arguments, possession: PersistentPossession | None = None, *, invocation_id: str = "invocation://object-acquire/unknown", current_scene_revision: str | None = None):
        self.driver, self.phase, self.arguments = driver, phase, arguments
        self.possession, self.invocation_id = possession or PersistentPossession(), invocation_id
        self.current_scene_revision = (
            current_scene_revision
            if current_scene_revision is not None
            else arguments.get("scene_revision") if phase == "place" else None
        )

    def poll(self):
        raw = self.driver.poll()
        if raw is None:
            return None
        status = raw["status"]
        if status == "succeeded" and raw.get("outcome_known") is not True:
            status = "unknown"
        success = status == "succeeded"
        refs = list(raw.get("artifact_refs", ()))
        outcome_known = raw.get("outcome_known", False)
        missing_evidence = success and not refs
        missing_acquire_effect = (
            self.phase == "acquire"
            and success
            and raw.get("world_change_started") is True
            and outcome_known is True
            and (
                not isinstance(raw.get("new_scene_revision"), str)
                or not raw["new_scene_revision"].strip()
            )
        )
        missing_place_postconditions = False
        if self.phase == "place" and success:
            missing_place_postconditions = not all(
                raw.get(name) is True
                for name in (
                    "release_confirmed",
                    "retreat_completed",
                    "clear_of_target",
                    "observation_ready",
                )
            ) or not isinstance(raw.get("new_scene_revision"), str)
        if missing_evidence or missing_acquire_effect or missing_place_postconditions:
            status, success = "unknown", False
            outcome_known = False
        self.possession.settle(
            self.phase,
            {**raw, "status": status, "outcome_known": outcome_known},
        )
        self.possession.last_invocation_ref = self.invocation_id
        self.possession.scene_revision = raw.get("new_scene_revision") if outcome_known else None
        arm_attempts = []
        for attempt in raw.get("arm_attempts", []):
            if not isinstance(attempt, Mapping):
                continue
            projected = {
                key: deepcopy(attempt[key])
                for key in (
                    "arm",
                    "status",
                    "failed_phase",
                    "failed_waypoint_index",
                    "detail",
                )
                if key in attempt
            }
            if "arm" in projected and "status" in projected:
                arm_attempts.append(projected)
        summary = {
            "version": "capability_outcome_summary_v1",
            "capability_phase": ("hold" if self.phase == "acquire" else "retreat") if success else "none",
            "status": status,
            "failure_owner": (
                "execution"
                if missing_evidence or missing_acquire_effect or missing_place_postconditions
                else raw.get("failure_owner")
            ),
            "failure_code": (
                "missing_execution_evidence"
                if missing_evidence
                else "missing_new_scene_revision"
                if missing_acquire_effect
                else "missing_place_postconditions"
                if missing_place_postconditions
                else raw.get("failure_code")
            ),
            "world_change_started": raw.get("world_change_started"),
            "outcome_known": outcome_known,
            "evidence_availability": "complete" if success and refs else "partial" if refs else "none",
            "artifact_refs": refs, "bounded_metric_names": [],
            "retryable_in_revision": raw.get("retryable_in_revision", False),
            "requires_replan": raw.get("requires_replan", False),
            "recommended_action": raw.get("recommended_action", "continue" if success else "stop"),
            "phase": raw.get("phase", self.phase),
            "selected_arm": raw.get("selected_arm"),
            "failed_phase": raw.get("failed_phase"),
            "arm_attempts": arm_attempts,
            "evidence_refs": list(raw.get("evidence_refs", refs)),
        }
        for key in ("possession_state", "object_support_state", "acquisition_measurement"):
            if key in raw:
                summary[key] = deepcopy(raw[key])
        if self.phase == "place":
            summary["post_release_evidence"] = {"availability": "complete" if success and refs else "none", "artifact_refs": refs if success else []}
            summary.update(
                release_confirmed=raw.get("release_confirmed") is True,
                retreat_completed=raw.get("retreat_completed") is True,
                clear_of_target=raw.get("clear_of_target") is True,
                observation_ready=raw.get("observation_ready") is True,
                new_scene_revision=raw.get("new_scene_revision"),
            )
        result = {key: value for key, value in self.arguments.items() if key not in {"freshness_ms", "max_age_ms", "frame_id"}}
        if self.phase == "place" and self.current_scene_revision is not None:
            result["current_scene_revision"] = self.current_scene_revision
        result.update(status=status, frame={"frame_id": self.arguments["frame_id"], "unit": "m"}, capability_outcome_summary=summary)
        if self.phase == "place":
            result.update(
                release_confirmed=raw.get("release_confirmed") is True,
                retreat_completed=raw.get("retreat_completed") is True,
                clear_of_target=raw.get("clear_of_target") is True,
                observation_ready=raw.get("observation_ready") is True,
                new_scene_revision=raw.get("new_scene_revision"),
            )
        if raw.get("new_scene_revision"):
            result["new_scene_revision"] = raw["new_scene_revision"]
        if isinstance(raw.get("scene_effects"), Mapping):
            result["scene_effects"] = deepcopy(dict(raw["scene_effects"]))
        result["evidence_refs"] = refs + ([f"placed:{self.arguments['entity_ref']}"] if success and self.phase == "place" else [])
        result["held_invocation_ref"] = self.invocation_id
        return result

    def cancel(self):
        self.driver.cancel()

    def stop(self):
        self.driver.stop()


def _spec(spec, *, argument_defaults=None, require_synchronized_views: bool = False):
    spec = deepcopy(spec)
    if spec["tool_id"] == "scene.observe" and require_synchronized_views:
        input_schema = spec["input_schema"]
        properties = input_schema["properties"]
        properties.pop("sensor_ref", None)
        properties["sensor_refs"]["minItems"] = 2
        input_schema["oneOf"] = [{"required": ["sensor_refs"]}]
    if argument_defaults:
        properties = spec.get("input_schema", {}).get("properties", {})
        if not isinstance(properties, dict) or set(argument_defaults) - set(properties):
            raise ValueError("Tool argument defaults must name declared input fields")
        for name, value in argument_defaults.items():
            properties[name]["default"] = deepcopy(value)
    action = spec["semantics"] == "action"
    planning = deepcopy(spec.get("planning", {}))
    planning.update({"schema_version": "paos-tool-spec-policy/v1",
                     "capabilities": [spec["tool_id"]],
                     "refreshes_scene": spec["tool_id"] == "scene.observe",
                     "input_binding_keys": ["entity_ref", "destination_ref"] if spec["tool_id"] == "object.place" else ["entity_ref"] if action else [],
                     "scene_write_behavior": "new_revision" if action else "none"})
    if spec["tool_id"] == "manipulation.prepare":
        planning["trusted_argument_builder"] = "manipulation_intent_v2"
        spec["default_timeout_ms"] = max(
            int(spec.get("default_timeout_ms") or 0), 360_000
        )
    if spec["tool_id"] == "manipulation.execute_subtask":
        planning["trusted_argument_builder"] = "manipulation_intent_v2"
    if spec["tool_id"] == "grasp.propose":
        planning["argument_projection"] = "entity_geometry_target_v1"
    spec["planning"] = planning
    if spec["tool_id"] == "scene.observe":
        spec["planning"]["capabilities"].append("task.verify")
    if action:
        properties = spec["output_schema"]["properties"]["result"]["properties"]
        properties["held_invocation_ref"] = {"type": "string", "minLength": 1}
        properties["evidence_refs"] = {"type": "array", "items": {"type": "string"}}
        properties["scene_effects"] = {"type": "object"}
        properties["capability_outcome_summary"]["properties"]["world_change_started"] = {"type": ["boolean", "null"]}
        properties["capability_outcome_summary"]["properties"].update(
            {
                "possession_state": {"enum": ["empty", "holding"]},
                "object_support_state": {
                    "enum": ["on_support", "displaced", "unknown"]
                },
                "acquisition_measurement": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "lift_displacement_m": {"type": "number"},
                        "minimum_lift_m": {"type": "number"},
                        "support_clearance_m": {"type": "number"},
                        "support_tolerance_m": {"type": "number"},
                    },
                },
            }
        )
        if spec["tool_id"] == "object.place":
            properties["current_scene_revision"] = {"type": "string", "minLength": 1}
    return spec


class PersistentObservationSource:
    """Adapt a generic observation source without coupling it to an Action client.

    New providers should expose ``capture(request)``.  The ``query`` fallback
    keeps existing hosts compatible while the source is migrated; it is not a
    second observation contract exposed to the Agent or Gateway.
    """

    def __init__(self, source):
        self.source = source

    def capture(self, request):
        capture = getattr(self.source, "capture", None)
        if callable(capture):
            return capture(dict(request))
        query = getattr(self.source, "query", None)
        if callable(query):
            return query("observe", dict(request))
        raise TypeError("observation source must expose capture(request) or query(operation, request)")


class PersistentActionEndpoint:
    """Resolve admitted preparation evidence before starting a provider Action."""

    def __init__(self, phase: str, client, resolve: Callable[[str, Mapping[str, Any]], Mapping[str, Any]], *, possession: PersistentPossession | None = None) -> None:
        self.phase = phase
        self.client = client
        self.resolve = resolve
        self.possession = possession or PersistentPossession()

    def admit(self, arguments):
        raise ValueError("persistent manipulation requires a task-owned caller")

    def admit_for_caller(self, arguments, *, caller_id):
        parts = caller_id.split(":") if isinstance(caller_id, str) else []
        if len(parts) != 4 or parts[0] != "paos" or not all(parts[1:]):
            raise ValueError("persistent Action caller must be bound to a PAOS task record")
        error = (validate_acquire if self.phase == "acquire" else validate_place)(arguments)
        if error:
            raise ValueError(error)
        public = deepcopy(arguments)
        task_resolver = getattr(self.resolve, "resolve_for_task", None)
        raw_resolved = (
            task_resolver(self.phase, public, task_id=parts[1])
            if callable(task_resolver)
            else self.resolve(self.phase, public)
        )
        resolved = deepcopy(dict(raw_resolved))
        keys = ("entity_ref", "candidate_ref", "preparation_ref") + (("destination_ref",) if self.phase == "place" else ())
        for key in keys:
            if resolved.get(key) != public.get(key):
                raise ValueError(f"resolved preparation changed {key}")
        assignment = resolved.get("assignment")
        if not isinstance(assignment, Mapping) or assignment.get("task_id") != parts[1]:
            raise ValueError("prepared assignment does not belong to this task")
        if assignment.get("assignment_ref") != public["assignment_ref"]:
            raise ValueError("prepared assignment reference mismatch")
        resolved["task_id"] = parts[1]
        if self.phase == "place":
            resolved["acquire_invocation_id"] = public["acquire_invocation_ref"]
            current_scene_revision = resolved.get("scene_revision")
            if not isinstance(current_scene_revision, str) or not current_scene_revision.strip():
                raise ValueError("place preparation lacks current scene revision")
        else:
            current_scene_revision = None
        self.possession.validate_begin(
            self.phase,
            owner=f"paos:{parts[1]}",
            entity_ref=public["entity_ref"],
            acquire_ref=public.get("acquire_invocation_ref"),
        )

        def start(invocation_id, attempt_id):
            acquire_ref = public.get("acquire_invocation_ref")
            self.possession.begin(
                self.phase,
                owner=f"paos:{parts[1]}",
                entity_ref=public["entity_ref"],
                acquire_ref=acquire_ref if self.phase == "place" else invocation_id,
            )
            try:
                driver = self.client.start(self.phase, invocation_id, f"paos:{parts[1]}", resolved)
            except Exception:
                self.possession.settle(self.phase, {"status": "failed", "outcome_known": True, "world_change_started": False})
                raise
            return ActionAdmission(driver=_ProjectedDriver(driver, self.phase, public, self.possession, invocation_id=invocation_id, current_scene_revision=current_scene_revision))

        return ActionAdmission(start=start)


class AssignmentArtifactStore(Protocol):
    """Structural interface for durable, reference-addressed route artifacts."""

    def put(self, assignment_ref: str, document: Mapping[str, Any]) -> None:
        """Persist one complete preparation artifact under its canonical reference."""
        ...

    def get(self, assignment_ref: str) -> Mapping[str, Any] | None:
        """Return the persisted artifact document, or ``None`` when absent."""
        ...


class SQLiteAssignmentArtifactStore:
    """Small provider-neutral durable store for preparation route artifacts.

    The store owns only serialization and reference lookup.  It does not derive
    assignments, choose a robot, or interpret environment-specific route data.
    A caller must provide the complete document produced by the preparation
    provider; partial documents are rejected before they reach acquire/place.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = RLock()
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS assignment_artifacts "
            "(assignment_ref TEXT PRIMARY KEY, document_json TEXT NOT NULL)"
        )
        self._connection.commit()

    def put(self, assignment_ref: str, document: Mapping[str, Any]) -> None:
        if not isinstance(assignment_ref, str) or not assignment_ref.startswith("artifact://"):
            raise ValueError("assignment artifact reference must use artifact://")
        if not isinstance(document, Mapping):
            raise TypeError("assignment artifact document must be an object")
        assignment = document.get("assignment")
        route_arguments = document.get("route_arguments")
        preparation_ref = document.get("preparation_ref")
        if not isinstance(assignment, Mapping) or not isinstance(route_arguments, Mapping):
            raise ValueError("assignment artifact requires assignment and route_arguments")
        if assignment.get("assignment_ref") != assignment_ref:
            raise ValueError("assignment artifact reference mismatch")
        if not isinstance(preparation_ref, str) or not preparation_ref.startswith("preparation://"):
            raise ValueError("assignment artifact requires preparation_ref")
        payload = json.dumps(dict(document), ensure_ascii=False, allow_nan=False, sort_keys=True)
        with self._lock:
            try:
                self._connection.execute(
                    "INSERT INTO assignment_artifacts(assignment_ref, document_json) VALUES(?, ?)",
                    (assignment_ref, payload),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                existing = self.get(assignment_ref)
                if existing != json.loads(payload):
                    raise ValueError("assignment reference already stores a different artifact") from exc

    def get(self, assignment_ref: str) -> Mapping[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT document_json FROM assignment_artifacts WHERE assignment_ref = ?",
                (assignment_ref,),
            ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        return deepcopy(value) if isinstance(value, Mapping) else None

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteAssignmentArtifactStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class StoredAssignmentResolver:
    """Resolve complete preparation artifacts without rebuilding routes.

    The store document has three fields: the canonical ``assignment`` object,
    its ``preparation_ref``, and provider-owned ``route_arguments``. The latter
    contains the approved execution route for this artifact. This resolver
    checks PAOS ownership and request identity, then returns those stored route
    arguments unchanged; it never derives a route from labels or environment
    configuration.
    """

    def __init__(self, store: AssignmentArtifactStore) -> None:
        getter = getattr(store, "get", None)
        if not callable(getter):
            raise TypeError("assignment artifact store must expose get(assignment_ref)")
        self.store = store

    def resolve_for_task(
        self, phase: str, request: Mapping[str, Any], *, task_id: str
    ) -> dict[str, Any]:
        if phase not in {"acquire", "place"}:
            raise ValueError("assignment resolution supports acquire or place")
        assignment_ref = request.get("assignment_ref")
        if not isinstance(assignment_ref, str) or not assignment_ref.startswith("artifact://"):
            raise ValueError("assignment lookup requires its canonical artifact reference")
        document = self.store.get(assignment_ref)
        if not isinstance(document, Mapping):
            raise ValueError("prepared assignment artifact was not found")
        assignment = document.get("assignment")
        route_arguments = document.get("route_arguments")
        if not isinstance(assignment, Mapping) or not isinstance(route_arguments, Mapping):
            raise ValueError("prepared assignment artifact is incomplete")
        if assignment.get("assignment_ref") != assignment_ref:
            raise ValueError("stored assignment reference does not match lookup key")
        if assignment.get("task_id") != task_id:
            raise ValueError("stored assignment belongs to another task")
        if document.get("preparation_ref") != request.get("preparation_ref"):
            raise ValueError("stored assignment preparation reference mismatch")
        for key in ("entity_ref", "candidate_ref"):
            if assignment.get(key) != request.get(key):
                raise ValueError(f"stored assignment {key} mismatch")
        if (
            assignment.get("scene_revision") is not None
            and route_arguments.get("scene_revision") != assignment.get("scene_revision")
        ):
            raise ValueError("stored route assignment scene_revision mismatch")
        if phase == "place" and route_arguments.get("destination_ref") != request.get("destination_ref"):
            raise ValueError("stored assignment destination mismatch")
        for key in ("entity_ref", "candidate_ref", "preparation_ref"):
            if route_arguments.get(key) != request.get(key):
                raise ValueError(f"stored route {key} mismatch")
        if phase == "acquire" and route_arguments.get("scene_revision") != request.get("scene_revision"):
            raise ValueError("stored route scene_revision mismatch")
        resolved = deepcopy(dict(route_arguments))
        if phase == "place":
            resolved["scene_revision"] = request.get("scene_revision")
        resolved["assignment"] = deepcopy(dict(assignment))
        return resolved


def register_subtask_tool(
    runtime: CapabilityRuntime,
    refresh_binding,
    tool_context_provider,
    resolve_subtask_context,
    assignment_store: AssignmentArtifactStore | None = None,
) -> None:
    """Register the Agent-facing subtask boundary after Runtime composition.

    The late registration point lets a host bind a provider-neutral perception
    adapter to this concrete Runtime without making the adapter environment
    aware or exposing intermediate Tool nodes to AgentLoop.
    """
    if not callable(refresh_binding):
        raise ValueError("refresh_binding must be callable")
    if not callable(resolve_subtask_context):
        raise ValueError("resolve_subtask_context must be callable")
    from .subtask_executor import SUBTASK_TOOL_SPEC, SubtaskActionEndpoint

    runtime.register_tool(
        deepcopy(SUBTASK_TOOL_SPEC),
        SubtaskActionEndpoint(runtime, refresh_binding, resolve_subtask_context, assignment_store=assignment_store),
        context_provider=lambda: tool_context_provider("manipulation.execute_subtask"),
    )


def build_persistent_runtime(*, client, understanding_provider, grasp_provider,
                             preparation_provider, capability_provider, resolve_preparation=None,
                             tool_context_provider, possession: PersistentPossession | None = None,
                             observation_source=None,
                             query_decorator=None, tool_input_defaults=None,
                             require_synchronized_views: bool = False,
                             held_preparation_provider=None, resolve_held_preparation=None,
                             register_legacy_actions: bool = True,
                             register_legacy_held_operations: bool = True,
                             refresh_subtask_binding=None, resolve_subtask_context=None,
                             assignment_store: AssignmentArtifactStore | None = None) -> CapabilityRuntime:
    """Use injected model providers and one persistent manipulation process.

    resolve_preparation belongs to the adapter and supplies the approved route
    and current admission scene from its preparation artifacts. Public Action
    arguments keep the original candidate/acquire provenance intact.
    tool_context_provider(tool_id) reports host-owned endpoint readiness, not
    whether a specific candidate or Action is admissible in the current world.
    """
    runtime = CapabilityRuntime()
    if assignment_store is not None:
        resolve_preparation = StoredAssignmentResolver(assignment_store)
    if resolve_preparation is None:
        raise ValueError("resolve_preparation or assignment_store is required")
    possession = possession or PersistentPossession()
    if (held_preparation_provider is None) != (resolve_held_preparation is None):
        raise ValueError("held preparation provider and resolver must be supplied together")
    registrations = [
        (OBSERVATION_TOOL_SPEC, ObservationEndpoint(PersistentObservationSource(
            observation_source if observation_source is not None else client
        ))),
        (SCENE_UNDERSTANDING_TOOL_SPEC, SceneUnderstandingEndpoint(understanding_provider)),
        (GRASP_PROPOSAL_TOOL_SPEC, GraspProposalEndpoint(grasp_provider)),
        (CAPABILITY_TOOL_SPEC, CapabilitySnapshotEndpoint(capability_provider)),
        (MANIPULATION_TOOL_SPEC, ManipulationPreparationEndpoint(preparation_provider)),
    ]
    if register_legacy_actions:
        registrations.extend([
            (ACQUIRE_TOOL_SPEC, PersistentActionEndpoint("acquire", client, resolve_preparation, possession=possession)),
            (PLACE_TOOL_SPEC, PersistentActionEndpoint("place", client, resolve_preparation, possession=possession)),
        ])
    for spec, endpoint in registrations:
        defaults = (tool_input_defaults or {}).get(spec["tool_id"])
        if query_decorator is not None and spec["semantics"] == "query":
            endpoint = query_decorator(spec["tool_id"], endpoint)
        live_spec = _spec(
                spec,
                argument_defaults=defaults,
                require_synchronized_views=require_synchronized_views,
            )
        if register_legacy_held_operations and spec["tool_id"] == "object.place":
            from .held_manipulation import HeldActionEndpoint, extended_place_spec

            live_spec = extended_place_spec(live_spec)
            endpoint = HeldActionEndpoint("place", client, resolve_held_preparation, possession, legacy_place=endpoint)
        runtime.register_tool(
            live_spec,
            endpoint,
            context_provider=lambda tool_id=spec["tool_id"]: tool_context_provider(tool_id),
        )
    if held_preparation_provider is not None:
        from .held_manipulation import (
            MANIPULATION_CYCLE_TOOL_SPEC,
            POUR_CYCLE_TOOL_SPEC,
            POUR_TOOL_SPEC,
            PREPARE_CYCLE_TOOL_SPEC,
            PREPARE_HELD_TOOL_SPEC,
            STIR_CYCLE_TOOL_SPEC,
            STIR_TOOL_SPEC,
            CycleActionEndpoint,
            CyclePreparationEndpoint,
            HeldActionEndpoint,
            HeldPreparationEndpoint,
            cycle_capability_available,
            extended_held_preparation_spec,
        )

        if register_legacy_held_operations:
            for spec, endpoint in (
                (PREPARE_HELD_TOOL_SPEC, HeldPreparationEndpoint(held_preparation_provider, possession)),
                (POUR_TOOL_SPEC, HeldActionEndpoint("pour", client, resolve_held_preparation, possession)),
                (STIR_TOOL_SPEC, HeldActionEndpoint("stir", client, resolve_held_preparation, possession)),
            ):
                if spec["tool_id"] == "manipulation.prepare_held":
                    spec = extended_held_preparation_spec(spec)
                if query_decorator is not None and spec["semantics"] == "query":
                    endpoint = query_decorator(spec["tool_id"], endpoint)
                runtime.register_tool(deepcopy(spec), endpoint,
                                      context_provider=lambda tool_id=spec["tool_id"]: tool_context_provider(tool_id))
        cycle_specs = (
            ("pour_cycle", POUR_CYCLE_TOOL_SPEC,
             CycleActionEndpoint("pour_cycle", client, resolve_held_preparation, possession,
                                preflight=held_preparation_provider)),
            ("stir_cycle", STIR_CYCLE_TOOL_SPEC,
             CycleActionEndpoint("stir_cycle", client, resolve_held_preparation, possession,
                                preflight=held_preparation_provider)),
            ("manipulation_cycle", MANIPULATION_CYCLE_TOOL_SPEC,
             CycleActionEndpoint("manipulation_cycle", client, resolve_held_preparation, possession,
                                preflight=held_preparation_provider)),
        )
        available_cycles = [entry for entry in cycle_specs
                            if (cycle_capability_available(held_preparation_provider, entry[0])
                                and cycle_capability_available(client, entry[0]))]
        if available_cycles:
            cycle_preparation = CyclePreparationEndpoint(held_preparation_provider, possession)
            if query_decorator is not None:
                cycle_preparation = query_decorator("manipulation.prepare_cycle", cycle_preparation)
            runtime.register_tool(deepcopy(PREPARE_CYCLE_TOOL_SPEC),
                                  cycle_preparation,
                                  context_provider=lambda: tool_context_provider("manipulation.prepare_cycle"))
        for _, spec, endpoint in available_cycles:
            runtime.register_tool(deepcopy(spec), endpoint,
                                  context_provider=lambda tool_id=spec["tool_id"]: tool_context_provider(tool_id))
    if refresh_subtask_binding is not None and resolve_subtask_context is not None:
        register_subtask_tool(
            runtime,
            refresh_subtask_binding,
            tool_context_provider,
            resolve_subtask_context,
            assignment_store,
        )
    return runtime
