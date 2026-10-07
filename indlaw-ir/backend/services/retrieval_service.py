import logging
from pathlib import Path

from backend.services.context_service import bounded_history, decide_context
from backend.services.evidence_selector import SelectorConfig, select_evidence
from doc2dial_retrieval.search import SearchEngine, result_dicts

LOGGER = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, root: Path):
        self.engine = SearchEngine(root)

    def search(self, message: str, conversation: list[dict[str, str]] | None = None) -> dict:
        conversation = conversation or []
        user_turns = [item for item in bounded_history(conversation) if item.get("role") == "user"]
        similarity = None
        if user_turns:
            vectors = self.engine.dense.encode_queries([message, user_turns[-1]["content"]])
            similarity = float(vectors[0] @ vectors[1])
        decision = decide_context(message, conversation, semantic_similarity=similarity)
        built = decision.effective_query
        recent = (
            [{"role": "user", "content": user_turns[-1]["content"]}]
            if decision.use_context
            else []
        )
        systems, best = self.engine.search_all(message, recent)
        candidates = result_dicts(systems["hybrid"])
        for result in candidates:
            result["section"] = (
                result["heading_path"][-1] if result["heading_path"] else result["title"]
            )
            result["span_id"] = ", ".join(result.get("span_ids", []))
        selector_config = SelectorConfig(**self.engine.config.get("evidence_selection", {}))
        results = select_evidence(built, candidates, selector_config)
        LOGGER.info(
            "RRF candidates query=%r top=%s",
            built,
            [(item.get("domain"), item.get("title")) for item in candidates[:5]],
        )
        for rank, result in enumerate(results, 1):
            result["rank"] = rank
        LOGGER.info(
            "FINAL EVIDENCE query=%r selected=%s",
            built,
            [
                (item.get("domain"), item.get("title"), round(item["final_evidence_score"], 3))
                for item in results
            ],
        )
        LOGGER.info(
            "context decision=%s score=%.3f reason=%s",
            "USE_CONTEXT" if decision.use_context else "STANDALONE",
            decision.score,
            decision.reason,
        )
        LOGGER.info("retrieval query=%r latency-ready best_semantic=%.4f", built, best)
        return {
            "query": built,
            "answer_query": built if decision.use_context else message.strip(),
            "results": results,
            "confidence": max(best, 0.0),
            "context_turns": decision.context_turns,
            "context_used": decision.use_context,
            "context_score": decision.score,
            "context_decision": "USE_CONTEXT" if decision.use_context else "STANDALONE",
            "context_reason": decision.reason,
        }
