"""Build the local, versioned BERT vocabulary cache for the WMD experiment."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from doc2dial_retrieval.retrieval import load_chunks
from doc2dial_retrieval.wmd.cache import build_cache
from doc2dial_retrieval.wmd.config import load_wmd_config
from doc2dial_retrieval.wmd.encoder import BertWordEncoder
from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/wmd_experiment.yaml")
    args = parser.parse_args()
    config = load_wmd_config(ROOT, args.config)
    chunks_path = ROOT / config.chunks_path
    chunks = [chunk.as_dict() for chunk in load_chunks(chunks_path)]
    target = ROOT / config.cache_dir
    manifest = build_cache(
        target,
        chunks,
        hashlib.sha256(chunks_path.read_bytes()).hexdigest(),
        config,
        WmdPreprocessor(version=config.preprocessing_version),
        BertWordEncoder(config),
    )
    print(
        {
            "cache_dir": str(target),
            "vocabulary_size": manifest.vocabulary_size,
            "document_count": manifest.document_count,
            "corpus_sha256": manifest.corpus_sha256,
            "model": f"{manifest.model_id}@{manifest.revision}",
        }
    )


if __name__ == "__main__":
    main()
