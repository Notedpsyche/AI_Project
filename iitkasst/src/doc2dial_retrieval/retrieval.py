"""BM25, BGE, and deterministic hybrid retrieval."""

# Search result serialization keeps comparable score fields together.
# ruff: noqa: E501

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import torch
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .data import Chunk, tokenize

DENSE_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class SearchResult:
    chunk: Chunk
    semantic_score: float | None = None
    semantic_rank: int | None = None
    bm25_score: float | None = None
    bm25_rank: int | None = None
    rrf_score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {**self.chunk.as_dict(), "semantic_score": self.semantic_score, "semantic_rank": self.semantic_rank,
                "bm25_score": self.bm25_score, "bm25_rank": self.bm25_rank, "rrf_score": self.rrf_score}


def _normalized_evidence(result: SearchResult) -> str:
    return " ".join(re.findall(r"\w+", result.chunk.text.lower()))


def _duplicate_evidence(left: SearchResult, right: SearchResult) -> bool:
    left_text, right_text = _normalized_evidence(left), _normalized_evidence(right)
    if not left_text or not right_text:
        return False
    if left_text == right_text:
        return True
    if min(len(left_text), len(right_text)) < 80:
        return False
    return SequenceMatcher(None, left_text, right_text).ratio() >= 0.94


def dedupe_results(results: list[SearchResult], k: int) -> list[SearchResult]:
    """Keep the strongest ranked representative of repeated evidence."""
    selected: list[SearchResult] = []
    for result in results:
        if any(_duplicate_evidence(result, existing) for existing in selected):
            continue
        selected.append(result)
        if len(selected) >= k:
            break
    return selected


class BM25Store:
    def __init__(self, chunks: list[Chunk], index: BM25Okapi | None = None):
        self.chunks = chunks
        self.index = index or BM25Okapi([tokenize(self.representation(chunk)) for chunk in chunks], k1=1.5, b=0.75)

    @staticmethod
    def representation(chunk: Chunk) -> str:
        return " ".join([*chunk.heading_path, chunk.text])

    def search(self, query: str, k: int = 50) -> list[SearchResult]:
        scores = self.index.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))[:k]
        results = [SearchResult(self.chunks[i], bm25_score=float(scores[i]), bm25_rank=rank) for rank, i in enumerate(order, 1)]
        return dedupe_results(results, k)

    def save(self, path: Path, metadata_path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(self.index, handle)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json_metadata(self.chunks), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, metadata_path: Path) -> BM25Store:
        with path.open("rb") as handle:
            index = pickle.load(handle)
        return cls(load_chunks(metadata_path), index)


class DenseStore:
    def __init__(self, model: SentenceTransformer, chunks: list[Chunk], index: faiss.Index):
        self.model, self.chunks, self.index = model, chunks, index

    def encode_query(self, query: str) -> np.ndarray:
        return self.model.encode([DENSE_PREFIX + query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")

    def encode_queries(self, queries: list[str], batch_size: int = 32) -> np.ndarray:
        return self.model.encode(
            [DENSE_PREFIX + query for query in queries],
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

    def search_vector(self, vector: np.ndarray, k: int = 50) -> list[SearchResult]:
        scores, indices = self.index.search(vector.reshape(1, -1), k)
        results = [
            SearchResult(self.chunks[int(i)], semantic_score=float(score), semantic_rank=rank)
            for rank, (score, i) in enumerate(zip(scores[0], indices[0]), 1)
            if i >= 0
        ]
        return dedupe_results(results, k)

    def search(self, query: str, k: int = 50) -> list[SearchResult]:
        return self.search_vector(self.encode_query(query), k)

    @classmethod
    def load(cls, model_name: str, index_path: Path, metadata_path: Path) -> DenseStore:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = SentenceTransformer(model_name, device=device)
        index = faiss.read_index(str(index_path))
        return cls(model, load_chunks(metadata_path), index)


def load_chunks(path: Path) -> list[Chunk]:
    import json

    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        return [Chunk(**row) for row in json.loads(text)]
    return [Chunk(**json.loads(line)) for line in text.splitlines() if line]


def json_metadata(chunks: list[Chunk]) -> str:
    import json

    return json.dumps([chunk.as_dict() for chunk in chunks], ensure_ascii=False, indent=2)


def hybrid(bm25: list[SearchResult], dense: list[SearchResult], rrf_k: int = 60, final_k: int = 5) -> list[SearchResult]:
    merged: dict[str, SearchResult] = {}
    for result in [*bm25, *dense]:
        current = merged.setdefault(result.chunk.chunk_id, SearchResult(result.chunk))
        if result.bm25_rank is not None:
            current.bm25_rank, current.bm25_score = result.bm25_rank, result.bm25_score
            current.rrf_score = (current.rrf_score or 0.0) + 1 / (rrf_k + result.bm25_rank)
        if result.semantic_rank is not None:
            current.semantic_rank, current.semantic_score = result.semantic_rank, result.semantic_score
            current.rrf_score = (current.rrf_score or 0.0) + 1 / (rrf_k + result.semantic_rank)
    ordered = sorted(merged.values(), key=lambda result: (-(result.rrf_score or 0.0), result.chunk.chunk_id))
    return dedupe_results(ordered, final_k)
