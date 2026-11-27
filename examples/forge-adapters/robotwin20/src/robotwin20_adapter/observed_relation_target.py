"""Current-binding relation targets from measured visual geometry, without motion."""

import json
from collections.abc import Mapping
from copy import deepcopy
from uuid import uuid4

import numpy as np

from .grounding import IDENTITY_KEYS
from .observed_binding import rigid_transform
from .observed_support import estimate_support
from .route_evidence import _artifact_path


class ObservedRelationTargetProvider:
    """Own visual/execution correspondence and observation-only support geometry."""

    def __init__(self, grounding, *, task_name):
        self.grounding = grounding
        self.task_name = task_name

    def _binding(self, binding_ref, identity):
        binding = self.grounding.bindings.get(binding_ref)
        if not isinstance(binding, Mapping):
            raise ValueError("relation target requires an explicit current scene binding")
        if (any(binding.get(key) != identity.get(key) for key in IDENTITY_KEYS)
                or binding.get("frame_id") != identity.get("frame_id")
                or binding.get("motion_authorized") is not False):
            raise ValueError("relation target binding identity/frame differs from current Query")
        self.grounding._current(binding)
        key = tuple(binding[k] for k in IDENTITY_KEYS)
        observation = self.grounding.observations.get(key)
        understanding = self.grounding.understandings.get(key)
        if (not isinstance(observation, Mapping) or not isinstance(understanding, Mapping)
                or observation.get("frame", {}).get("frame_id") != binding["frame_id"]
                or understanding.get("frame", {}).get("frame_id") != binding["frame_id"]):
            raise ValueError("relation target lacks current observation/understanding")
        calibration = json.loads(_artifact_path(self.grounding.root, binding["calibration_ref"]).read_text())
        if (calibration.get("camera_name") != binding["frame_id"]
                or not np.allclose(np.linalg.inv(rigid_transform(calibration["extrinsic_cv"])),
                                   rigid_transform(binding["world_T_observation"]))):
            raise ValueError("relation target calibration differs from current binding")
        mappings = binding.get("bindings", [])
        visual = [entry.get("entity_ref") for entry in mappings]
        execution = [entry.get("execution_entity_ref") for entry in mappings]
        if (not visual or any(not isinstance(ref, str) or not ref.startswith("entity://")
                              for ref in (*visual, *execution))
                or len(set(visual)) != len(visual) or len(set(execution)) != len(execution)
                or set(visual) != set(binding.get("objects", {}))
                or any(binding["objects"][ref].get("entity_ref") != target
                       for ref, target in zip(visual, execution))):
            raise ValueError("relation binding visual/execution correspondence is ambiguous")
        return binding, observation, understanding

    def project_relation_goal(self, task_goal_facts, *, subtask_id, binding_ref, identity):
        """Project a preserved benchmark goal through one measured scene binding."""
        binding, _, _ = self._binding(binding_ref, identity)
        goals = [goal for goal in task_goal_facts.get("goals", [])
                 if goal.get("subtask_id") == subtask_id]
        if len(goals) != 1 or task_goal_facts.get("motion_authorized") is not False:
            raise ValueError("relation goal is absent or ambiguous")
        goal = goals[0]
        reverse = {entry["execution_entity_ref"]: entry["entity_ref"] for entry in binding["bindings"]}
        moving = reverse.get(goal.get("execution_entity_ref"))
        source_target = goal.get("relation_target_ref")
        target = (reverse.get(source_target) if isinstance(source_target, str)
                  and source_target.startswith("entity://") else source_target)
        if (moving is None or not isinstance(target, str)
                or not target.startswith(("entity://", "surface://")) or moving == target):
            raise ValueError("relation goal lacks unique current visual correspondence")
        source_refs = list(task_goal_facts.get("evidence_refs", []))
        if task_goal_facts.get("goal_ref"):
            source_refs.append(task_goal_facts["goal_ref"])
        evidence = {
            "schema_version": "paos-robotwin20-relation-goal-projection/v1",
            "task_name": self.task_name, "binding_ref": binding_ref,
            **{key: binding[key] for key in IDENTITY_KEYS},
            "source_goal": deepcopy(task_goal_facts), "source_subtask": deepcopy(goal),
            "source_evidence_refs": list(dict.fromkeys(source_refs)),
            "entity_ref": moving, "relation_target_ref": target,
            "execution_entity_ref": goal["execution_entity_ref"],
            "execution_relation_target_ref": source_target, "motion_authorized": False,
        }
        ref = self.grounding._write("relation-goal-projections", evidence)
        return {"entity_ref": moving, "relation_target_ref": target,
                "scene_entity_refs": list(binding["objects"]),
                "evidence_refs": list(dict.fromkeys([binding_ref, *source_refs, ref]))}

    def _cloud(self, binding, understanding, entity_ref):
        matches = [item for item in understanding.get("derived_artifacts", [])
                   if item.get("kind") == "object_point_cloud" and item.get("entity_ref") == entity_ref]
        if len(matches) != 1:
            raise ValueError("relation target requires one current object point cloud")
        cloud = matches[0]
        if (any(cloud.get(key) != binding[key] for key in IDENTITY_KEYS)
                or cloud.get("frame_id") != binding["frame_id"]):
            raise ValueError("relation point cloud lineage differs from current binding")
        points = np.load(_artifact_path(self.grounding.root, cloud["artifact_ref"] + ".npy"), allow_pickle=False)
        if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 3
                or not np.issubdtype(points.dtype, np.number) or not np.isfinite(points).all()):
            raise ValueError("relation point cloud is invalid")
        transform = rigid_transform(binding["world_T_observation"])
        return cloud["artifact_ref"], points @ transform[:3, :3].T + transform[:3, 3]

    def propose(self, request):
        if request.get("goal_relation") != "on":
            raise ValueError("observed relation target supports on relations")
        binding, observation, understanding = self._binding(request.get("binding_ref"), request)
        moving_ref, target_ref = request["entity_ref"], request["relation_target_ref"]
        if moving_ref == target_ref or moving_ref not in binding["objects"]:
            raise ValueError("relation moving entity is absent or self-supporting")
        moving = binding["objects"][moving_ref]
        if not str(moving.get("object_frame_id", "")).startswith("observed-envelope"):
            raise ValueError("relation moving extent is not a current visual model")
        moving_cloud, _ = self._cloud(binding, understanding, moving_ref)
        pose = rigid_transform(moving["world_T_object"])
        half = np.abs(pose[:3, :3]) @ np.asarray(moving["half_extents_m"], dtype=float)
        if half.shape != (3,) or not np.isfinite(half).all() or np.any(half <= 0):
            raise ValueError("relation moving visual extent is invalid")
        policy = self.grounding.support_policy
        cloud_refs = [moving_cloud]
        if target_ref.startswith("entity://"):
            if target_ref not in binding["objects"]:
                raise ValueError("relation support entity is not scene-bound")
            support_ref, points = self._cloud(binding, understanding, target_ref)
            cloud_refs.append(support_ref)
            # Full object clouds include vertical sides. Estimate only the
            # highest observed band; isolated raised points fail the same
            # minimum-point/tilt checks instead of becoming a support plane.
            top = points[points[:, 2] >= points[:, 2].max() - policy.inlier_distance_m]
            support = estimate_support(top, support_ref, policy)
            height = support["estimation"]["height_m"]
            if np.any(points[:, 2] > height + policy.inlier_distance_m):
                raise ValueError("relation support top is contaminated by raised geometry")
            top = top[np.abs(top[:, 2] - height) <= policy.inlier_distance_m]
            low, high = top[:, :2].min(axis=0), top[:, :2].max(axis=0)
            margin = policy.uncertainty_m
            if np.any(high - low < 2 * (half[:2] + margin)):
                raise ValueError("relation support top has insufficient footprint")
            pose[:2, 3] = (low + high) / 2
            pose[2, 3] = float(top[:, 2].max()) + policy.uncertainty_m + half[2]
            support["top_bounds_xy_m"] = [low.tolist(), high.tolist()]
        elif target_ref == "surface://table":
            # Explicit table goals use unmasked scene depth, avoiding accidental
            # reuse of an object's semantic on-support as the table surface.
            support = self.grounding._observed_support_from_depth(binding, understanding)
            projected, _ = self.grounding._free_support_target(binding, moving_ref, support)
            pose = rigid_transform(projected["world_T_object_target"])
        else:
            raise ValueError("observed relation target surface is unsupported")
        depth = self.grounding._depth_artifact_for_binding(observation, binding, code="observed_support_unavailable")
        # Recheck after disk reads before publishing a target candidate.
        self.grounding._current(binding)
        token = uuid4().hex
        evidence = {
            "schema_version": "paos-robotwin20-relation-target-evidence/v1",
            "task_name": self.task_name, "query": deepcopy(dict(request)),
            "geometry_source": "observation", "binding_ref": request["binding_ref"],
            "execution_mappings": [{"entity_ref": item["entity_ref"],
                                    "execution_entity_ref": item["execution_entity_ref"]}
                                   for item in binding["bindings"]],
            "cloud_refs": cloud_refs, "depth_ref": depth["ref"],
            "calibration_ref": binding["calibration_ref"], "support": support,
            "support_world_top_m": float(pose[2, 3] - half[2]),
            "world_T_object_target": pose.reshape(-1).tolist(), "motion_authorized": False,
        }
        evidence_ref = self.grounding._write("relation-target-evidence", evidence)
        return {"status": "available", "candidate_set_ref": f"relation-target-set://{token}",
                **{key: request[key] for key in (*IDENTITY_KEYS, "frame_id", "entity_ref",
                                                "goal_relation", "relation_target_ref")},
                "candidates": [{"candidate_ref": f"relation-target://{token}/1",
                                "destination_ref": f"destination://relation/{token}",
                                "world_T_object_target": pose.reshape(-1).tolist(),
                                "evidence_refs": [evidence_ref]}], "motion_authorized": False}
