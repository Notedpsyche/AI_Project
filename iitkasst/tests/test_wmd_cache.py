import json

import numpy as np
import pytest

from doc2dial_retrieval.wmd.cache import build_cache, load_cache
from doc2dial_retrieval.wmd.config import WmdConfig
from doc2dial_retrieval.wmd.encoder import EncodedWords
from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor


class FakeEncoder:
    metadata = {
        "model_id": "fake-bert",
        "revision": "test-revision",
        "encoder_layer": 11,
        "selector": "encoder_layer_11_cls",
        "dimension": 768,
    }

    def encode_words(self, words: tuple[str, ...]) -> EncodedWords:
        vectors = np.zeros((len(words), 768), dtype=np.float32)
        for index, word in enumerate(words):
            vectors[index, index % 768] = 1.0
        return EncodedWords(words, vectors, ())


def config() -> WmdConfig:
    return WmdConfig("fake-bert", "test-revision", "cache", "chunks.jsonl")


def chunks() -> list[dict]:
    return [
        {"chunk_id": "one", "title": "B.Tech", "heading_path": ["Fees"], "text": "Tuition fee 2026"},
        {"chunk_id": "two", "title": "PhD", "heading_path": ["Eligibility"], "text": "Qualification requirement"},
    ]


def test_cache_round_trip_and_vector_alignment(tmp_path) -> None:
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(chunk) for chunk in chunks()), encoding="utf-8")
    target = tmp_path / "cache"
    preprocessor = WmdPreprocessor()
    manifest = build_cache(target, chunks(), __import__("hashlib").sha256(path.read_bytes()).hexdigest(), config(), preprocessor, FakeEncoder())
    loaded = load_cache(target, path, config(), preprocessor)
    assert manifest.vocabulary_size == len(loaded.vocabulary)
    assert loaded.vectors.shape == (len(loaded.vocabulary), 768)
    found, vectors, missing = loaded.vectors_for(("tuition", "missing"))
    assert found == ("tuition",)
    assert vectors.shape == (1, 768)
    assert missing == ("missing",)


def test_cache_rejects_manifest_configuration_mismatch(tmp_path) -> None:
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(chunk) for chunk in chunks()), encoding="utf-8")
    target = tmp_path / "cache"
    preprocessor = WmdPreprocessor()
    build_cache(target, chunks(), __import__("hashlib").sha256(path.read_bytes()).hexdigest(), config(), preprocessor, FakeEncoder())
    changed = WmdConfig("fake-bert", "test-revision", "cache", "chunks.jsonl", query_token_limit=8)
    with pytest.raises(ValueError, match="config_fingerprint mismatch"):
        load_cache(target, path, changed, preprocessor)


def test_cache_build_never_overwrites_existing_artifact(tmp_path) -> None:
    target = tmp_path / "cache"
    target.mkdir()
    with pytest.raises(FileExistsError):
        build_cache(target, chunks(), "hash", config(), WmdPreprocessor(), FakeEncoder())
