"""Shared, query-level evaluation helpers for the local college corpus."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path

from backend.services.college_query import resolve_scope
from backend.services.college_select import select_evidence
from doc2dial_retrieval.search import SearchEngine, result_dicts

ROOT = Path(__file__).resolve().parents[1]


def load_judgments(root: Path = ROOT) -> list[dict]:
    path = root / "evaluation/judgments.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Human judgments are required: {path}. See evaluation/annotation_guide.md")
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    families: dict[str, str] = {}
    gold_splits: dict[str, str] = {}
    ids: set[str] = set()
    for item in items:
        required = {"query_id", "query", "split", "question_family", "gold_chunk_ids", "answerable", "answer_fact", "expected_behavior"}
        if not required <= item.keys():
            raise ValueError(f"Incomplete judgment row: {item.get('query_id')}")
        if item["split"] not in {"train", "dev", "test"} or item["query_id"] in ids:
            raise ValueError(f"Invalid split or duplicate ID: {item['query_id']}")
        ids.add(item["query_id"])
        behavior = item["expected_behavior"]
        if behavior not in {"answer", "clarify", "abstain"}:
            raise ValueError(f"Invalid expected behavior: {item['query_id']}")
        if item["answerable"] != (behavior == "answer"):
            raise ValueError(f"Answerability and expected behavior disagree: {item['query_id']}")
        if behavior == "clarify" and not item.get("clarification_needed"):
            raise ValueError(f"Clarification target missing: {item['query_id']}")
        if behavior == "answer" and not item["answer_fact"].strip():
            raise ValueError(f"Answer fact missing: {item['query_id']}")
        if behavior != "answer" and item["answer_fact"].strip():
            raise ValueError(f"Non-answer row has an answer fact: {item['query_id']}")
        family = item["question_family"]
        if family in families and families[family] != item["split"]:
            raise ValueError(f"Question family crosses splits: {family}")
        families[family] = item["split"]
        if not item["answerable"] and item["gold_chunk_ids"]:
            raise ValueError(f"Unanswerable question has gold evidence: {item['query_id']}")
        if item["answerable"] and not item["gold_chunk_ids"]:
            raise ValueError(f"Answerable question needs gold evidence: {item['query_id']}")
        for chunk_id in item["gold_chunk_ids"]:
            if chunk_id in gold_splits and gold_splits[chunk_id] != item["split"]:
                raise ValueError(f"Gold passage crosses splits: {chunk_id}")
            gold_splits[chunk_id] = item["split"]
    return items


def corpus_hash(root: Path = ROOT) -> str:
    return hashlib.sha256((root / "data/processed/chunks.jsonl").read_bytes()).hexdigest()


def retrieve_modes(engine: SearchEngine, item: dict, reranker: dict | None = None) -> dict[str, list[str]]:
    engine.config["search"]["final_top_k"] = 10
    history = item.get("history", [])
    systems, _ = engine.search_all(item["query"], history)
    modes = {mode: [row.chunk.chunk_id for row in systems[mode][:10]] for mode in ("bm25", "semantic", "hybrid")}
    if reranker is not None:
        rows = result_dicts(systems["hybrid"])
        for row in rows:
            row["section"] = row["heading_path"][-1] if row["heading_path"] else row["title"]
        scope = resolve_scope(item["query"], history)
        modes["reranked"] = [row["chunk_id"] for row in select_evidence(scope, rows, reranker, top_k=10)]
    return modes


def query_metrics(gold: set[str], predicted: list[str]) -> dict[str, float]:
    if not gold:
        return {}
    top = predicted[:10]
    hits = [1 if chunk_id in gold else 0 for chunk_id in top]
    first = next((index + 1 for index, hit in enumerate(hits) if hit), None)
    dcg = sum(hit / math.log2(index + 2) for index, hit in enumerate(hits))
    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(gold), 10)))
    return {
        "recall_at_5": len(set(top[:5]) & gold) / len(gold),
        "mrr_at_10": 1 / first if first else 0.0,
        "ndcg_at_10": dcg / ideal if ideal else 0.0,
    }


def evaluate(engine: SearchEngine, items: list[dict], reranker: dict | None = None) -> tuple[dict, list[dict]]:
    totals: dict[str, list[dict[str, float]]] = defaultdict(list)
    rows: list[dict] = []
    latencies: list[float] = []
    for item in items:
        started = time.perf_counter()
        modes = retrieve_modes(engine, item, reranker)
        latencies.append((time.perf_counter() - started) * 1000)
        gold = set(item["gold_chunk_ids"])
        row = {"query_id": item["query_id"], "split": item["split"], "answerable": item["answerable"], "gold_chunk_ids": sorted(gold), "rankings": modes}
        rows.append(row)
        if item["answerable"]:
            for mode, ranking in modes.items():
                totals[mode].append(query_metrics(gold, ranking))
    summary = {
        mode: {metric: sum(row[metric] for row in values) / len(values) for metric in ("recall_at_5", "mrr_at_10", "ndcg_at_10")}
        for mode, values in totals.items() if values
    }
    ordered = sorted(latencies)
    latency = {"p50_ms": statistics.median(ordered), "p95_ms": ordered[max(0, math.ceil(.95 * len(ordered)) - 1)]} if ordered else {}
    return {"queries": len(items), "answerable_queries": sum(item["answerable"] for item in items), "metrics": summary, "retrieval_latency": latency}, rows
