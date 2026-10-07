import json
from pathlib import Path

import faiss
import numpy as np


def test_faiss_embedding_metadata_alignment() -> None:
    root = Path("indexes/faiss")
    index = faiss.read_index(str(root / "index.faiss"))
    embeddings = np.load(root / "embeddings.npy")
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert index.ntotal == len(metadata) == embeddings.shape[0]
    assert embeddings.shape[1] == 384
