import numpy as np

from litjev.scoring import calibrated_distribution


def test_calibrated_distribution_only_uses_allowed_candidates() -> None:
    logits = np.array([100.0, 2.0, 1.0, -2.0])

    result = calibrated_distribution(
        vocabulary_logits=logits,
        candidate_token_ids=[1, 2, 3],
        temperature=2.0,
    )

    assert result.winner_index == 0
    assert np.isclose(sum(result.probabilities), 1.0)
    assert result.probabilities[0] > result.probabilities[1]
    assert result.probabilities[0] < 0.7
