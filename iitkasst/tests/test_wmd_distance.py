import numpy as np
import pytest

from doc2dial_retrieval.wmd.distance import (
    EmptyDistributionError,
    WmdError,
    exact_wmd,
    ground_cost,
    weighted_centroid_cosine,
)


def test_identical_distributions_have_zero_wmd() -> None:
    masses = np.asarray([0.5, 0.5])
    vectors = np.asarray([[0.0, 0.0], [1.0, 0.0]])
    assert exact_wmd(masses, vectors, masses, vectors) == pytest.approx(0.0)


def test_exact_wmd_is_symmetric_and_nonnegative() -> None:
    left_masses = np.asarray([1.0])
    right_masses = np.asarray([0.5, 0.5])
    left = np.asarray([[0.0, 0.0]])
    right = np.asarray([[1.0, 0.0], [3.0, 0.0]])
    forward = exact_wmd(left_masses, left, right_masses, right)
    backward = exact_wmd(right_masses, right, left_masses, left)
    assert forward == pytest.approx(2.0)
    assert backward == pytest.approx(forward)
    assert forward >= 0.0


def test_ground_cost_is_euclidean() -> None:
    cost = ground_cost(np.asarray([[0.0, 0.0]]), np.asarray([[3.0, 4.0]]))
    assert cost.shape == (1, 1)
    assert cost[0, 0] == pytest.approx(5.0)


def test_weighted_centroid_cosine_is_a_separate_similarity_baseline() -> None:
    vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]])
    assert weighted_centroid_cosine(np.asarray([1.0, 0.0]), vectors, np.asarray([1.0, 0.0]), vectors) == pytest.approx(1.0)


def test_empty_or_invalid_distributions_fail_closed() -> None:
    with pytest.raises(EmptyDistributionError):
        exact_wmd(np.asarray([]), np.empty((0, 2)), np.asarray([1.0]), np.asarray([[0.0, 0.0]]))
    with pytest.raises(WmdError):
        exact_wmd(np.asarray([1.0]), np.asarray([[np.nan, 0.0]]), np.asarray([1.0]), np.asarray([[0.0, 0.0]]))
