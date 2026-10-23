"""Evaluate shared-pool BERT centroid/WMD reranking on reviewed questions."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def reciprocal_rank(rows: Iterable[dict], gold: set[str], limit: int = 10) -> float:
    for rank, row in enumerate(list(rows)[:limit], 1):
        if str(row["chunk_id"]) in gold:
            return 1.0 / rank
    return 0.0


def recall(rows: Iterable[dict], gold: set[str], limit: int) -> float:
    if not gold:
        return 0.0
    return len({str(row["chunk_id"]) for row in list(rows)[:limit]} & gold) / len(gold)


def ndcg(rows: Iterable[dict], relevance: dict[str, int], limit: int = 10) -> float:
    ranked = list(rows)[:limit]
    dcg = sum(
        (2 ** relevance.get(str(row["chunk_id"]), 0) - 1) / math.log2(rank + 1)
        for rank, row in enumerate(ranked, 1)
    )
    ideal = sorted(relevance.values(), reverse=True)[:limit]
    idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def main() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from backend.services.college_query import eligible, resolve_scope
    from doc2dial_retrieval.retrieval import hybrid
    from doc2dial_retrieval.search import SearchEngine, result_dicts
    from doc2dial_retrieval.wmd.cache import load_cache
    from doc2dial_retrieval.wmd.config import load_wmd_config
    from doc2dial_retrieval.wmd.encoder import BertWordEncoder
    from doc2dial_retrieval.wmd.fusion import rank_fuse_bm25_wmd
    from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor
    from doc2dial_retrieval.wmd.ranker import WmdReranker

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--config", default="configs/wmd_experiment.yaml")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = [
        json.loads(line)
        for line in Path(args.questions).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pending = [case["id"] for case in cases if case.get("review_status") != "reviewed"]
    if pending:
        raise ValueError("WMD evaluation requires human-reviewed cases; pending: " + ", ".join(pending))
    config = load_wmd_config(ROOT, args.config)
    preprocessor = WmdPreprocessor(version=config.preprocessing_version)
    cache = load_cache(ROOT / config.cache_dir, ROOT / config.chunks_path, config, preprocessor)
    ranker = WmdReranker(cache, config, preprocessor, BertWordEncoder(config))
    engine = SearchEngine(ROOT)
    outcomes = []
    for case in cases:
        query = str(case["query"])
        scope = resolve_scope(query, [])
        started = time.perf_counter()
        built = engine.build_query(query, None, engine.config["query"]["history_turns"])
        bm25_results = engine.bm25.search(built, 50)
        dense_results = engine.dense.search(built, 50)
        systems = {
            "bm25": bm25_results,
            "semantic": dense_results,
            "hybrid": hybrid(bm25_results, dense_results, engine.config["search"]["rrf_k"], 50),
        }
        rankings = {name: result_dicts(rows) for name, rows in systems.items()}
        for rows in rankings.values():
            for row in rows:
                row["section"] = row["heading_path"][-1] if row.get("heading_path") else row.get("title", "")
        rankings = {name: [row for row in rows if eligible(row, scope)] for name, rows in rankings.items()}
        hybrid_rows = rankings["hybrid"]
        for row in hybrid_rows:
            row["section"] = row["heading_path"][-1] if row.get("heading_path") else row.get("title", "")
        eligible_pool = hybrid_rows[: config.candidate_limit]
        centroid = ranker.rerank_centroid(scope.query, eligible_pool)
        wmd = ranker.rerank(scope.query, eligible_pool)
        bm25 = rankings["bm25"]
        fusion = rank_fuse_bm25_wmd(bm25[: config.candidate_limit], wmd)
        gold = set(case.get("gold_chunk_ids", []))
        relevance = {str(chunk_id): int(grade) for chunk_id, grade in case.get("gold_relevance", {}).items()}
        relevance.update({chunk_id: relevance.get(chunk_id, 1) for chunk_id in gold})
        ranked_systems = {
            "bm25": bm25,
            "bge": rankings["semantic"],
            "rrf": hybrid_rows,
            "centroid": centroid,
            "wmd": wmd,
            "bm25_wmd_rrf": fusion,
        }
        outcomes.append(
            {
                "id": case["id"],
                "query": query,
                "gold_chunk_ids": sorted(gold),
                "rankings": ranked_systems,
                "metrics": {
                    name: {
                        "recall_at_5": recall(rows, gold, 5),
                        "recall_at_10": recall(rows, gold, 10),
                        "mrr_at_10": reciprocal_rank(rows, gold),
                        "ndcg_at_10": ndcg(rows, relevance),
                    }
                    for name, rows in ranked_systems.items()
                },
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw_results.json").write_text(json.dumps(outcomes, indent=2, ensure_ascii=False), encoding="utf-8")
    print({"cases": len(outcomes), "output": str(output / "raw_results.json")})


if __name__ == "__main__":
    main()
