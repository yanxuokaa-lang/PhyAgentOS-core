from types import SimpleNamespace

import pytest
from robotwin_planning_geometry import SimulationProbeError, _validate_trajectory
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
