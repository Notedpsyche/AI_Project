"""Build structure-aware Doc2Dial retrieval chunks."""

# Persist compact preprocessing statistics as one record.
# ruff: noqa: E501

import json
from pathlib import Path

from doc2dial_retrieval.data import build_chunks, write_chunks

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    chunks, stats = build_chunks(ROOT / "data/raw/doc2dial")
    write_chunks(chunks, ROOT / "data/processed/chunks.jsonl")
    (ROOT / "data/processed/chunk_stats.json").write_text(json.dumps({**stats, "chunks": len(chunks)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**stats, "chunks": len(chunks)}, indent=2))


if __name__ == "__main__":
    main()
