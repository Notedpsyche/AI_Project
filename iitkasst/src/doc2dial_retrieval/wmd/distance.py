"""Exact balanced optimal transport for Word Mover's Distance."""

from __future__ import annotations

import math

import numpy as np
import ot


class WmdError(ValueError):
    """Raised when a WMD measure cannot be solved safely."""


class EmptyDistributionError(WmdError):
    """Raised when preprocessing leaves no transport mass."""


def _validate_measure(masses: np.ndarray, vectors: np.ndarray, name: str) -> tuple[np.ndarray, np.ndarray]:
    weights = np.asarray(masses, dtype=np.float64)
    matrix = np.asarray(vectors, dtype=np.float64)
    if weights.ndim != 1 or matrix.ndim != 2 or len(weights) != len(matrix):
        raise WmdError(f"{name} masses and vectors have incompatible shapes")
    if not len(weights):
        raise EmptyDistributionError(f"{name} has no transport terms")
    if not np.isfinite(weights).all() or not np.isfinite(matrix).all():
        raise WmdError(f"{name} contains non-finite values")
    if (weights < 0).any() or not math.isclose(float(weights.sum()), 1.0, abs_tol=1e-12):
        raise WmdError(f"{name} masses must be non-negative and sum to one")
    return weights, matrix


def ground_cost(left_vectors: np.ndarray, right_vectors: np.ndarray) -> np.ndarray:
    left = np.asarray(left_vectors, dtype=np.float64)
    right = np.asarray(right_vectors, dtype=np.float64)
    if left.ndim != 2 or right.ndim != 2 or left.shape[1:] != right.shape[1:]:
        raise WmdError("Ground-cost vectors must be two-dimensional with equal dimensions")
    if not len(left) or not len(right) or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise WmdError("Ground-cost vectors must be finite and non-empty")
    cost = np.ascontiguousarray(np.linalg.norm(left[:, None, :] - right[None, :, :], axis=2), dtype=np.float64)
    if not np.isfinite(cost).all() or (cost < 0).any():
        raise WmdError("Ground-cost matrix is invalid")
    return cost


def exact_wmd(
    left_masses: np.ndarray,
    left_vectors: np.ndarray,
    right_masses: np.ndarray,
    right_vectors: np.ndarray,
) -> float:
    """Return exact Earth Mover's Distance under Euclidean token costs."""
    a, left = _validate_measure(left_masses, left_vectors, "left")
    b, right = _validate_measure(right_masses, right_vectors, "right")
    if not math.isclose(float(a.sum()), float(b.sum()), abs_tol=1e-12):
        raise WmdError("Transport marginals have unequal total mass")
    distance = float(ot.emd2(a, b, ground_cost(left, right), numItermax=100000))
    if not math.isfinite(distance):
        raise WmdError("Optimal transport produced a non-finite distance")
    if distance < -1e-10:
        raise WmdError("Optimal transport produced a negative distance")
    return max(distance, 0.0)


def weighted_centroid_cosine(
    left_masses: np.ndarray,
    left_vectors: np.ndarray,
    right_masses: np.ndarray,
    right_vectors: np.ndarray,
) -> float:
    """Paper-style weighted-centroid cosine baseline, distinct from WMD."""
    a, left = _validate_measure(left_masses, left_vectors, "left")
    b, right = _validate_measure(right_masses, right_vectors, "right")
    left_centroid = a @ left
    right_centroid = b @ right
    denominator = float(np.linalg.norm(left_centroid) * np.linalg.norm(right_centroid))
    if denominator <= 1e-12 or not math.isfinite(denominator):
        raise WmdError("Centroid cosine has a zero or non-finite norm")
    similarity = float(left_centroid @ right_centroid / denominator)
    if not math.isfinite(similarity):
        raise WmdError("Centroid cosine is non-finite")
    return max(-1.0, min(1.0, similarity))
