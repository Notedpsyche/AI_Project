"""Command-line search over the Doc2Dial prototype indexes."""

# ruff: noqa: E501

import argparse
import json
from pathlib import Path

from doc2dial_retrieval.search import SearchEngine, result_dicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--mode", choices=("bm25", "semantic", "hybrid"), default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    engine = SearchEngine(Path(__file__).resolve().parents[1])
    results, best = engine.search(args.query, mode=args.mode)
    threshold = engine.config["retrieval"]["semantic_threshold"]
    print(json.dumps({"query": args.query, "mode": args.mode, "best_semantic_cosine": best, "refused": threshold is not None and best < threshold, "results": result_dicts(results[: args.top_k])}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
