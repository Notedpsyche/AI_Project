"""Collect the allowlisted IIIT Kottayam sources and prepare local chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from doc2dial_retrieval.college import build_college_chunks, collect_sources
from doc2dial_retrieval.data import write_chunks

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "prepare", "all"])
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    raw_dir = ROOT / config["paths"]["raw_dir"]
    if args.action in {"collect", "all"}:
        inventory = collect_sources(ROOT / "configs/college_sources.json", raw_dir)
        print(f"Collected {len(inventory)} allowlisted sources locally")
    if args.action in {"prepare", "all"}:
        chunks = build_college_chunks(raw_dir)
        write_chunks(chunks, ROOT / config["paths"]["chunks"])
        print(json.dumps({"sources": len({chunk.doc_id for chunk in chunks}), "chunks": len(chunks)}, indent=2))


if __name__ == "__main__":
    main()
