"""Measured and predicted gripper geometry; no commands or simulator stepping."""

from contextlib import contextmanager
from copy import deepcopy
from itertools import product

import numpy as np


def gripper_configuration(task, arm, command=None):
    """Return joint intervals, keeping control targets distinct from measurements.

    A future close has no known stopping position without contact evidence.
    Retain the measured reference geometry and label the missing prediction;
    do not inflate it or invent a fully closed holding state.
    Open/released predicts the physically achievable endpoint of the command.
    """
    entity = getattr(task.robot, f"{arm}_entity")
    joints = list(entity.get_active_joints())
    indices = {joint.get_name(): i for i, joint in enumerate(joints)}
    measured = np.asarray(entity.get_qpos(), dtype=float)
    gripper = getattr(task.robot, f"{arm}_gripper")
    scale = getattr(task.robot, f"{arm}_gripper_scale")
    if not gripper:
        raise ValueError("gripper geometry joints are unavailable")
    if command not in {None, "open", "contact", "released", "closed"}:
        raise ValueError("unsupported gripper geometry command")
    result = []
    for joint, multiplier, offset in gripper:
        name = joint.get_name()
        index = indices[name]
        low, high = np.asarray(joint.get_limits(), dtype=float).reshape(-1, 2)[0]
        if not np.isfinite([low, high, measured[index]]).all() or low > high:
            raise ValueError("gripper physical limits or measured position are invalid")
        target = None
        if command is None:
            # Small numerical excursions are retained, never silently clamped.
            bounds, source = [float(measured[index])] * 2, "measured_joint"
        elif command == "closed":
            bounds = [float(measured[index])] * 2
            source = "measured_reference_holding_prediction_unavailable"
            target = float(scale[0]) * float(multiplier) + float(offset)
        else:
            target = float(scale[1]) * float(multiplier) + float(offset)
            if not np.isfinite(target):
                raise ValueError("gripper command target is non-finite")
            bounds, source = [float(np.clip(target, low, high))] * 2, "bounded_command_prediction"
        if target is not None and not np.isfinite(target):
            raise ValueError("gripper command target is non-finite")
        result.append({"joint_name": name, "index": index, "bounds_m": bounds,
                       "source": source, "command_target_m": target})
    return result


def geometry_samples(qpos, configuration):
    """Interval corners for the Franka's independent prismatic fingers."""
    for values in product(*(sorted(set(item["bounds_m"])) for item in configuration)):
        sample = np.asarray(qpos, dtype=float).copy()
        for item, value in zip(configuration, values):
            sample[item["index"]] = value
        yield sample


@contextmanager
def planner_gripper_state(task, arm, command=None):
    """Synchronize every CuRobo rollout with the same Runtime-owned joint state.

    Native sphere geometry and margins remain unchanged. Missing future holding
    width is diagnostic information, not a reason to enlarge the robot model.
    All tensors, including existing attachment spheres, are restored on exit.
    """
    import yaml
    from curobo.types.robot import RobotConfig

    configuration = gripper_configuration(task, arm, command)
    planner = getattr(task.robot, f"{arm}_planner")
    with open(planner.yml_path, encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    config = config.get("robot_cfg", config)
    saved = []
    seen = set()
    previous = getattr(task, "_paos_gripper_geometry", None)
    try:
        replacements = []
        for model in (planner.motion_gen, planner.motion_gen_batch):
            source = deepcopy(config)
            locks = source["kinematics"]["lock_joints"]
            for item in configuration:
                name = item["joint_name"]
                if name not in locks:
                    raise ValueError("gripper joint is not a locked planner joint")
                locks[name] = sum(item["bounds_m"]) / 2
            replacement = RobotConfig.from_dict(source, model.tensor_args).kinematics.kinematics_config
            instances = [model.kinematics, *model.get_all_kinematics_instances()]
            configs = [model.robot_cfg.kinematics.kinematics_config,
                       *(instance.kinematics_config for instance in instances)]
            for current in configs:
                identity = id(current)
                if identity in seen:
                    continue
                seen.add(identity)
                original = deepcopy(current)
                saved.append((current, original))
                replacements.append((current, original, replacement))
        # Snapshot all instances before writing: rollouts can share some CUDA
        # tensors while owning separate lock-state and configuration metadata.
        for current, original, replacement in replacements:
            updated = deepcopy(replacement)
            # Preserve attachments, disabled spheres and all native margins.
            updated.link_spheres.copy_(original.link_spheres)
            for item in configuration:
                joint = next(j for j in getattr(task.robot, f"{arm}_entity").get_active_joints()
                             if j.get_name() == item["joint_name"])
                link = joint.get_child_link().get_name()
                indices = updated.get_sphere_index_from_link_name(link)
                if not len(indices):
                    raise ValueError("gripper link has no planner collision spheres")
            current.copy_(updated)
            # CuRobo JointState.copy_ returns an ignored clone when optional
            # velocity/acceleration fields differ; copy locked positions in place.
            current.lock_jointstate.position.copy_(updated.lock_jointstate.position.reshape_as(
                current.lock_jointstate.position))
        task._paos_gripper_geometry = {"arm": arm, "joints": configuration}
        yield configuration
    finally:
        for current, original in reversed(saved):
            # Route attachment changes belong to the caller, not to this
            # temporary finger configuration. Preserve them across restoration.
            attachment = (current.get_link_spheres("attached_object").clone()
                          if "attached_object" in current.link_name_to_idx_map else None)
            current.copy_(original)
            current.lock_jointstate.position.copy_(original.lock_jointstate.position.reshape_as(
                current.lock_jointstate.position))
            if attachment is not None:
                current.update_link_spheres("attached_object", attachment)
        if previous is None:
            task.__dict__.pop("_paos_gripper_geometry", None)
        else:
            task._paos_gripper_geometry = previous
