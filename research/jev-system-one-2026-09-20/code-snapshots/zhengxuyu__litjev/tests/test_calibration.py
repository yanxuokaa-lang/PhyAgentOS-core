import numpy as np
import pytest

from litjev.calibration import CalibrationProfile, TemperatureCalibrator


def test_temperature_calibration_reduces_overconfident_nll() -> None:
    logits = np.array(
        [
            [8.0, 0.0],
            [8.0, 0.0],
            [8.0, 0.0],
            [8.0, 0.0],
        ]
    )
    labels = np.array([0, 0, 1, 1])

    profile = TemperatureCalibrator.fit(logits, labels)

    assert profile.temperature > 1.0
    assert profile.nll_after < profile.nll_before
    assert profile.sample_count == 4


def test_calibration_profile_round_trip(tmp_path) -> None:
    profile = TemperatureCalibrator.fit(
        np.array([[2.0, 0.0], [0.0, 2.0]]),
        np.array([0, 1]),
        model_id="test-model",
    )
    path = tmp_path / "calibration.json"

    profile.save(path)
    restored = profile.load(path)

    assert restored == profile


def test_pre_migration_profiles_cannot_be_silently_reused(tmp_path):
    path = tmp_path / "old.json"
    path.write_text('{"temperature": 2, "sample_count": 2, "nll_before": 1, "nll_after": 0.5}')
    with pytest.raises(ValueError, match="refit"):
        CalibrationProfile.load(path)
