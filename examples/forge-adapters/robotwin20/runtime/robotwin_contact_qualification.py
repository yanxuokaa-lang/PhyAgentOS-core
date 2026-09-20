"""Persistent no-motion contact qualification, using the bound observed model."""

from copy import deepcopy
from math import isfinite

from robotwin_grasp_contact_geometry_worker import capture_task_geometry
from robotwin_route_planner import evaluate_contact

from robotwin20_adapter.grasp_postprocessing import (
    GRASP_POSTPROCESSING_SCHEMA_VERSION,
    _quaternion_rotation,
    _rotation_quaternion,
    derive_robot_hand_pose,
    qualify_geometry_artifact,
)


def qualify_point_contact(task, candidate, geometry, arm, hand, distances, approach, scene, deadline):
    import numpy as np
    from robotwin_gripper_geometry import geometry_samples, gripper_configuration
    from robotwin_observed_collision import collision_components
    from robotwin_planning_geometry import _quat_matrix_wxyz

    from robotwin20_adapter.observed_collision import local_contact, visibility_counts

    reference = geometry["arms"][arm]["reference_hand_pose"]
    reference_rotation = _quat_matrix_wxyz(reference["orientation_wxyz"])
    entity = getattr(task.robot, f"{arm}_entity")
    original = np.asarray(entity.get_qpos()).copy()
    opened = next(geometry_samples(original, gripper_configuration(task, arm, "open")))
    try:
        entity.set_qpos(opened.tolist())
        links = {link.get_name(): link for link in entity.get_links()}
        shapes = {name: [(vertices - reference["position_m"]) @ reference_rotation
                         for vertices in collision_components(links[name])]
                  for name in ("panda_hand", "panda_leftfinger", "panda_rightfinger")}
    finally:
        entity.set_qpos(original.tolist())
    if any(not parts for parts in shapes.values()):
        raise ValueError("gripper collision components are incomplete")
    rotation = np.asarray(_quaternion_rotation(hand["orientation_xyzw"], "hand orientation"))
    grasp = candidate["execution_grasp"]
    target = np.asarray(grasp["robot_target_pose"]["position_m"])
    ingress = np.asarray(grasp["ingress_direction"]["vector"])
    sweep = (np.asarray(approach) - target) @ rotation
    all_vertices = np.concatenate([v for parts in shapes.values() for v in parts])
    variants = []
    for distance in distances:
        deadline.remaining("contact_qualification")
        delta = -distance * ingress
        position = np.asarray(hand["position_m"]) + delta
        target_points = (scene["target"] - position) @ rotation
        environment = (scene["environment"] - position) @ rotation
        local = local_contact(target_points, environment, shapes, approach_delta=sweep, policy=scene["policy"])
        vertices_world = all_vertices @ rotation.T + position
        support = float(vertices_world[:, 2].min()) - geometry["support_plane"]["offset_m"]
        reasons = list(local["rejection_reasons"])
        if support < 0:
            reasons.append("mesh_support_penetration")
        visibility = visibility_counts(np.vstack((vertices_world, vertices_world + np.asarray(approach) - target)),
            scene["depth"], scene["intrinsic"], scene["world_T_camera"],
            scene["policy"].depth_scale_to_m, scene["policy"].uncertainty_m)
        variants.append({"backoff_m": distance, "robot_target_position_m": (target + delta).tolist(),
            "contact_center_position_m": (np.asarray(grasp["contact_center_pose"]["position_m"]) + delta).tolist(),
            "support_clearance_m": support, "local_contact": local, "visibility": visibility,
            "visibility_sampling": "convex_vertices_at_contact_and_approach_endpoints",
            "rejection_reasons": reasons, "status": "valid" if not reasons else "rejected"})
    selected = next((v for v in variants if v["status"] == "valid"), None)
    return {"schema_version": GRASP_POSTPROCESSING_SCHEMA_VERSION, "parent_candidate_ref": candidate["candidate_ref"],
            "variants": variants, "selected_backoff_m": None if selected is None else selected["backoff_m"],
            "status": "qualified" if selected else "unavailable", "motion_authorized": False,
            "qualification_scope": "observed_convex_contact_and_approach", "observed_collision": scene["evidence"]}


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
    scene = getattr(task, "_paos_observed_collision", None)
    for arm in arms:
        deadline.remaining("contact_qualification")
        mesh = (qualify_point_contact(task, bound, geometry, arm, hand, distances, approach, scene, deadline)
                if scene is not None else qualify_geometry_artifact(bound, geometry, arm_id=arm, **kwargs))
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
        if scene is None:
            qualification = qualify_geometry_artifact(bound, geometry, arm_id=arm,
                curobo_clearance_m=[v["clearance_m"] if v["planner_status"] == "success" else None for v in evaluations], **kwargs)
        else:
            qualification = deepcopy(mesh)
            for variant, evaluation in zip(qualification["variants"], evaluations):
                variant["planner_status"] = evaluation["planner_status"]
                variant["curobo_clearance_m"] = evaluation["clearance_m"]
                if evaluation["planner_status"] != "success":
                    variant["status"] = "rejected"
                    variant["rejection_reasons"].append("planner_not_evaluated" if evaluation["planner_status"] == "not_evaluated" else "contact_planner_rejected")
                elif evaluation["clearance_m"] is None or not isfinite(evaluation["clearance_m"]) or evaluation["clearance_m"] < 0:
                    variant["status"] = "rejected"
                    variant["rejection_reasons"].append("contact_clearance_unproven_or_negative")
            selected_variant = next((v for v in qualification["variants"] if v["status"] == "valid"), None)
            qualification["status"] = "qualified" if selected_variant else "unavailable"
            qualification["selected_backoff_m"] = None if selected_variant is None else selected_variant["backoff_m"]
            qualification["qualification_scope"] = "observed_convex_and_curobo_contact"
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
