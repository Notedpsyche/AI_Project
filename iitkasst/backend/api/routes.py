import re
import time

from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import ChatRequest, ChatResponse, Evidence, SearchRequest
from backend.config import MODEL_NAME
from backend.services.college_answer import grounded_answer

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict:
    service = getattr(request.app.state, "retrieval", None)
    if service is None:
        return {
            "status": "loading", "model": MODEL_NAME, "retrieval": "hybrid", "device": "unknown"
        }
    device = str(service.engine.dense.model.device)
    return {"status": "ok", "model": MODEL_NAME, "retrieval": "hybrid", "device": device}


def _evidence(rows: list[dict]) -> list[Evidence]:
    return [Evidence(**{key: row.get(key) for key in Evidence.model_fields}) for row in rows]


@router.post("/search")
def search(payload: SearchRequest, request: Request) -> dict:
    service = getattr(request.app.state, "retrieval", None)
    if service is None:
        raise HTTPException(503, "The retrieval system is still loading.")
    started = time.perf_counter()
    result = service.search(payload.query)
    return {
        "query": payload.query,
        "retrieval_mode": "hybrid",
        "results": [item.model_dump() for item in _evidence(result["results"])],
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    service = getattr(request.app.state, "retrieval", None)
    if service is None:
        raise HTTPException(503, "The retrieval system is still loading.")
    started = time.perf_counter()
    result = service.search(payload.message, [item.model_dump() for item in payload.conversation])
    answer, refused = grounded_answer(result["scope"], result["results"])
    cited_ranks = {int(rank) for rank in re.findall(r"\[(\d+)\]", answer)}
    cited_evidence = [item for item in result["results"] if item["rank"] in cited_ranks] if not refused else []
    response = ChatResponse(
        answer=answer,
        refused=refused,
        query=result["query"],
        retrieval_mode="hybrid",
        context_used=result["context_used"],
        context_turns=result["context_turns"],
        context_score=result["context_score"],
        context_decision=result["context_decision"],
        context_reason=result["context_reason"],
        confidence=result["confidence"],
        evidence=_evidence(cited_evidence),
        debug={
            "current_query": payload.message,
            "context_decision": result["context_decision"],
            "context_score": result["context_score"],
            "context_reason": result["context_reason"],
            "programme": result["scope"].programme,
            "admission_year": result["scope"].admission_year,
            "intent": result["scope"].intent,
            "reformulated_query": result["query"],
            "final_evidence": [item["title"] for item in cited_evidence],
        },
    )
    request.app.state.last_latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return response
