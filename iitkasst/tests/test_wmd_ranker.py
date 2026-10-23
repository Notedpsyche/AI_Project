import hashlib
import json

import numpy as np
import pytest

from doc2dial_retrieval.wmd.cache import build_cache, load_cache
from doc2dial_retrieval.wmd.config import WmdConfig
from doc2dial_retrieval.wmd.encoder import EncodedWords
from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor
from doc2dial_retrieval.wmd.ranker import WmdReranker


class SemanticFakeEncoder:
    metadata = {
        "model_id": "fake-bert",
        "revision": "test-revision",
        "encoder_layer": 11,
        "selector": "encoder_layer_11_cls",
        "dimension": 768,
    }

    def encode_words(self, words: tuple[str, ...]) -> EncodedWords:
        vectors = np.zeros((len(words), 768), dtype=np.float32)
        coordinates = {"alpha": 0.0, "beta": 2.0, "gamma": 4.0}
        for index, word in enumerate(words):
            vectors[index, 0] = coordinates.get(word, 6.0)
            vectors[index, 1] = 1.0
            vectors[index] /= np.linalg.norm(vectors[index])
        return EncodedWords(words, vectors, ())


def _setup(tmp_path):
    config = WmdConfig("fake-bert", "test-revision", "cache", "chunks.jsonl", candidate_limit=2)
    chunks = [
        {"chunk_id": "beta", "title": "", "heading_path": [""], "text": "beta"},
        {"chunk_id": "alpha", "title": "", "heading_path": [""], "text": "alpha"},
    ]
    chunk_path = tmp_path / "chunks.jsonl"
    chunk_path.write_text("\n".join(json.dumps(chunk) for chunk in chunks), encoding="utf-8")
    preprocessor = WmdPreprocessor()
    target = tmp_path / "cache"
    encoder = SemanticFakeEncoder()
    build_cache(target, chunks, hashlib.sha256(chunk_path.read_bytes()).hexdigest(), config, preprocessor, encoder)
    return config, preprocessor, load_cache(target, chunk_path, config, preprocessor), encoder, chunks


def test_ranker_orders_ascending_distance_and_preserves_metadata(tmp_path) -> None:
    config, preprocessor, cache, encoder, candidates = _setup(tmp_path)
    ranked = WmdReranker(cache, config, preprocessor, encoder).rerank("alpha", [{**candidate, "source_url": f"https://example/{candidate['chunk_id']}"} for candidate in candidates])
    assert [row["chunk_id"] for row in ranked] == ["alpha", "beta"]
    assert ranked[0]["wmd_distance"] == pytest.approx(0.0)
    assert ranked[0]["source_url"] == "https://example/alpha"
    assert ranked[0]["wmd_rank"] == 1


def test_ranker_enforces_candidate_limit(tmp_path) -> None:
    config, preprocessor, cache, encoder, candidates = _setup(tmp_path)
    ranker = WmdReranker(cache, config, preprocessor, encoder)
    with pytest.raises(ValueError, match="candidate limit"):
        ranker.rerank("alpha", candidates, limit=3)
