"""Generic conversation-context gating before retrieval query construction."""

# Compact generic intent patterns are intentionally kept readable.
# ruff: noqa: E501

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

STOPWORDS = {
    "a", "an", "and", "are", "be", "can", "do", "for", "how", "i", "if", "in",
    "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "what", "with",
    "you", "your",
}
INTENT_GROUPS = {
    "address": {"address", "telephone", "contact", "mailing", "update", "change"},
    "application": {"apply", "application", "document", "documents", "proof", "identity", "eligibility"},
    "benefits": {"benefit", "benefits", "retirement", "disability", "survivor", "medicare"},
    "complaint": {"complaint", "report", "file", "problem", "business"},
    "card": {"card", "replace", "replacement", "number"},
    "fraud": {"fraud", "scam", "phishing", "identity"},
    "status": {"status", "check", "where", "when", "long"},
}
FOLLOW_UP_ONLY_TERMS = {
    "again", "can", "could", "do", "does", "how", "it", "online", "offline",
    "same", "that", "the", "there", "these", "those", "this", "what", "when",
    "where", "which", "who", "why", "long", "much", "many", "often", "far",
    "take", "takes", "cost", "costs", "price", "fee", "fees", "duration", "time",
    "document", "documents", "proof", "identity", "requirement", "requirements",
    "needed", "need", "status", "check",
}
REFERENCE_RE = re.compile(
    r"\b(it|this|that|these|those|there|online|again|same|do that|do it|what about|where can i|how long|can i|could i)\b",
    re.IGNORECASE,
)
FOLLOW_UP_INFO_RE = re.compile(
    r"\b(?:how\s+(?:long|much|many|often|far)|what\s+(?:documents?|proof|requirements?)"
    r"|where\b|when\b|online\b|offline\b|(?:cost|price|fee|fees|duration)\b)\b",
    re.IGNORECASE,
)
EXPLICIT_TASK_RE = re.compile(
    r"\b(apply|application|change|update|replace|report|file|renew|check|verify|request|documents?|proof|benefits?|retirement|card|fraud|complaint)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContextDecision:
    use_context: bool
    score: float
    reason: str
    context_turns: int
    effective_query: str


def bounded_history(conversation: Sequence[dict[str, str]], turns: int = 3) -> list[dict[str, str]]:
    """Keep the most recent meaningful user/assistant turns for inspection."""
    items = [item for item in conversation if item.get("content", "").strip()]
    return items[-turns * 2 :]


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\w+", text)
        if len(token) > 2 and token.lower() not in STOPWORDS
    }


def _intent_groups(text: str) -> set[str]:
    tokens = _tokens(text)
    return {group for group, words in INTENT_GROUPS.items() if tokens & words}


def _user_turns(conversation: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return [item for item in bounded_history(conversation) if item.get("role") == "user"]


def _is_underspecified_follow_up(message: str) -> bool:
    """Recognize information requests that lack a complete standalone task."""
    tokens = _tokens(message)
    anchors = tokens - FOLLOW_UP_ONLY_TERMS
    has_follow_up_signal = bool(REFERENCE_RE.search(message) or FOLLOW_UP_INFO_RE.search(message))
    return has_follow_up_signal and not anchors


def decide_context(
    message: str,
    conversation: Sequence[dict[str, str]],
    semantic_similarity: float | None = None,
) -> ContextDecision:
    """Decide whether the current question depends on a previous user turn.

    The default is standalone. A short/anaphoric question can opt into history,
    but an explicit new intent wins even when the domain stays the same.
    """
    users = _user_turns(conversation)
    if not users:
        return ContextDecision(False, 0.0, "No previous user question is available.", 0, message.strip())
    previous = users[-1]["content"].strip()
    current_tokens, previous_tokens = _tokens(message), _tokens(previous)
    overlap = len(current_tokens & previous_tokens) / max(len(current_tokens | previous_tokens), 1)
    current_groups, previous_groups = _intent_groups(message), _intent_groups(previous)
    reference = bool(REFERENCE_RE.search(message))
    explicit_task = bool(EXPLICIT_TASK_RE.search(message))
    underspecified_follow_up = _is_underspecified_follow_up(message)
    information_change = bool(
        current_groups
        and previous_groups
        and current_groups.isdisjoint(previous_groups)
        and not underspecified_follow_up
    )
    if semantic_similarity is None:
        semantic_similarity = overlap
    semantic_similarity = max(0.0, min(1.0, float(semantic_similarity)))
    topic_continuity = max(overlap, 1.0 if current_groups & previous_groups else 0.0)
    score = 0.45 * semantic_similarity + 0.35 * float(reference) + 0.20 * topic_continuity
    if information_change:
        score -= 0.55
    score = max(0.0, min(1.0, score))

    use_context = (
        (
            underspecified_follow_up
            and not information_change
            and (semantic_similarity >= 0.20 or len(current_tokens) <= 8)
        )
        or (reference and not information_change and (semantic_similarity >= 0.20 or len(current_tokens) <= 6))
        or (bool(current_groups & previous_groups) and len(current_tokens) <= 6 and not information_change)
        or (not explicit_task and not information_change and score >= 0.52)
    )
    if information_change:
        reason = "Current query introduces a different information need."
    elif use_context:
        reason = "Current query contains an unresolved reference to the previous task."
    else:
        reason = "Current query is sufficiently self-contained to search independently."
    # The previous user task is the safest compact context. The prior answer
    # is intentionally excluded from reformulation so stale answer text cannot
    # contaminate a new retrieval query.
    recent = [users[-1]]
    effective = context_query(message, recent) if use_context else message.strip()
    return ContextDecision(use_context, score, reason, len(recent) if use_context else 0, effective)


def context_query(
    message: str, conversation: Sequence[dict[str, str]], turns: int = 3
) -> str:
    history = bounded_history(conversation, turns)
    if not history:
        return message.strip()
    prefix = "\n".join(f"{item['role'].upper()}: {item['content']}" for item in history)
    return f"{prefix}\nCURRENT QUESTION: {message.strip()}"
