"""Load indexes and execute BM25, semantic, or hybrid search."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

from .retrieval import BM25Store, DenseStore, SearchResult, hybrid


class SearchEngine:
    def __init__(self, root: Path, config_path: str = "configs/config.yaml"):
        config = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
        self.config = config
        self.root = root
        self.bm25 = BM25Store.load(
            root / config["paths"]["bm25_index"], root / config["paths"]["bm25_metadata"]
        )
        self.dense = DenseStore.load(
            config["model"]["name"],
            root / config["paths"]["faiss_index"],
            root / config["paths"]["faiss_metadata"],
        )
        self.by_id = {chunk.chunk_id: i for i, chunk in enumerate(self.dense.chunks)}
        self.embeddings = np.load(root / config["paths"]["embeddings"])
        if torch.cuda.is_available() and self.dense.model.device.type != "cuda":
            raise RuntimeError("Dense model did not load on CUDA.")

    @staticmethod
    def build_query(query: str, history: list[dict[str, str]] | None, turns: int = 3) -> str:
        if not history:
            return query
        recent = history[-turns:]
        prefix = "\n".join(f"{item['role'].upper()}: {item['content']}" for item in recent)
        return f"{prefix}\nCURRENT QUESTION: {query}"

    def _attach_missing_scores(self, vector: np.ndarray, results: list[SearchResult]) -> list[SearchResult]:
        for result in results:
            index = self.by_id[result.chunk.chunk_id]
            result.semantic_score = float(self.embeddings[index] @ vector)
        return results

    def _retrieve(self, query: str, history: list[dict[str, str]] | None, vector: np.ndarray | None = None) -> tuple[
        list[SearchResult], list[SearchResult], float
    ]:
        built = self.build_query(query, history, self.config["query"]["history_turns"])
        bm25 = self.bm25.search(built, self.config["search"]["bm25_top_k"])
        dense = self.dense.search_vector(vector, self.config["search"]["dense_top_k"]) if vector is not None else self.dense.search(built, self.config["search"]["dense_top_k"])
        best_cosine = max((result.semantic_score or -1.0 for result in [*bm25, *dense]), default=-1.0)
        return bm25, dense, best_cosine

    def search_all(
        self, query: str, history: list[dict[str, str]] | None = None, vector: np.ndarray | None = None
    ) -> tuple[dict[str, list[SearchResult]], float]:
        """Retrieve all modes from one BM25/dense encoding pass."""
        bm25, dense, best_cosine = self._retrieve(query, history, vector)
        built = self.build_query(query, history, self.config["query"]["history_turns"])
        candidate_k = max(
            self.config["search"]["dense_top_k"], self.config["search"]["bm25_top_k"]
        )
        return {
            "bm25": self._attach_missing_scores(vector if vector is not None else self.dense.encode_query(built)[0], bm25[: self.config["search"]["final_top_k"]]),
            "semantic": dense[: self.config["search"]["final_top_k"]],
            "hybrid": hybrid(bm25, dense, self.config["search"]["rrf_k"], candidate_k),
        }, best_cosine

    def search(self, query: str, history: list[dict[str, str]] | None = None, mode: str = "hybrid") -> tuple[list[SearchResult], float]:
        systems, best_cosine = self.search_all(query, history)
        return systems[mode], best_cosine


def result_dicts(results: list[SearchResult]) -> list[dict[str, Any]]:
    return [result.as_dict() for result in results]
