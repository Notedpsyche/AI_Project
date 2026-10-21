"""College retrieval while retaining the project's BM25/BGE/RRF engine."""

import hashlib
import json
import logging
from pathlib import Path

from backend.services.college_query import resolve_scope
from backend.services.college_select import select_evidence
from doc2dial_retrieval.search import SearchEngine, result_dicts

LOGGER = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, root: Path):
        self.engine = SearchEngine(root)
        model_path = root / "models/college_reranker.json"
        saved = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else None
        if saved and saved.get("deploy") is True:
            if len(saved.get("weights", [])) != 6:
                raise ValueError("Deployed reranker has an incompatible feature schema")
            corpus_path = root / "data/processed/chunks.jsonl"
            digest = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
            if saved.get("corpus_sha256") != digest:
                raise ValueError("Deployed reranker was trained on a different college corpus")
        self.reranker = saved if saved and saved.get("deploy") is True else None

    def search(self, message: str, conversation: list[dict[str, str]] | None = None) -> dict:
        conversation = conversation or []
        scope = resolve_scope(message, conversation)
        previous = next((item["content"] for item in reversed(conversation[-6:]) if item.get("role") == "user"), "")
        recent = [{"role": "user", "content": previous}] if scope.use_context else []
        systems, best = self.engine.search_all(message, recent)
        candidates = result_dicts(systems["hybrid"])
        for row in candidates:
            row["section"] = row["heading_path"][-1] if row["heading_path"] else row["title"]
            row["span_id"] = ""
        results = select_evidence(scope, candidates, self.reranker)
        for rank, row in enumerate(results, 1):
            row["rank"] = rank
        LOGGER.info("college query=%r selected=%s", scope.query, [(row["doc_id"], row["section"]) for row in results])
        return {
            "query": scope.query,
            "scope": scope,
            "results": results,
            "candidate_preview": candidates[:20],
            "confidence": max(best, 0.0),
            "context_turns": 1 if scope.use_context else 0,
            "context_used": scope.use_context,
            "context_score": 1.0 if scope.use_context else 0.0,
            "context_decision": "USE_CONTEXT" if scope.use_context else "STANDALONE",
            "context_reason": scope.reason,
        }
