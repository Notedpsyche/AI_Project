"""Small, explainable query-intent representation shared by ranking and answers."""

# Compact task vocabularies are intentionally kept readable.
# ruff: noqa: E501

from __future__ import annotations

import re
from dataclasses import dataclass

TASK_GROUPS = {
    "address": {"address", "telephone", "contact", "mailing", "update", "change"},
    "application": {"apply", "application", "document", "documents", "proof", "eligibility"},
    "benefits": {"benefit", "benefits", "retirement", "disability", "survivor", "medicare"},
    "complaint": {"complaint", "report", "file", "problem", "business", "vehicle"},
    "card": {"card", "replace", "replacement", "number"},
    "fraud": {"fraud", "scam", "phishing", "identity"},
    "status": {"status", "check", "where", "when", "long", "take"},
}
TASK_PROFILES = {
    "card": re.compile(r"\b(?:social\s+security\s+)?card\b", re.I),
    "benefits_application": re.compile(
        r"\b(?:social\s+security|retirement|disability|survivor|medicare|benefits?)\b",
        re.I,
    ),
    "address_change": re.compile(r"\b(?:address|mailing|contact|telephone)\b", re.I),
    "benefit_status": re.compile(
        r"\b(?:status|check|where|when)\b.*\b(?:benefit|retirement|disability|survivor|medicare)\b"
        r"|\b(?:benefit|retirement|disability|survivor|medicare)\b.*\b(?:status|check|where|when)\b",
        re.I,
    ),
    "vehicle": re.compile(r"\b(?:vehicle|dmv|registration|register)\b", re.I),
}
STOPWORDS = {"a", "an", "and", "are", "be", "can", "do", "for", "how", "i", "if", "in", "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "what", "with", "you", "your"}


@dataclass(frozen=True)
class QueryIntent:
    text: str
    task_groups: frozenset[str]
    task_terms: frozenset[str]
    answer_type: str
    task_profile: str | None = None


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"\w+", text) if len(token) > 2 and token.lower() not in STOPWORDS}


def _task_profile(text: str, tokens: set[str]) -> str | None:
    """Infer a compact task identity from entity/action combinations."""
    normalized = " ".join(re.findall(r"\w+", text.lower()))
    if TASK_PROFILES["card"].search(normalized):
        if re.search(r"\b(?:document|documents|proof|identity|requirement|requirements|needed)\b", normalized):
            return "card_requirements"
        if re.search(r"\b(?:replace|replacement|renew|obtain|get|request)\b", normalized):
            return "card_replacement"
        return "card"
    if TASK_PROFILES["address_change"].search(normalized) and re.search(
        r"\b(?:change|update|modify|correct)\b", normalized
    ):
        return "address_change"
    if TASK_PROFILES["benefit_status"].search(normalized):
        return "benefit_status"
    if TASK_PROFILES["vehicle"].search(normalized):
        return "vehicle"
    if TASK_PROFILES["benefits_application"].search(normalized) and re.search(
        r"\b(?:apply|application|documents?|proof|eligibility|requirements?)\b",
        normalized,
    ):
        return "benefits_application"
    return None


def classify_intent(text: str) -> QueryIntent:
    tokens = _tokens(text)
    groups = frozenset(group for group, words in TASK_GROUPS.items() if tokens & words)
    if re.search(r"\b(can|could|is|are|does|will)\b", text, re.I):
        answer_type = "yes_no"
    elif re.search(r"\b(documents?|proof|requirements?|needed)\b", text, re.I):
        answer_type = "requirements"
    elif re.search(r"\b(why|reason)\b", text, re.I):
        answer_type = "explanation"
    elif re.search(r"\b(how|steps|apply|replace|change|update|report|file)\b", text, re.I):
        answer_type = "procedural"
    else:
        answer_type = "concise"
    return QueryIntent(text, groups, frozenset(tokens), answer_type, _task_profile(text, tokens))


def task_match(query: QueryIntent, candidate_text: str) -> tuple[float, float]:
    candidate = classify_intent(candidate_text)
    if not query.task_groups:
        return 0.5, 0.0
    shared = query.task_groups & candidate.task_groups
    same_card_family = (
        query.task_profile
        and candidate.task_profile
        and query.task_profile.startswith("card")
        and candidate.task_profile.startswith("card")
    )
    profile_conflict = bool(
        query.task_profile
        and candidate.task_profile
        and query.task_profile != candidate.task_profile
        and not same_card_family
    )
    contradiction = bool(candidate.task_groups and not shared) or profile_conflict
    lexical = len(query.task_terms & candidate.task_terms) / max(len(query.task_terms), 1)
    if profile_conflict:
        return 0.0, 1.0
    profile_match = 1.0 if query.task_profile and query.task_profile == candidate.task_profile else 0.0
    if same_card_family:
        profile_match = 0.75
    match = min(
        1.0,
        0.50 * (len(shared) / len(query.task_groups))
        + 0.25 * lexical
        + 0.25 * profile_match,
    )
    return match, 1.0 if contradiction else 0.0
