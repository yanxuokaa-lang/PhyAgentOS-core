"""Wire the pick-place Skill to persistent providers through normal Tool endpoints."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

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


class _ProjectedDriver:
    def __init__(self, driver, phase, arguments):
        self.driver, self.phase, self.arguments = driver, phase, arguments

    def poll(self):
        raw = self.driver.poll()
        if raw is None:
            return None
        status = raw["status"]
        if status == "succeeded" and raw.get("outcome_known") is not True:
            status = "unknown"
        success = status == "succeeded"
        refs = list(raw.get("artifact_refs", ()))
        summary = {
            "version": "capability_outcome_summary_v1",
            "capability_phase": ("hold" if self.phase == "acquire" else "retreat") if success else "none",
            "status": status, "failure_owner": raw.get("failure_owner"),
            "failure_code": raw.get("failure_code"), "world_change_started": raw.get("world_change_started"),
            "outcome_known": raw.get("outcome_known", False),
            "evidence_availability": "complete" if success and refs else "partial" if refs else "none",
            "artifact_refs": refs, "bounded_metric_names": [],
        }
        if self.phase == "place":
            summary["post_release_evidence"] = {"availability": "complete" if success and refs else "none", "artifact_refs": refs if success else []}
        result = {key: value for key, value in self.arguments.items() if key not in {"freshness_ms", "max_age_ms", "frame_id"}}
        result.update(status=status, frame={"frame_id": self.arguments["frame_id"], "unit": "m"}, capability_outcome_summary=summary)
        if raw.get("new_scene_revision"):
            result["new_scene_revision"] = raw["new_scene_revision"]
        result["evidence_refs"] = refs + ([f"placed:{self.arguments['entity_ref']}"] if success and self.phase == "place" else [])
        return result

    def cancel(self):
        self.driver.cancel()

    def stop(self):
        self.driver.stop()


def _spec(spec):
    spec = deepcopy(spec)
    action = spec["semantics"] == "action"
    spec["planning"] = {"schema_version": "paos-tool-spec-policy/v1",
                        "capabilities": [spec["tool_id"], "object.relocate"],
                        "refreshes_scene": spec["tool_id"] == "scene.observe",
                        "input_binding_keys": ["entity_ref", "destination_ref"] if spec["tool_id"] == "object.place" else ["entity_ref"] if action else [],
                        "scene_write_behavior": "new_revision" if action else "none"}
    if spec["tool_id"] == "scene.observe":
        spec["planning"]["capabilities"].append("task.verify")
    if action:
        properties = spec["output_schema"]["properties"]["result"]["properties"]
        properties["new_scene_revision"] = {"type": "string", "minLength": 1}
        properties["evidence_refs"] = {"type": "array", "items": {"type": "string"}}
        properties["capability_outcome_summary"]["properties"]["world_change_started"] = {"type": ["boolean", "null"]}
    return spec


class PersistentObservationSource:
    def __init__(self, client):
        self.client = client

    def capture(self, request):
        return self.client.query("observe", request)


class PersistentActionEndpoint:
    """Resolve admitted preparation evidence before starting a provider Action."""

    def __init__(self, phase: str, client, resolve: Callable[[str, Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self.phase = phase
        self.client = client
        self.resolve = resolve

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
        resolved = deepcopy(dict(self.resolve(self.phase, public)))
        keys = ("entity_ref", "candidate_ref", "preparation_ref") + (("destination_ref",) if self.phase == "place" else ())
        for key in keys:
            if resolved.get(key) != public.get(key):
                raise ValueError(f"resolved preparation changed {key}")
        if self.phase == "place":
            resolved["acquire_invocation_id"] = public["acquire_invocation_ref"]

        def start(invocation_id, attempt_id):
            driver = self.client.start(self.phase, invocation_id, f"paos:{parts[1]}", resolved)
            return ActionAdmission(driver=_ProjectedDriver(driver, self.phase, public))

        return ActionAdmission(start=start)


def build_persistent_runtime(*, client, understanding_provider, grasp_provider,
                             preparation_provider, capability_provider, resolve_preparation) -> CapabilityRuntime:
    """Use injected model providers and one persistent manipulation process.

    resolve_preparation belongs to the adapter and supplies the approved route
    and current admission scene from its preparation artifacts. Public Action
    arguments keep the original candidate/acquire provenance intact.
    """
    runtime = CapabilityRuntime()
    runtime.register_tool(_spec(OBSERVATION_TOOL_SPEC), ObservationEndpoint(PersistentObservationSource(client)))
    runtime.register_tool(_spec(SCENE_UNDERSTANDING_TOOL_SPEC), SceneUnderstandingEndpoint(understanding_provider))
    runtime.register_tool(_spec(GRASP_PROPOSAL_TOOL_SPEC), GraspProposalEndpoint(grasp_provider))
    runtime.register_tool(_spec(CAPABILITY_TOOL_SPEC), CapabilitySnapshotEndpoint(capability_provider))
    runtime.register_tool(_spec(MANIPULATION_TOOL_SPEC), ManipulationPreparationEndpoint(preparation_provider))
    runtime.register_tool(_spec(ACQUIRE_TOOL_SPEC), PersistentActionEndpoint("acquire", client, resolve_preparation))
    runtime.register_tool(_spec(PLACE_TOOL_SPEC), PersistentActionEndpoint("place", client, resolve_preparation))
    return runtime
