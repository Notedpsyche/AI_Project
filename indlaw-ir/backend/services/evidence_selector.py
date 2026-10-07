"""Post-RRF evidence selection.

This layer intentionally works on retrieved result dictionaries.  It does not
change BM25, dense retrieval, or RRF; it only decides which RRF candidates are
useful enough and distinct enough to show to a person or answer composer.
"""

# Score formulas are intentionally kept readable as compact expressions.
# ruff: noqa: E501

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from backend.services.intent_service import classify_intent, task_match

TOKEN_RE = re.compile(r"\w+")
STOPWORDS = {
    "a", "an", "and", "are", "be", "can", "do", "for", "how", "i", "if", "in",
    "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "what", "with",
    "you", "your",
}
ACTION_WORDS = {
    "apply", "change", "check", "complaint", "file", "find", "get", "issue", "make",
    "place", "report", "replace", "request", "renew", "submit", "update", "verify",
}
ROLE_WORDS = {"against", "received", "someone", "you", "yourself", "filed"}
ADVERSARIAL_RE = re.compile(
    r"(?:against\s+you|filed\s+against|received\s+a\s+complaint|someone\s+files)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SelectorConfig:
    top_k: int = 3
    similarity_threshold: float = 0.90
    semantic_weight: float = 0.25
    bm25_weight: float = 0.10
    rrf_weight: float = 0.15
    domain_weight: float = 0.30
    intent_weight: float = 0.25
    quality_weight: float = 0.15
    task_weight: float = 0.20
    contradiction_weight: float = 0.25
    redundancy_weight: float = 0.25


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS}


def evidence_similarity(left: str, right: str) -> float:
    """Blend sequence and token similarity so additions are not missed."""
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence = SequenceMatcher(None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))).ratio()
    return 0.55 * sequence + 0.45 * jaccard


def _source_text(item: dict[str, Any]) -> str:
    heading = " ".join(item.get("heading_path", []))
    return " ".join(
        str(item.get(key, "")) for key in ("domain", "title", "section", "doc_id")
    ) + " " + heading


def _minmax(values: list[float]) -> dict[int, float]:
    if not values:
        return {}
    low, high = min(values), max(values)
    if high == low:
        return {index: 1.0 for index in range(len(values))}
    return {index: (value - low) / (high - low) for index, value in enumerate(values)}


def _domain_scores(query: str, candidates: list[dict[str, Any]]) -> list[float]:
    query_terms = _tokens(query)
    raw = []
    for item in candidates:
        source_terms = _tokens(_source_text(item))
        raw.append(len(query_terms & source_terms) / max(len(query_terms), 1))
    best = max(raw, default=0.0)
    # Source consistency is relative to this candidate pool, not a hard-coded
    # list of domains. A candidate with the strongest source cue gets full credit.
    if not best:
        return [0.0 for _ in raw]
    # Preserve the leading collection's score for its other sections, such as
    # a limitation section whose title omits the full agency name.
    best_domain = candidates[raw.index(best)].get("domain")
    return [
        1.0 if item.get("domain") == best_domain else score / best
        for item, score in zip(candidates, raw)
    ]


def _intent_score(query: str, item: dict[str, Any]) -> float:
    query_terms = _tokens(query)
    text_terms = _tokens(str(item.get("text", "")) + " " + _source_text(item))
    overlap = len(query_terms & text_terms) / max(len(query_terms), 1)
    query_actions = query_terms & ACTION_WORDS
    text_actions = text_terms & ACTION_WORDS
    action_match = len(query_actions & text_actions) / max(len(query_actions), 1) if query_actions else overlap
    query_role = bool(ADVERSARIAL_RE.search(query))
    text_role = bool(ADVERSARIAL_RE.search(str(item.get("text", "")) + " " + _source_text(item)))
    role_conflict = query_role != text_role
    return max(0.0, min(1.0, 0.55 * overlap + 0.45 * action_match - (0.60 if role_conflict else 0.0)))


def _quality_score(item: dict[str, Any]) -> float:
    text = str(item.get("text", ""))
    sentences = len(re.findall(r"[.!?](?:\s|$)", text))
    steps = len(re.findall(r"(?:\b\d+[.)]|select|choose|log in|enter|review|submit)\b", text.lower()))
    length_score = min(len(text) / 500.0, 1.0)
    return min(1.0, 0.15 * length_score + 0.20 * min(sentences / 4, 1.0) + 0.65 * min(steps / 5, 1.0))


def _reason(item: dict[str, Any], domain: float, intent: float, redundancy: float) -> str:
    parts = []
    if domain >= 0.9:
        parts.append("source consistency")
    if intent >= 0.7:
        parts.append("intent match")
    if float(item.get("semantic_score") or 0.0) >= 0.7:
        parts.append("high semantic relevance")
    if redundancy == 0:
        parts.append("complementary evidence")
    return ", ".join(parts) or "best available distinct evidence"


def select_evidence(query: str, candidates: list[dict[str, Any]], config: SelectorConfig | None = None) -> list[dict[str, Any]]:
    config = config or SelectorConfig()
    if not candidates:
        return []
    # Cosine scores are already comparable across this normalized BGE index.
    # Keeping them absolute prevents a high-scoring wrong-domain result from
    # winning merely because it is the pool maximum.
    semantic = {
        index: max(0.0, min(1.0, float(item.get("semantic_score") or 0.0)))
        for index, item in enumerate(candidates)
    }
    bm25 = _minmax([float(item.get("bm25_score") or 0.0) for item in candidates])
    rrf = _minmax([float(item.get("rrf_score") or 0.0) for item in candidates])
    domains = _domain_scores(query, candidates)
    query_intent = classify_intent(query)
    scored: list[dict[str, Any]] = []
    for index, item in enumerate(candidates):
        intent = _intent_score(query, item)
        quality = _quality_score(item)
        task, contradiction = task_match(query_intent, str(item.get("title", "")) + " " + str(item.get("text", "")))
        intent_conflict = bool(ADVERSARIAL_RE.search(query)) != bool(
            ADVERSARIAL_RE.search(str(item.get("text", "")) + " " + _source_text(item))
        )
        intent_conflict_penalty = 0.25 if intent_conflict else 0.0
        score = (
            config.semantic_weight * semantic[index]
            + config.bm25_weight * bm25[index]
            + config.rrf_weight * rrf[index]
            + config.domain_weight * domains[index]
            + config.intent_weight * intent
            + config.quality_weight * quality
            + config.task_weight * task
            - config.contradiction_weight * contradiction
            - intent_conflict_penalty
        )
        enriched = dict(item)
        enriched.update({"domain_score": domains[index], "intent_score": intent, "task_match_score": task, "contradiction_penalty": contradiction, "evidence_quality_score": quality, "final_evidence_score": score, "redundancy_penalty": 0.0, "intent_conflict_penalty": intent_conflict_penalty})
        scored.append(enriched)
    compatible = [item for item in scored if item["contradiction_penalty"] < 1.0]
    if compatible:
        scored = compatible
    preferred_domains = {item.get("domain") for item in scored if item["domain_score"] >= 0.99}
    if len(preferred_domains) == 1:
        preferred_domain = next(iter(preferred_domains))
        same_domain_count = sum(item.get("domain") == preferred_domain for item in scored)
        if same_domain_count >= 2:
            scored = [item for item in scored if item.get("domain_score", 0.0) >= 0.15]
    selected: list[dict[str, Any]] = []
    remaining = scored[:]
    while remaining and len(selected) < config.top_k:
        best_item = None
        best_value = float("-inf")
        for item in remaining:
            max_similarity = max((evidence_similarity(item.get("text", ""), chosen.get("text", "")) for chosen in selected), default=0.0)
            penalty = config.redundancy_weight * max_similarity
            value = float(item["final_evidence_score"]) - penalty
            if value > best_value:
                best_value, best_item = value, item
        assert best_item is not None
        remaining.remove(best_item)
        similarity = max((evidence_similarity(best_item.get("text", ""), chosen.get("text", "")) for chosen in selected), default=0.0)
        if selected and similarity >= config.similarity_threshold:
            continue
        best_item["redundancy_penalty"] = config.redundancy_weight * similarity
        best_item["final_evidence_score"] = best_value
        best_item["selection_reason"] = _reason(best_item, best_item["domain_score"], best_item["intent_score"], similarity)
        selected.append(best_item)
    return selected
