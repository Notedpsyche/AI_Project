import json
from pathlib import Path

import faiss
import numpy as np
import pytest
import yaml


def test_faiss_embedding_metadata_alignment() -> None:
    config = yaml.safe_load(Path("configs/config.yaml").read_text(encoding="utf-8"))
    paths = config["paths"]
    index_path = Path(paths["faiss_index"])
    if not index_path.exists():
        pytest.skip("Local-only college index has not been built")
    index = faiss.read_index(str(index_path))
    embeddings = np.load(paths["embeddings"])
    metadata = json.loads(Path(paths["faiss_metadata"]).read_text(encoding="utf-8"))
    assert index.ntotal == len(metadata) == embeddings.shape[0]
    assert embeddings.shape[1] == index.d
