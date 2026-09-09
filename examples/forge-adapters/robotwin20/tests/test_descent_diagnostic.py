from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_descent_diagnostic as diagnostic


@pytest.mark.parametrize(
    "center,radius,expected",
    [([0, 0, 1.2], 0.1, 0.1), ([0, 0, 1], 0.001, -0.001), ([0, 0, 0], 0.1, -1.1)],
)
def test_sphere_box_signed_distance(center, radius, expected):
    assert diagnostic.sphere_box_clearance(
        center, radius, [0, 0, 0, 1, 0, 0, 0], [2, 2, 2]
    ) == pytest.approx(expected)


def test_rotated_thin_box_distance():
    q = [2**-0.5, 0, 2**-0.5, 0]
    assert diagnostic.sphere_box_clearance(
        [0.2, 0, 0], 0.01, [0, 0, 0, *q], [2, 2, 0.1]
    ) == pytest.approx(0.14)


def test_failed_ablation_restores_exact_attachment(monkeypatch):
    import sys
    from types import ModuleType

    module = ModuleType("curobo.types.robot")
    module.JointState = object
    monkeypatch.setitem(sys.modules, "curobo.types.robot", module)
    attachment = SimpleNamespace(clone=lambda: snapshot)
    snapshot = np.array([[1.0, 2.0, 3.0, 0.001]])
    calls = []
    model = SimpleNamespace(
        kinematics=SimpleNamespace(
            kinematics_config=SimpleNamespace(get_link_spheres=lambda name: attachment)
        ),
        detach_object_from_robot=lambda: calls.append("detach"),
        attach_spheres_to_robot=lambda **kwargs: calls.append(kwargs),
    )
    task = SimpleNamespace(
        robot=SimpleNamespace(
            right_planner=SimpleNamespace(motion_gen=model),
            right_plan_path=lambda *args, **kwargs: {"status": "Fail"},
        )
    )
    monkeypatch.setattr(diagnostic, "_joint_limits", lambda planner: [])
    with pytest.raises(ValueError, match="segment failed"):
        diagnostic.diagnose_attached_segment(task, {}, "right", None, [], [])
    assert calls[0] == "detach"
    assert calls[1]["sphere_tensor"] is snapshot
    assert calls[1]["link_name"] == "attached_object"
