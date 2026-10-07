"""Deterministic answer composition from selected evidence only."""

# Compact evidence patterns are intentionally kept readable.
# ruff: noqa: E501

from __future__ import annotations

import re
from difflib import SequenceMatcher

from backend.config import REFUSAL
from backend.services.intent_service import classify_intent, task_match

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|(?<=:)\s+")
ACTION_RE = re.compile(
    r"\b(log in|select|choose|enter|type|review|verify|submit|call|report|file|apply|update|change|renew|complete|follow)\b",
    re.IGNORECASE,
)
LIMITATION_RE = re.compile(
    r"\b(not available|unavailable|except|unless|only if|cannot|can't|does not apply|do not have|without)\b",
    re.IGNORECASE,
)
NOISE_RE = re.compile(
    r"\b(still have questions|for more information|learn more|visit our website)\b",
    re.IGNORECASE,
)
STEP_ORDER = (
    r"log in|sign in|open",
    r"my profile|profile",
    r"update|change|edit",
    r"enter|type|provide",
    r"when|date|take effect",
    r"next|continue",
    r"review|verify|check",
    r"submit|save|finish",
)
STEP_START_RE = re.compile(
    r"^(log in|sign in|open|select|choose|enter|type|review|verify|submit|call|report|file|apply|renew|complete)\b",
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    return [part.strip(" -") for part in SENTENCE_RE.split(" ".join(text.split())) if part.strip()]


def _dedupe_claims(sentences: list[str]) -> list[str]:
    selected: list[str] = []
    for sentence in sentences:
        normalized = re.sub(r"[^a-z0-9 ]", "", sentence.lower())
        if len(normalized) < 12:
            continue
        if any(
            normalized == re.sub(r"[^a-z0-9 ]", "", old.lower())
            or SequenceMatcher(
                None, normalized, re.sub(r"[^a-z0-9 ]", "", old.lower())
            ).ratio()
            >= 0.92
            for old in selected
        ):
            continue
        selected.append(sentence)
    return selected


def _relevant_sentences(message: str, evidence: list[dict]) -> list[str]:
    query_intent = classify_intent(message)
    query_terms = {
        token.lower()
        for token in re.findall(r"\w+", message)
        if len(token) > 3
        and token.lower() not in {"what", "how", "should", "with", "from", "that"}
    }
    ordered: list[str] = []
    for item in evidence:
        for sentence in _sentences(str(item.get("text", ""))):
            words = {word.lower() for word in re.findall(r"\w+", sentence)}
            _, contradiction = task_match(query_intent, sentence)
            if contradiction and (ACTION_RE.search(sentence) or query_intent.task_groups):
                continue
            if words & query_terms or ACTION_RE.search(sentence) or LIMITATION_RE.search(sentence):
                if not NOISE_RE.search(sentence):
                    ordered.append(sentence)
    return _dedupe_claims(ordered)


def _step_rank(sentence: str, position: int) -> tuple[int, int]:
    if re.search(r"\b(select|choose)\s+when\b|\btake effect\b", sentence, re.IGNORECASE):
        return 4, position
    for rank, pattern in enumerate(STEP_ORDER):
        if re.search(pattern, sentence, re.IGNORECASE):
            return rank, position
    return len(STEP_ORDER), position


def grounded_answer(
    message: str, evidence: list[dict], confidence: float, threshold: float = 0.67
) -> tuple[str, bool]:
    if confidence < threshold or not evidence:
        return REFUSAL, True
    claims = _relevant_sentences(message, evidence)
    if not claims:
        return REFUSAL, True

    query_intent = classify_intent(message)
    procedures = [
        claim
        for claim in claims
        if ACTION_RE.search(claim)
        and (STEP_START_RE.search(claim) or re.search(r"\bthen\s+select\b", claim, re.I))
    ]
    limitations = [claim for claim in claims if LIMITATION_RE.search(claim)]
    procedural_query = query_intent.answer_type == "procedural"

    if query_intent.answer_type == "yes_no":
        direct = [
            claim
            for claim in claims
            if re.search(r"\b(online|available|can|cannot|can't|yes|no)\b", claim, re.I)
        ]
        if direct:
            answer = " ".join(direct[:2])
            if procedures:
                answer += "\n\n" + "\n".join(
                    f"{index}. {step}"
                    for index, step in enumerate(
                        sorted(procedures, key=lambda sentence: _step_rank(sentence, procedures.index(sentence)))[:6],
                        1,
                    )
                )
            return answer, False

    if query_intent.answer_type == "requirements":
        requirement_claims = [
            claim
            for claim in claims
            if re.search(r"\b(document|documents|proof|identity|required|need|eligib)\w*\b", claim, re.I)
        ]
        if requirement_claims:
            return "\n".join(f"- {claim}" for claim in requirement_claims[:6]), False
        return "The available documents provide only partial information about the requirements.", False

    if procedural_query and len(procedures) >= 2:
        intro = next(
            (
                claim
                for claim in claims
                if claim not in procedures
                and not LIMITATION_RE.search(claim)
                and not NOISE_RE.search(claim)
                and re.search(r"\b(can|may|online|account|available)\b", claim, re.I)
            ),
            "",
        )
        steps = sorted(procedures, key=lambda sentence: _step_rank(sentence, procedures.index(sentence)))[:8]
        answer = (intro + "\n\n" if intro else "") + "\n".join(
            f"{index}. {step}" for index, step in enumerate(steps, 1)
        )
        if limitations:
            answer += "\n\nNote: " + " ".join(limitations[:2])
        return answer, False

    return " ".join(claims[:4]), False


def extract_claims(message: str, evidence: list[dict]) -> list[str]:
    """Expose the same filtered claims used by the answer composer for debug output."""
    return _relevant_sentences(message, evidence)
