import numpy as np
from replay_observed_preparation import reexpress_target


def test_target_reexpression_preserves_rigid_motion_for_every_model_point():
    old = np.eye(4)
    old[:3, :3] = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    old[:3, 3] = [.2, .1, .75]
    new = np.eye(4)
    new[:3, 3] = [.21, .11, .76]
    target = old.copy()
    target[:3, 3] = [.1, -.1, .75]
    result = np.array(reexpress_target(target.ravel().tolist(), old.ravel().tolist(), new.ravel().tolist())).reshape(4, 4)
    assert np.allclose(result @ np.linalg.inv(new), target @ np.linalg.inv(old))
    assert np.allclose(result[:3, :3], np.eye(3))
