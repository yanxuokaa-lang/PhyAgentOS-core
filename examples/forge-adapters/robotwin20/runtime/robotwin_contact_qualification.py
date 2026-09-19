"""Persistent no-motion contact qualification, using the bound observed model."""

from copy import deepcopy

from robotwin_grasp_contact_geometry_worker import capture_task_geometry
from robotwin_route_planner import evaluate_contact

from robotwin20_adapter.grasp_postprocessing import (
    _rotation_quaternion,
    derive_robot_hand_pose,
    qualify_geometry_artifact,
)


def qualify_observed_contact(task, request, candidate, record, adaptation, arms, deadline, *, runtime_profile):
    if not arms or any(arm not in {"left", "right"} for arm in arms):
        raise ValueError("contact qualification requires explicit supported arms")
    deadline.remaining("contact_qualification")
    distances = adaptation.get("contact_backoff_candidates_m", [0.])
    geometry = capture_task_geometry(task, runtime_profile)
    geometry["scene_revision"] = request["scene_revision"]
    model = record["world_T_object"]
    hand = derive_robot_hand_pose(candidate["execution_grasp"]["robot_target_pose"],
                                 reference_distance_m=adaptation["robot_target_reference_distance_m"],
                                 gripper_bias_m=adaptation["robot_gripper_bias_m"], delta_matrix=adaptation["robot_delta_matrix"])
    kwargs = dict(object_center_m=[model[i] for i in (3, 7, 11)],
                  object_half_extents_m=record["half_extents_m"],
                  object_orientation_xyzw=_rotation_quaternion([model[i:i+3] for i in (0, 4, 8)]),
                  backoff_candidates_m=distances, target_hand_pose=hand, check_finger_envelope=True)
    bound = {**candidate, "scene_revision": request["scene_revision"]}
    # Use the materialized nominal approach distance, not an embodiment constant.
    import numpy as np
    approach = candidate["route"][0]["waypoints"][0]["position_m"]
    target = candidate["execution_grasp"]["robot_target_pose"]["position_m"]
    clearance = float(np.linalg.norm(np.asarray(approach) - target))
    attempts, qualified = [], []
    for arm in arms:
        deadline.remaining("contact_qualification")
        mesh = qualify_geometry_artifact(bound, geometry, arm_id=arm, **kwargs)
        evaluations = []
        for variant in mesh["variants"]:
            deadline.remaining("contact_qualification")
            result = {"planner_status": "not_evaluated", "clearance_m": None}
            if variant["status"] == "valid":
                grasp = deepcopy(candidate["execution_grasp"])
                for field, key in (("robot_target_pose", "robot_target_position_m"),
                                   ("contact_center_pose", "contact_center_position_m")):
                    grasp[field]["position_m"] = variant[key]
                result = evaluate_contact(task, grasp, arm, clearance)
            evaluations.append({"backoff_m": variant["backoff_m"], **result})
        deadline.remaining("contact_qualification")
        qualification = qualify_geometry_artifact(bound, geometry, arm_id=arm,
            curobo_clearance_m=[v["clearance_m"] if v["planner_status"] == "success" else None for v in evaluations], **kwargs)
        qualification["provider_evaluation"] = {"arm_id": arm, "variants": evaluations,
            "scene_revision": request["scene_revision"], "motion_authorized": False, "simulator_steps": 0}
        attempts.append({"arm_id": arm, "qualification": qualification})
        if qualification["status"] == "qualified":
            qualified.append((qualification["selected_backoff_m"], arm, qualification))
    selected = min(qualified, key=lambda item: item[:2]) if qualified else None
    return {"status": "qualified" if selected else "unavailable", "motion_authorized": False,
            "scene_revision": request["scene_revision"], "candidate_ref": candidate["candidate_ref"],
            "arm_id": selected[1] if selected else None, "qualification": selected[2] if selected else None,
            "arm_attempts": attempts}
