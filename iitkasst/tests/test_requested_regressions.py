from backend.services.answer_service import grounded_answer
from backend.services.context_service import decide_context
from backend.services.evidence_selector import select_evidence
from backend.services.intent_service import classify_intent


def candidate(title: str, domain: str, text: str, semantic: float, bm25: float, rrf: float) -> dict:
    return {
        "title": title,
        "domain": domain,
        "doc_id": title,
        "section": title,
        "text": text,
        "semantic_score": semantic,
        "bm25_score": bm25,
        "rrf_score": rrf,
    }


def test_card_duration_follow_up_inherits_previous_task() -> None:
    result = decide_context(
        "How long does it take?",
        [{"role": "user", "content": "How do I replace my Social Security card?"}],
        semantic_similarity=0.05,
    )
    assert result.use_context is True
    assert "Social Security card" in result.effective_query
    assert "CURRENT QUESTION: How long does it take?" in result.effective_query

    selected = select_evidence(
        result.effective_query,
        [
            candidate("DMV processing times", "dmv", "How long does vehicle registration take?", .98, 40, .04),
            candidate("Social Security card replacement", "ssa", "A replacement Social Security card is processed after the request is submitted.", .78, 20, .03),
        ],
    )
    assert selected[0]["domain"] == "ssa"


def test_address_online_follow_up_inherits_address_task() -> None:
    result = decide_context(
        "Can I do it online?",
        [{"role": "user", "content": "How do I change my address with Social Security?"}],
        semantic_similarity=0.05,
    )
    assert result.use_context is True
    selected = select_evidence(
        result.effective_query,
        [
            candidate("Social Security address change", "ssa", "You can update your address online through your account.", .84, 20, .03),
            candidate("Social Security card replacement", "ssa", "Request a replacement Social Security card online.", .90, 30, .04),
        ],
    )
    assert selected[0]["title"] == "Social Security address change"
    answer, refused = grounded_answer(result.effective_query, selected, .9)
    assert refused is False
    assert "online" in answer.lower()


def test_benefits_application_rejects_card_documents() -> None:
    query = "What documents do I need to apply for Social Security?"
    intent = classify_intent(query)
    assert intent.task_profile == "benefits_application"
    selected = select_evidence(
        query,
        [
            candidate("Social Security card documents", "ssa", "Documents and proof of identity needed to replace a Social Security card.", .97, 45, .05),
            candidate("Apply for retirement benefits", "ssa", "To apply for Social Security retirement benefits, provide documents showing eligibility and work history.", .78, 25, .03),
        ],
    )
    assert all("card" not in row["title"].lower() for row in selected)
    answer, refused = grounded_answer(query, selected, .9)
    assert refused is False
    assert "retirement benefits" in answer.lower()
    assert "replace a social security card" not in answer.lower()


def test_new_vehicle_topic_does_not_inherit_card_context() -> None:
    result = decide_context(
        "How do I register a vehicle?",
        [{"role": "user", "content": "How do I replace my Social Security card?"}],
        semantic_similarity=0.05,
    )
    assert result.use_context is False
    assert result.effective_query == "How do I register a vehicle?"

