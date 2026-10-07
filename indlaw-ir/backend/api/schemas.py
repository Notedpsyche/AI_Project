from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation: list[Message] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class Evidence(BaseModel):
    rank: int
    title: str
    domain: str
    doc_id: str
    span_id: str
    section: str
    text: str
    semantic_score: float | None = None
    semantic_rank: int | None = None
    bm25_score: float | None = None
    bm25_rank: int | None = None
    rrf_score: float | None = None
    domain_score: float | None = None
    intent_score: float | None = None
    task_match_score: float | None = None
    contradiction_penalty: float | None = None
    intent_conflict_penalty: float | None = None
    evidence_quality_score: float | None = None
    redundancy_penalty: float | None = None
    final_evidence_score: float | None = None
    selection_reason: str | None = None


class ChatResponse(BaseModel):
    answer: str
    refused: bool
    query: str
    retrieval_mode: str
    context_used: bool
    context_turns: int
    context_score: float
    context_decision: str
    context_reason: str
    confidence: float
    evidence: list[Evidence]
    debug: dict | None = None
