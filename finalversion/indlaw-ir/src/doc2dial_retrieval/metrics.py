"""Deterministic ranking metrics for grounded retrieval evaluation."""

from __future__ import annotations

from collections.abc import Iterable


def recall_at_k(ranked_ids: Iterable[str], relevant_ids: set[str], k: int) -> bool:
    """Return whether any relevant ID occurs in the first ``k`` results."""
    return bool(set(list(ranked_ids)[:k]) & relevant_ids)


def reciprocal_rank(ranked_ids: Iterable[str], relevant_ids: set[str]) -> float:
    """Return the reciprocal rank of the first relevant result, or zero."""
    for rank, result_id in enumerate(ranked_ids, 1):
        if result_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def aggregate_metrics(
    rows: list[dict], mode: str, cutoffs: tuple[int, ...] = (1, 3, 5, 10)
) -> dict[str, float]:
    """Aggregate Recall@K and MRR for one retrieval mode."""
    if not rows:
        return {f"recall_at_{k}": 0.0 for k in cutoffs} | {"mrr": 0.0}
    metrics = {
        f"recall_at_{k}": sum(
            recall_at_k(row["systems"][mode]["top_ids"], set(row["gold_chunk_ids"]), k)
            for row in rows
        )
        / len(rows)
        for k in cutoffs
    }
    metrics["mrr"] = sum(
        reciprocal_rank(row["systems"][mode]["top_ids"], set(row["gold_chunk_ids"]))
        for row in rows
    ) / len(rows)
    return metrics
