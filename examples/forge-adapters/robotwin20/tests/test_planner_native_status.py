from types import SimpleNamespace

import pytest
from robotwin_capability_controller import ControllerLimits
from robotwin_planning_geometry import (
    SimulationProbeError,
    _admit_capability_trajectory,
    _validate_trajectory,
)
from robotwin_route_planner import plan_path_with_status


@pytest.mark.parametrize("raises", [False, True])
def test_native_status_is_retained_without_persistent_planner_patch(raises):
    class Model:
        def plan_single(self):
            if raises:
                raise RuntimeError("provider failure")
            return SimpleNamespace(status="IK_FAIL")
    model = Model()
    def plan(pose):
        model.plan_single()
        return {"status": "Fail"}
    task = SimpleNamespace(robot=SimpleNamespace(left_planner=SimpleNamespace(motion_gen=model), left_plan_path=plan))
    if raises:
        with pytest.raises(RuntimeError, match="provider failure"):
            plan_path_with_status(task, "left", [])
    else:
        result = plan_path_with_status(task, "left", [])
        with pytest.raises(SimulationProbeError, match="IK_FAIL"):
            _validate_trajectory(result, [])
    assert "plan_single" not in vars(model)


def test_readiness_canonicalizes_float32_boundary_with_controller_semantics():
    np = pytest.importorskip("numpy")
    limits = ControllerLimits(
        joint_order=tuple(f"j{index}" for index in range(7)),
        position_lower_rad=(-2.8973,) * 7,
        position_upper_rad=(2.8973,) * 7,
        velocity_lower_radps=(-2.0,) * 7,
        velocity_upper_radps=(2.0,) * 7,
    )
    result = {
        "status": "Success",
        "position": np.asarray([[2.8973000049591064] + [0.0] * 6], dtype=np.float64),
        "velocity": np.zeros((1, 7), dtype=np.float64),
    }

    admitted = _admit_capability_trajectory(result, limits)

    assert admitted["position"][0, 0] == 2.8973


def test_readiness_rejects_material_capability_violation():
    np = pytest.importorskip("numpy")
    limits = ControllerLimits(
        joint_order=tuple(f"j{index}" for index in range(7)),
        position_lower_rad=(-2.8973,) * 7,
        position_upper_rad=(2.8973,) * 7,
        velocity_lower_radps=(-2.0,) * 7,
        velocity_upper_radps=(2.0,) * 7,
    )
    result = {
        "status": "Success",
        "position": np.asarray([[2.89731] + [0.0] * 6], dtype=np.float64),
        "velocity": np.zeros((1, 7), dtype=np.float64),
    }

    with pytest.raises(SimulationProbeError, match="position exceeds"):
        _admit_capability_trajectory(result, limits)
