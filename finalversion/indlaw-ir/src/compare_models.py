"""Compare BGE-small and BGE-base on the fixed validation queries."""

from __future__ import annotations

import json
from pathlib import Path

from doc2dial_retrieval.search import SearchEngine

ROOT = Path(__file__).resolve().parents[1]
QUERIES = (
    "How do I change my address with Social Security?",
    "What should I do if I need to report a complaint?",
)


def main() -> None:
    engines = {
        "bge_small": SearchEngine(ROOT),
        "bge_base": SearchEngine(ROOT, "configs/config_bge_base.yaml"),
    }
    comparison = {}
    for query in QUERIES:
        comparison[query] = {}
        for model_name, engine in engines.items():
            rows = {}
            for mode in ("semantic", "hybrid"):
                results, best_score = engine.search(query, mode=mode)
                rows[mode] = {
                    "best_semantic_cosine": best_score,
                    "results": [result.as_dict() for result in results],
                }
            comparison[query][model_name] = rows
    output = ROOT / "results/model_query_comparison.json"
    output.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
