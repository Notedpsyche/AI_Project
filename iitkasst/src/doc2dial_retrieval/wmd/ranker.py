"""Bounded exact-WMD reranking over existing retrieval candidates."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Mapping

import numpy as np

from .cache import EmbeddingCache
from .config import WmdConfig
from .distance import WmdError, exact_wmd, weighted_centroid_cosine
from .encoder import BertWordEncoder
from .preprocessing import WmdPreprocessor
from .representation import TextMeasure, build_document_measure, build_query_measure


class WmdReranker:
    def __init__(self, cache: EmbeddingCache, config: WmdConfig, preprocessor: WmdPreprocessor, encoder: BertWordEncoder):
        self.cache = cache
        self.config = config
        self.preprocessor = preprocessor
        self.encoder = encoder
        self._query_lru: OrderedDict[str, np.ndarray] = OrderedDict()

    def _vectors_for_measure(self, measure: TextMeasure) -> tuple[np.ndarray, np.ndarray]:
        found, vectors, missing = self.cache.vectors_for(measure.terms)
        if missing:
            encoded = self.encoder.encode_words(missing)
            for word, vector in zip(encoded.words, encoded.vectors):
                self._query_lru[word] = vector
                self._query_lru.move_to_end(word)
            while len(self._query_lru) > 256:
                self._query_lru.popitem(last=False)
        lookup = {word: vector for word, vector in zip(found, vectors)}
        lookup.update(self._query_lru)
        kept = [(term, count) for term, count in zip(measure.terms, measure.counts) if term in lookup]
        if not kept:
            raise WmdError("No cached or encodable WMD terms remain")
        masses = np.asarray([count for _, count in kept], dtype=np.float64)
        masses /= masses.sum()
        return masses, np.asarray([lookup[term] for term, _ in kept], dtype=np.float32)

    def rerank(self, query: str, candidates: list[Mapping[str, object]], limit: int | None = None) -> list[dict]:
        requested = self.config.candidate_limit if limit is None else limit
        if requested < 1 or requested > self.config.candidate_limit:
            raise ValueError(f"WMD candidate limit must be between 1 and {self.config.candidate_limit}")
        query_measure = build_query_measure(query, self.preprocessor, self.config)
        query_masses, query_vectors = self._vectors_for_measure(query_measure)
        ranked: list[dict] = []
        for original_rank, candidate in enumerate(candidates[:requested], 1):
            row = dict(candidate)
            started = time.perf_counter()
            try:
                chunk_id = str(row["chunk_id"])
                document = self.cache.documents.get(chunk_id)
                if document is None:
                    document = build_document_measure(row, self.preprocessor, self.config)
                document_masses, document_vectors = self._vectors_for_measure(document)
                row["wmd_distance"] = exact_wmd(query_masses, query_vectors, document_masses, document_vectors)
                row["wmd_status"] = "ok"
            except (KeyError, WmdError, ValueError) as error:
                row["wmd_distance"] = None
                row["wmd_status"] = f"error: {error}"
            row["wmd_elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
            row["original_rrf_rank"] = original_rank
            ranked.append(row)
        ranked.sort(
            key=lambda row: (
                row["wmd_distance"] is None,
                float(row["wmd_distance"]) if row["wmd_distance"] is not None else float("inf"),
                row["original_rrf_rank"],
                str(row.get("chunk_id", "")),
            )
        )
        for rank, row in enumerate(ranked, 1):
            row["wmd_rank"] = rank
        return ranked

    def rerank_centroid(self, query: str, candidates: list[Mapping[str, object]], limit: int | None = None) -> list[dict]:
        """Rank the same candidate pool by weighted-centroid cosine."""
        requested = self.config.candidate_limit if limit is None else limit
        if requested < 1 or requested > self.config.candidate_limit:
            raise ValueError(f"WMD candidate limit must be between 1 and {self.config.candidate_limit}")
        query_masses, query_vectors = self._vectors_for_measure(build_query_measure(query, self.preprocessor, self.config))
        ranked: list[dict] = []
        for original_rank, candidate in enumerate(candidates[:requested], 1):
            row = dict(candidate)
            try:
                document = self.cache.documents.get(str(row["chunk_id"])) or build_document_measure(row, self.preprocessor, self.config)
                document_masses, document_vectors = self._vectors_for_measure(document)
                row["centroid_cosine"] = weighted_centroid_cosine(query_masses, query_vectors, document_masses, document_vectors)
                row["centroid_status"] = "ok"
            except (KeyError, WmdError, ValueError) as error:
                row["centroid_cosine"] = None
                row["centroid_status"] = f"error: {error}"
            row["original_rrf_rank"] = original_rank
            ranked.append(row)
        ranked.sort(
            key=lambda row: (
                row["centroid_cosine"] is None,
                -float(row["centroid_cosine"]) if row["centroid_cosine"] is not None else float("inf"),
                row["original_rrf_rank"],
            )
        )
        for rank, row in enumerate(ranked, 1):
            row["centroid_rank"] = rank
        return ranked
