"""Experimental rank fusion for incomparable BM25 and WMD values."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping


def rank_fuse_bm25_wmd(bm25_rows: Iterable[Mapping[str, object]], wmd_rows: Iterable[Mapping[str, object]], rrf_k: int = 60) -> list[dict]:
    """Fuse ranks only; raw BM25 relevance and WMD distances are never added."""
    if rrf_k < 1:
        raise ValueError("rrf_k must be positive")
    merged: dict[str, dict] = {}
    scores: defaultdict[str, float] = defaultdict(float)
    for rank, row in enumerate(bm25_rows, 1):
        chunk_id = str(row["chunk_id"])
        merged.setdefault(chunk_id, dict(row))
        scores[chunk_id] += 1.0 / (rrf_k + rank)
    for rank, row in enumerate(wmd_rows, 1):
        chunk_id = str(row["chunk_id"])
        # Keep WMD diagnostics on a chunk already introduced by BM25. This is
        # presentation metadata only; the fused score still uses ranks alone.
        merged.setdefault(chunk_id, dict(row)).update(
            {key: value for key, value in row.items() if value is not None}
        )
        scores[chunk_id] += 1.0 / (rrf_k + rank)
    ordered = sorted(merged, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    result: list[dict] = []
    for rank, chunk_id in enumerate(ordered, 1):
        row = dict(merged[chunk_id])
        row["bm25_wmd_rrf_score"] = scores[chunk_id]
        row["bm25_wmd_rrf_rank"] = rank
        result.append(row)
    return result
