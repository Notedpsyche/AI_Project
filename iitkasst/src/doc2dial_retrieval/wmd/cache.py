"""Versioned, validated on-disk cache for BERT WMD vocabulary vectors."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .config import WmdConfig
from .preprocessing import WmdPreprocessor
from .representation import TextMeasure, build_document_measure, collect_vocabulary


class WordEncoder(Protocol):
    @property
    def metadata(self) -> dict[str, object]: ...

    def encode_words(self, words: tuple[str, ...]): ...


@dataclass(frozen=True)
class CacheManifest:
    schema_version: int
    corpus_sha256: str
    config_fingerprint: str
    preprocessing_fingerprint: str
    model_id: str
    revision: str
    encoder_layer: int
    selector: str
    dimension: int
    dtype: str
    vocabulary_size: int
    document_count: int

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CacheManifest:
        return cls(**{key: value[key] for key in cls.__annotations__})


@dataclass
class EmbeddingCache:
    root: Path
    manifest: CacheManifest
    vocabulary: tuple[str, ...]
    vectors: np.ndarray
    documents: dict[str, TextMeasure]

    def vectors_for(self, terms: tuple[str, ...]) -> tuple[tuple[str, ...], np.ndarray, tuple[str, ...]]:
        index = {word: number for number, word in enumerate(self.vocabulary)}
        found = tuple(term for term in terms if term in index)
        missing = tuple(term for term in terms if term not in index)
        rows = np.asarray([index[term] for term in found], dtype=np.intp)
        return found, np.asarray(self.vectors[rows], dtype=np.float32), missing


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_cache(
    target: Path,
    chunks: list[Mapping[str, object]],
    corpus_sha256: str,
    config: WmdConfig,
    preprocessor: WmdPreprocessor,
    encoder: WordEncoder,
) -> CacheManifest:
    if target.exists():
        raise FileExistsError(f"WMD cache already exists at {target}; remove only that exact cache directory before rebuilding")
    documents = {str(chunk["chunk_id"]): build_document_measure(chunk, preprocessor, config) for chunk in chunks}
    vocabulary = collect_vocabulary(documents)
    encoded = encoder.encode_words(vocabulary)
    retained = tuple(encoded.words)
    retained_index = {word: index for index, word in enumerate(retained)}
    if encoded.vectors.shape != (len(retained), 768):
        raise ValueError("WMD encoder returned an unexpected vocabulary matrix shape")
    documents = {
        chunk_id: TextMeasure(
            tuple(term for term in measure.terms if term in retained_index),
            tuple(count for term, count in zip(measure.terms, measure.counts) if term in retained_index),
        )
        for chunk_id, measure in documents.items()
    }
    documents = {chunk_id: measure for chunk_id, measure in documents.items() if measure.terms}
    metadata = encoder.metadata
    manifest = CacheManifest(
        schema_version=1,
        corpus_sha256=corpus_sha256,
        config_fingerprint=config.fingerprint(),
        preprocessing_fingerprint=preprocessor.fingerprint(),
        model_id=str(metadata["model_id"]),
        revision=str(metadata["revision"]),
        encoder_layer=int(metadata["encoder_layer"]),
        selector=str(metadata["selector"]),
        dimension=int(metadata["dimension"]),
        dtype="float32",
        vocabulary_size=len(retained),
        document_count=len(documents),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".wmd-build-", dir=target.parent))
    try:
        (staging / "vocabulary.json").write_text(json.dumps(retained, ensure_ascii=False), encoding="utf-8")
        np.save(staging / "embeddings.npy", encoded.vectors.astype(np.float32, copy=False))
        (staging / "documents.json").write_text(
            json.dumps({chunk_id: measure.as_dict() for chunk_id, measure in documents.items()}, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        (staging / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def load_cache(
    target: Path,
    chunks_path: Path,
    config: WmdConfig,
    preprocessor: WmdPreprocessor,
) -> EmbeddingCache:
    required = [target / name for name in ("vocabulary.json", "embeddings.npy", "documents.json", "manifest.json")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("WMD cache is missing. Run 'uv run python src/build_wmd_cache.py'. Missing: " + ", ".join(missing))
    manifest = CacheManifest.from_dict(json.loads((target / "manifest.json").read_text(encoding="utf-8")))
    expected = {
        "corpus_sha256": _sha256(chunks_path),
        "config_fingerprint": config.fingerprint(),
        "preprocessing_fingerprint": preprocessor.fingerprint(),
        "model_id": config.model_id,
        "revision": config.revision,
        "encoder_layer": config.encoder_layer,
        "selector": "encoder_layer_11_cls",
        "dimension": 768,
        "dtype": "float32",
    }
    for field, value in expected.items():
        if getattr(manifest, field) != value:
            raise ValueError(f"WMD cache {field} mismatch; rebuild the WMD cache")
    vocabulary = tuple(json.loads((target / "vocabulary.json").read_text(encoding="utf-8")))
    vectors = np.load(target / "embeddings.npy", mmap_mode="r")
    if vectors.shape != (len(vocabulary), 768) or vectors.dtype != np.float32:
        raise ValueError("WMD cache vocabulary/vector alignment is invalid")
    if manifest.vocabulary_size != len(vocabulary):
        raise ValueError("WMD cache manifest vocabulary count mismatch")
    raw_documents = json.loads((target / "documents.json").read_text(encoding="utf-8"))
    documents = {chunk_id: TextMeasure.from_dict(value) for chunk_id, value in raw_documents.items()}
    if manifest.document_count != len(documents):
        raise ValueError("WMD cache manifest document count mismatch")
    return EmbeddingCache(target, manifest, vocabulary, vectors, documents)
