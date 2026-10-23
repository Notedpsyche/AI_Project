"""Bounded term-frequency measures for the WMD experiment."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from .config import WmdConfig
from .preprocessing import WmdPreprocessor


@dataclass(frozen=True)
class TextMeasure:
    terms: tuple[str, ...]
    counts: tuple[int, ...]

    def masses(self) -> np.ndarray:
        total = sum(self.counts)
        if total <= 0:
            return np.empty(0, dtype=np.float64)
        return np.asarray(self.counts, dtype=np.float64) / float(total)

    def as_dict(self) -> dict:
        return {"terms": list(self.terms), "counts": list(self.counts)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> TextMeasure:
        terms = tuple(str(item) for item in value["terms"])
        counts = tuple(int(item) for item in value["counts"])
        if len(terms) != len(counts) or any(count <= 0 for count in counts):
            raise ValueError("Invalid WMD term-frequency measure")
        return cls(terms, counts)


def _measure(tokens: tuple[str, ...]) -> TextMeasure:
    counts = Counter(tokens)
    terms = tuple(sorted(counts))
    return TextMeasure(terms, tuple(counts[term] for term in terms))


def build_query_measure(text: str, preprocessor: WmdPreprocessor, config: WmdConfig) -> TextMeasure:
    return _measure(preprocessor.tokenize_terms(text)[: config.query_token_limit])


def build_document_measure(chunk: Mapping[str, object], preprocessor: WmdPreprocessor, config: WmdConfig) -> TextMeasure:
    title = preprocessor.tokenize_terms(str(chunk.get("title", "")))[: config.title_token_limit]
    heading_path = chunk.get("heading_path") or []
    leaf_heading = str(heading_path[-1]) if heading_path else str(chunk.get("title", ""))
    heading = preprocessor.tokenize_terms(leaf_heading)[: config.heading_token_limit]
    passage = preprocessor.tokenize_terms(str(chunk.get("text", "")))[: config.passage_token_limit]
    return _measure(title + heading + passage)


def collect_vocabulary(measures: Mapping[str, TextMeasure]) -> tuple[str, ...]:
    return tuple(sorted({term for measure in measures.values() for term in measure.terms}))
