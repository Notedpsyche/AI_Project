import numpy as np
import pytest

from doc2dial_retrieval.wmd.config import load_wmd_config
from doc2dial_retrieval.wmd.encoder import BertWordEncoder


@pytest.mark.model
def test_pinned_bert_word_encoder_returns_normalized_layer_vectors() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config = load_wmd_config(root)
    encoded = BertWordEncoder(config, device="cpu", local_files_only=True).encode_words(("btech", "tuition", "2026"))
    assert encoded.words == ("btech", "tuition", "2026")
    assert encoded.vectors.shape == (3, 768)
    assert np.allclose(np.linalg.norm(encoded.vectors, axis=1), 1.0, atol=1e-5)
    assert not encoded.rejected
