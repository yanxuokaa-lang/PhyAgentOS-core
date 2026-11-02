import importlib.util
from pathlib import Path

import pytest


def inspector():
    path = Path(__file__).parents[1] / "scripts" / "inspect_collision_receipt.py"
    spec = importlib.util.spec_from_file_location("collision_receipt_inspector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_private_receipt_inspector_accepts_structured_and_legacy_without_inventing_missing_joints():
    receipt = {"attempts": [
        {"error": "pregrasp IK failed"},
        {"error": "grasp: checked joints=[1, 2, 3, 4, 5, 6, 7]; finger overlaps table"},
        {"collision_diagnostic": {"checked_joints": [7, 6, 5, 4, 3, 2, 1]}},
        {"error": "old checked joints=[0, 0, 0, 0, 0, 0, 0]",
         "collision_diagnostic": {"checked_joints": [1] * 7}},
    ]}
    samples = list(inspector().checked_samples(receipt))
    assert [index for index, _, _ in samples] == [1, 2, 3]
    assert samples[0][2] == pytest.approx([1, 2, 3, 4, 5, 6, 7])
    assert samples[1][2] == pytest.approx([7, 6, 5, 4, 3, 2, 1])
    assert samples[2][2] == pytest.approx([1] * 7)
