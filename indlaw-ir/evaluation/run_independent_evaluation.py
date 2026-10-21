"""Run the frozen agent-authored audit set without changing the application.

User-visible answers come from the live FastAPI /api/chat endpoint. A local,
read-only SearchEngine instance mirrors the backend retrieval call so that the
BM25, dense, RRF, and evidence-selection stages can be inspected.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.college_query import eligible, resolve_scope  # noqa: E402
from backend.services.college_select import select_evidence  # noqa: E402
from doc2dial_retrieval.search import SearchEngine, result_dicts  # noqa: E402

DATASET = ROOT / "evaluation/independent_questions.jsonl"
EXPECTED_DATASET_SHA256 = "4d849f726481afc11950465a2bb9981b72b63562719b8fe8f54c3a94e8dcb60a"
OUTPUT = ROOT / "results/college/independent_evaluation.json"
API_LOG = ROOT / "results/college/independent_evaluation_api.jsonl"
BASE_URL = "http://127.0.0.1:8000"


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def row_view(row: dict, scope=None) -> dict:
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


def call_api(case: dict) -> tuple[dict, float]:
    payload = json.dumps({"message": case["query"], "conversation": case["history"]}).encode()
    request = Request(
        BASE_URL + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=60) as response:
        result = json.load(response)
    return result, (time.perf_counter() - started) * 1000


def citation_supported(answer: str, evidence: list[dict]) -> tuple[bool, list[dict]]:
    claims = re.findall(r"•\s*(.*?)\s*\[(\d+)\]", answer, re.S)
    if not claims:
        return False, [{"reason": "No claim-level citations were found."}]
    by_rank = {int(row["rank"]): row for row in evidence}
    checks = []
    valid = True
    for claim, rank_text in claims:
        rank = int(rank_text)
        row = by_rank.get(rank)
        support = "" if row is None else f"{row.get('section', '')} {row.get('text', '')}"
        supported = row is not None and compact(claim) in compact(support)
        valid = valid and supported
        checks.append(
            {
                "citation_rank": rank,
                "claim": claim,
                "chunk_id": row.get("chunk_id") if row else None,
                "supported": supported,
            }
        )
    return valid, checks


def retrieval_metrics(ranked_ids: list[str], evidence: list[dict]) -> dict | None:
    if not evidence:
        return None
    grades = {item["chunk_id"]: int(item["grade"]) for item in evidence}
    relevant = set(grades)

    def recall_at(k: int) -> float:
        return len(relevant.intersection(ranked_ids[:k])) / len(relevant)

    first = next((rank for rank, chunk_id in enumerate(ranked_ids[:10], 1) if chunk_id in relevant), None)
    dcg = sum((2 ** grades.get(chunk_id, 0) - 1) / math.log2(rank + 1) for rank, chunk_id in enumerate(ranked_ids[:10], 1))
    ideal = sorted(grades.values(), reverse=True)[:10]
    idcg = sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
    return {
        "recall_at_5": recall_at(5),
        "recall_at_10": recall_at(10),
        "mrr_at_10": 0.0 if first is None else 1.0 / first,
        "ndcg_at_10": 0.0 if idcg == 0 else dcg / idcg,
    }


def classify(case: dict, api: dict, selected: list[dict]) -> dict:
    answer = api["answer"]
    folded = answer.casefold()
    matched = [fact for fact in case["required_facts"] if fact.casefold() in folded]
    missing = [fact for fact in case["required_facts"] if fact.casefold() not in folded]
    forbidden = [fact for fact in case["forbidden_facts"] if fact.casefold() in folded]
    citation_ok, citation_checks = citation_supported(answer, selected) if not api["refused"] else (True, [])
    completeness = 1.0 if not case["required_facts"] else len(matched) / len(case["required_facts"])
    expects_answer = case["expected_behavior"] == "answer"
    if not expects_answer:
        label = "correct_abstention" if api["refused"] else "unsupported_or_hallucinated"
    elif api["refused"]:
        label = "unnecessary_abstention"
    elif forbidden:
        label = "partially_correct" if matched else "incorrect"
    elif not citation_ok:
        label = "unsupported_or_hallucinated"
    elif not missing:
        label = "correct_and_complete"
    elif matched:
        label = "correct_but_incomplete"
    else:
        label = "incorrect"
    return {
        "classification": label,
        "matched_required_facts": matched,
        "missing_required_facts": missing,
        "forbidden_facts_present": forbidden,
        "answer_completeness": completeness,
        "citation_supported": citation_ok,
        "citation_checks": citation_checks,
    }


def main() -> None:
    dataset_sha = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    if dataset_sha != EXPECTED_DATASET_SHA256:
        raise SystemExit(f"Frozen dataset hash changed: {dataset_sha}")
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]
    engine = SearchEngine(ROOT)
    original_cutoff = engine.config["search"]["final_top_k"]
    engine.config["search"]["final_top_k"] = 10
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    API_LOG.write_text("", encoding="utf-8")
    try:
        for index, case in enumerate(cases, 1):
            api, latency_ms = call_api(case)
            with API_LOG.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"case_id": case["case_id"], "latency_ms": latency_ms, "response": api}, ensure_ascii=False) + "\n")
            scope = resolve_scope(case["query"], case["history"])
            previous = next((item["content"] for item in reversed(case["history"][-6:]) if item.get("role") == "user"), "")
            retrieval_history = [{"role": "user", "content": previous}] if scope.use_context else []
            systems, best = engine.search_all(case["query"], retrieval_history)
            mode_rows = {name: result_dicts(items[:10]) for name, items in systems.items()}
            fused = result_dicts(systems["hybrid"])
            for item in fused:
                item["section"] = item["heading_path"][-1] if item["heading_path"] else item["title"]
                item["span_id"] = ""
            selected = select_evidence(scope, fused, top_k=3)
            for rank, item in enumerate(selected, 1):
                item["rank"] = rank
            assessment = classify(case, api, selected)
            ranked_ids = [item["chunk_id"] for item in fused]
            rows.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "conversation_type": case["conversation_type"],
                    "query": case["query"],
                    "history": case["history"],
                    "expected_behavior": case["expected_behavior"],
                    "expected_answer": case["expected_answer"],
                    "answerable_from_current_corpus": case["answerable_from_current_corpus"],
                    "actual_answer": api["answer"],
                    "refused": api["refused"],
                    "api_latency_ms": round(latency_ms, 3),
                    "api_context": {
                        "used": api["context_used"],
                        "decision": api["context_decision"],
                        "reason": api["context_reason"],
                        "debug": api.get("debug"),
                    },
                    "resolved_scope": {
                        "query": scope.query,
                        "topic": scope.topic,
                        "intent": scope.intent,
                        "programme": scope.programme,
                        "admission_year": scope.admission_year,
                        "admission_route": scope.admission_route,
                        "requires_route": scope.requires_route,
                    },
                    "best_dense_score": best,
                    "bm25_top_10": [row_view(item, scope) for item in mode_rows["bm25"]],
                    "dense_top_10": [row_view(item, scope) for item in mode_rows["semantic"]],
                    "rrf_top_10": [row_view(item, scope) for item in mode_rows["hybrid"]],
                    "selected_evidence": [row_view(item, scope) for item in selected],
                    "api_cited_evidence": api["evidence"],
                    "retrieval_metrics": retrieval_metrics(ranked_ids, case["relevant_evidence"]),
                    **assessment,
                }
            )
            print(f"{index:02d}/{len(cases)} {case['case_id']} {assessment['classification']} {latency_ms:.1f} ms", flush=True)
    finally:
        engine.config["search"]["final_top_k"] = original_cutoff

    latencies = [row["api_latency_ms"] for row in rows]
    answerable = [row for row in rows if row["answerable_from_current_corpus"]]
    unanswerable = [row for row in rows if not row["answerable_from_current_corpus"]]
    actually_answered = [row for row in rows if not row["refused"]]
    retrieval_rows = [row for row in rows if row["retrieval_metrics"] is not None]
    category_rows: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        category_rows[row["category"]].append(row)

    def subset_summary(items: list[dict]) -> dict:
        return {
            "cases": len(items),
            "correct_and_complete": sum(row["classification"] == "correct_and_complete" for row in items),
            "correct_but_incomplete": sum(row["classification"] == "correct_but_incomplete" for row in items),
            "partially_correct": sum(row["classification"] == "partially_correct" for row in items),
            "incorrect": sum(row["classification"] == "incorrect" for row in items),
            "unsupported_or_hallucinated": sum(row["classification"] == "unsupported_or_hallucinated" for row in items),
            "unnecessary_abstention": sum(row["classification"] == "unnecessary_abstention" for row in items),
            "correct_abstention": sum(row["classification"] == "correct_abstention" for row in items),
        }

    strict_correct = sum(row["classification"] in {"correct_and_complete", "correct_abstention"} for row in rows)
    summary = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "label": "agent-authored and agent-verified frozen evaluation; not independently human-validated",
        "dataset_sha256": dataset_sha,
        "corpus_sha256": hashlib.sha256((ROOT / "data/processed/chunks.jsonl").read_bytes()).hexdigest(),
        "pipeline": "live FastAPI answer plus read-only local BM25/BGE/FAISS/RRF trace",
        "total_cases": len(rows),
        "strict_correct": strict_correct,
        "strict_correctness_rate": strict_correct / len(rows),
        "answerable_cases": len(answerable),
        "answerable_correct_and_complete": sum(row["classification"] == "correct_and_complete" for row in answerable),
        "answer_completeness_rate": statistics.mean(row["answer_completeness"] for row in answerable),
        "unanswerable_cases": len(unanswerable),
        "correct_abstentions": sum(row["classification"] == "correct_abstention" for row in unanswerable),
        "unnecessary_abstentions": sum(row["classification"] == "unnecessary_abstention" for row in rows),
        "unsupported_answer_count": sum(row["classification"] == "unsupported_or_hallucinated" for row in rows),
        "citation_support_rate": sum(row["citation_supported"] for row in actually_answered) / len(actually_answered) if actually_answered else None,
        "citation_support_denominator": len(actually_answered),
        "retrieval_recall_at_5": statistics.mean(row["retrieval_metrics"]["recall_at_5"] for row in retrieval_rows),
        "retrieval_recall_at_10": statistics.mean(row["retrieval_metrics"]["recall_at_10"] for row in retrieval_rows),
        "mrr_at_10": statistics.mean(row["retrieval_metrics"]["mrr_at_10"] for row in retrieval_rows),
        "ndcg_at_10": statistics.mean(row["retrieval_metrics"]["ndcg_at_10"] for row in retrieval_rows),
        "retrieval_metric_denominator": len(retrieval_rows),
        "api_latency_p50_ms": percentile(latencies, 0.50),
        "api_latency_p95_ms": percentile(latencies, 0.95),
        "subsets": {
            "answerable": subset_summary(answerable),
            "unanswerable": subset_summary(unanswerable),
            "standalone": subset_summary([row for row in rows if row["conversation_type"] == "standalone"]),
            "conversational": subset_summary([row for row in rows if row["conversation_type"] == "conversational"]),
        },
        "categories": {category: subset_summary(items) for category, items in sorted(category_rows.items())},
    }
    OUTPUT.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
