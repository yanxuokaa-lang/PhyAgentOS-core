"""Adapter-private preparation projection from Coordinator-owned Query evidence."""

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path

from PhyAgentOS.forge.manipulation import ManipulationIntent
from pick_place_workflow.relation_target import bind_relation_target_candidate

from .route_evidence import _artifact_path
from .stack_relation_preparation import StackRelationPreparationError


def build_stack_relation_preparation_inputs(artifact_root: Path, *, task_name: str):
    """Read the exact direct-predecessor records supplied by the Coordinator port."""
    def resolve(request, task_id):
        context = request.get("coordinator_context")
        if not isinstance(context, Mapping) or context.get("task_id") != task_id:
            raise StackRelationPreparationError("stack preparation requires Coordinator context")
        intent = ManipulationIntent.model_validate(context.get("intent"))
        if intent.task_id != task_id or request.get("intent") != intent.model_dump(mode="json"):
            raise StackRelationPreparationError("stack preparation intent differs from Coordinator context")
        queries = context.get("predecessor_queries")
        required = ("scene.bind", "grasp.propose", "manipulation.capabilities", "relation.target")
        if not isinstance(queries, Mapping) or any(key not in queries for key in required):
            raise StackRelationPreparationError("stack preparation lacks direct predecessor Queries")
        identity = {key: getattr(intent, key) for key in
                    ("scene_revision", "observation_ref", "calibration_ref")}
        for name in required:
            query = queries[name]
            if (not isinstance(query, Mapping) or not isinstance(query.get("arguments"), Mapping)
                    or not isinstance(query.get("result"), Mapping)):
                raise StackRelationPreparationError("stack predecessor Query projection is invalid")
            if any(query["arguments"].get(key) != value for key, value in identity.items()):
                raise StackRelationPreparationError(f"{name} Query identity differs from current intent")
            if query["result"].get("status") != "available":
                raise StackRelationPreparationError(f"{name} Query is unavailable")
        bound = queries["scene.bind"]["result"]
        grasp = queries["grasp.propose"]["result"]
        capability = queries["manipulation.capabilities"]["result"]
        relation = queries["relation.target"]["result"]
        for name, result in (("scene.bind", bound), ("grasp.propose", grasp),
                             ("manipulation.capabilities", capability), ("relation.target", relation)):
            if any(result.get(key) != value for key, value in identity.items()):
                raise StackRelationPreparationError(f"{name} result identity differs from current intent")
        if (bound.get("frame_id") != "world"
                or bound.get("observation_frame_id") != intent.observation_frame_id
                or grasp.get("frame", {}).get("frame_id") != intent.observation_frame_id
                or grasp.get("candidate_set_ref") != intent.candidate_set_ref):
            raise StackRelationPreparationError("stack preparation frame/candidate lineage differs")
        entities = bound.get("entities", [])
        matches = [entry for entry in entities if entry.get("entity_ref") == intent.entity_ref]
        if len(matches) != 1:
            raise StackRelationPreparationError("stack preparation entity is not uniquely scene-bound")
        if matches[0].get("execution_entity_ref") != relation.get("entity_ref"):
            raise StackRelationPreparationError("stack relation Provider requires observed-to-execution identity mapping")
        relation_arguments = queries["relation.target"]["arguments"]
        selected = bind_relation_target_candidate(
            relation, candidate_ref=request.get("candidate_ref"), expected=relation_arguments)
        if (request.get("relation_query_result") != relation
                or request.get("relation_binding") != selected):
            raise StackRelationPreparationError("selected relation differs from persisted Query")
        sources = set()
        for ref in selected["evidence_refs"]:
            try:
                evidence = json.loads(_artifact_path(Path(artifact_root), ref).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise StackRelationPreparationError("relation evidence artifact is unavailable or invalid") from exc
            if (not isinstance(evidence, Mapping)
                    or evidence.get("schema_version") != "paos-robotwin20-relation-target-evidence/v1"
                    or evidence.get("task_name") != task_name
                    or evidence.get("query") != relation_arguments
                    or evidence.get("motion_authorized") is not False
                    or not isinstance(evidence.get("geometry_source"), str)
                    or not evidence["geometry_source"].strip()):
                raise StackRelationPreparationError("relation evidence artifact does not match persisted Query")
            sources.add(evidence["geometry_source"])
        if len(sources) != 1:
            raise StackRelationPreparationError("relation evidence has ambiguous geometry sources")
        grasp_arguments = queries["grasp.propose"]["arguments"]
        return deepcopy({
            **identity, "intent": intent.model_dump(mode="json"),
            "entity_ref": intent.entity_ref, "frame_id": intent.observation_frame_id,
            "binding_ref": bound["binding_ref"], "candidate_set_ref": grasp["candidate_set_ref"],
            "candidates": grasp["candidates"], "capability_snapshot_ref": capability["snapshot_ref"],
            "freshness_ms": grasp_arguments["freshness_ms"], "max_age_ms": grasp_arguments["max_age_ms"],
            "target_geometry_source": sources.pop(),
        })
    return resolve
