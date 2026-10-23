"""Compare existing BM25/BGE/RRF retrieval with exact BERT + WMD reranking."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _view(row: dict) -> dict:
    return {
        key: row.get(key)
        for key in (
            "chunk_id", "title", "section", "source_url", "programme", "admission_year", "rrf_score",
            "semantic_score", "bm25_score", "original_rrf_rank", "centroid_rank", "centroid_cosine",
            "centroid_status", "wmd_rank", "wmd_distance", "wmd_status", "wmd_elapsed_ms",
            "bm25_wmd_rrf_rank", "bm25_wmd_rrf_score",
        )
    }


def main() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from backend.services.college_query import eligible, resolve_scope
    from doc2dial_retrieval.search import SearchEngine, result_dicts
    from doc2dial_retrieval.wmd.cache import load_cache
    from doc2dial_retrieval.wmd.config import load_wmd_config
    from doc2dial_retrieval.wmd.encoder import BertWordEncoder
    from doc2dial_retrieval.wmd.fusion import rank_fuse_bm25_wmd
    from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor
    from doc2dial_retrieval.wmd.ranker import WmdReranker

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--config", default="configs/wmd_experiment.yaml")
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args()
    started = time.perf_counter()
    config = load_wmd_config(ROOT, args.config)
    preprocessor = WmdPreprocessor(version=config.preprocessing_version)
    scope = resolve_scope(args.query, [])
    engine = SearchEngine(ROOT)
    systems, _ = engine.search_all(args.query)
    baseline = {name: result_dicts(rows) for name, rows in systems.items()}
    for rows in baseline.values():
        for row in rows:
            row["section"] = row["heading_path"][-1] if row.get("heading_path") else row.get("title", "")
    hybrid = baseline["hybrid"]
    for row in hybrid:
        row["section"] = row["heading_path"][-1] if row.get("heading_path") else row.get("title", "")
    eligible_candidates = [row for row in hybrid if eligible(row, scope)]
    eligible_bm25 = [row for row in baseline["bm25"] if eligible(row, scope)]
    cache = load_cache(ROOT / config.cache_dir, ROOT / config.chunks_path, config, preprocessor)
    ranker = WmdReranker(cache, config, preprocessor, BertWordEncoder(config))
    wmd_started = time.perf_counter()
    centroid = ranker.rerank_centroid(scope.query, eligible_candidates)
    reranked = ranker.rerank(scope.query, eligible_candidates)
    fused = rank_fuse_bm25_wmd(eligible_bm25[: config.candidate_limit], reranked)
    payload = {
        "query": args.query,
        "effective_query": scope.query,
        "scope": {
            "topic": scope.topic,
            "intent": scope.intent,
            "programmes": list(scope.programmes),
            "admission_year": scope.admission_year,
        },
        "baseline": {name: [_view(row) for row in rows[: args.top]] for name, rows in baseline.items()},
        "eligible_rrf_candidates": len(eligible_candidates),
        "centroid_reranked": [_view(row) for row in centroid[: args.top]],
        "wmd_reranked": [_view(row) for row in reranked[: args.top]],
        "bm25_wmd_rank_fused": [_view(row) for row in fused[: args.top]],
        "timing_ms": {
            "wmd": round((time.perf_counter() - wmd_started) * 1000, 3),
            "total": round((time.perf_counter() - started) * 1000, 3),
        },
        "cache": {
            "corpus_sha256": cache.manifest.corpus_sha256,
            "model": f"{cache.manifest.model_id}@{cache.manifest.revision}",
            "vocabulary_size": cache.manifest.vocabulary_size,
        },
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    print(rendered)
    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
