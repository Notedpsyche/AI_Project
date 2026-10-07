"""Build reloadable BM25 and FAISS indexes from processed chunks."""

# Index construction keeps the model call and persisted-alignment fields together.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
import torch
import yaml
from sentence_transformers import SentenceTransformer

from doc2dial_retrieval.retrieval import DENSE_PREFIX, BM25Store, load_chunks

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--skip-bm25", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for BGE embedding generation on this machine.")
    chunks = load_chunks(ROOT / "data/processed/chunks.jsonl")
    if not args.skip_bm25:
        bm25 = BM25Store(chunks)
        bm25.save(ROOT / config["paths"]["bm25_index"], ROOT / config["paths"]["bm25_metadata"])
    model = SentenceTransformer(config["model"]["name"], device="cuda")
    texts = [" ".join([*chunk.heading_path, chunk.text]) for chunk in chunks]
    embeddings = model.encode(
        texts, batch_size=64, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True
    ).astype("float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss_path = ROOT / config["paths"]["faiss_index"]
    embeddings_path = ROOT / config["paths"]["embeddings"]
    metadata_path = ROOT / config["paths"]["faiss_metadata"]
    faiss_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(faiss_path))
    np.save(embeddings_path, embeddings)
    metadata_path.write_text(
        json.dumps([chunk.as_dict() for chunk in chunks], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "chunks": len(chunks),
        "dimensions": embeddings.shape[1],
        "model": config["model"]["name"],
        "device": str(model.device),
        "gpu": torch.cuda.get_device_name(0),
        "batch_size": 64,
        "prefix": DENSE_PREFIX,
    }, indent=2))


if __name__ == "__main__":
    main()
