"""Emit an inspectable end-to-end retrieval trace for applicant questions."""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.college_answer import grounded_answer
from backend.services.college_query import eligible, normalized_terms, resolve_scope
from backend.services.college_select import select_evidence
from doc2dial_retrieval.search import SearchEngine, result_dicts

def _row(row: dict, scope=None) -> dict:
    return {
        "rank": row.get("rank"),
        "chunk_id": row["chunk_id"],
        "title": row["title"],
        "section": (row.get("heading_path") or [row["title"]])[-1],
        "source_url": row.get("source_url", ""),
        "programme": row.get("programme", ""),
        "admission_year": row.get("admission_year"),
        "topics": row.get("topics", []),
        "bm25_score": row.get("bm25_score"),
        "bm25_rank": row.get("bm25_rank"),
        "semantic_score": row.get("semantic_score"),
        "semantic_rank": row.get("semantic_rank"),
        "rrf_score": row.get("rrf_score"),
        "final_evidence_score": row.get("final_evidence_score"),
        "eligible": eligible(row, scope) if scope else None,
        "text": row["text"],
    }


def trace(engine: SearchEngine, query: str) -> dict:
    scope = resolve_scope(query, [])
    original_cutoff = engine.config["search"]["final_top_k"]
    engine.config["search"]["final_top_k"] = 10
    try:
        systems, best = engine.search_all(query)
    finally:
        engine.config["search"]["final_top_k"] = original_cutoff
    mode_rows = {name: result_dicts(rows[:10]) for name, rows in systems.items()}
    candidates = result_dicts(systems["hybrid"])
    for row in candidates:
        row["section"] = row["heading_path"][-1] if row["heading_path"] else row["title"]
        row["span_id"] = ""
    evidence = select_evidence(scope, candidates, top_k=3)
    for rank, row in enumerate(evidence, 1):
        row["rank"] = rank
    answer, refused = grounded_answer(scope, evidence)
    return {
        "query": query,
        "normalized_query": query.strip(),
        "normalized_terms": sorted(normalized_terms(query)),
        "scope": asdict(scope),
        "best_dense_score": best,
        "bm25_top_10": [_row(row, scope) for row in mode_rows["bm25"]],
        "dense_top_10": [_row(row, scope) for row in mode_rows["semantic"]],
        "rrf_top_10": [_row(row, scope) for row in mode_rows["hybrid"][:10]],
        "eligible_rrf_top_10": [row["chunk_id"] for row in mode_rows["hybrid"][:10] if eligible(row, scope)],
        "selected_evidence": [_row(row, scope) for row in evidence],
        "answer": answer,
        "refused": refused,
        "abstention_reason": answer if refused else "",
        "reranker_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queries", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    engine = SearchEngine(ROOT)
    payload = [trace(engine, query) for query in args.queries]
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
