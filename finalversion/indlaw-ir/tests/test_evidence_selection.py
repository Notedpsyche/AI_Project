# ruff: noqa: E501

from backend.services.answer_service import grounded_answer
from backend.services.context_service import decide_context
from backend.services.evidence_selector import select_evidence
from backend.services.intent_service import classify_intent, task_match


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


def test_address_prefers_source_and_removes_duplicate_dmv() -> None:
    rows = select_evidence(
        "How do I change my address with Social Security?",
        [
            candidate("Escrow accounts", "dmv", "How do I update my address with the DMV?", .99, 40, .04),
            candidate("How to change your address?", "ssa", "Log in to my Social Security. Select My Profile. Select Update Contact Information.", .91, 30, .03),
            candidate("Change of Address | Social Security Administration", "ssa", "Log in to my Social Security. Select My Profile. Select Update Contact Information.", .88, 28, .029),
            candidate("SSI limitation", "ssa", "The online address update service is not available for SSI recipients.", .75, 10, .02),
        ],
    )
    assert rows[0]["domain"] == "ssa"
    assert not any(row["domain"] == "dmv" for row in rows)
    assert len(rows) == 2
    assert rows[1]["title"] == "SSI limitation"


def test_complaint_intent_demotes_complaint_against_user() -> None:
    rows = select_evidence(
        "What should I do if I need to report a complaint?",
        [
            candidate("What to do if a complaint is filed against you", "dmv", "If someone files a complaint against you, respond to the notice.", .90, 25, .03),
            candidate("How to report a complaint", "dmv", "You can report or file a complaint against a regulated business.", .86, 22, .029),
        ],
    )
    assert rows[0]["title"] == "How to report a complaint"


def test_follow_up_query_retains_context() -> None:
    decision = decide_context(
        "Can I do it online?",
        [{"role": "user", "content": "How do I change my address with Social Security?"}],
    )
    assert decision.use_context is True
    assert decision.context_turns == 1
    assert "Social Security" in decision.effective_query
    assert "CURRENT QUESTION: Can I do it online?" in decision.effective_query


def test_weak_evidence_refuses_without_fabrication() -> None:
    answer, refused = grounded_answer("What is the capital of France?", [], .35)
    assert refused is True
    assert "couldn't find enough information" in answer


def test_answer_composes_ordered_unique_procedure() -> None:
    answer, refused = grounded_answer(
        "How do I change my address with Social Security?",
        [
            {"text": "Select Update Contact Information. Enter your address. Select Next."},
            {"text": "Log in to my Social Security. Select My Profile. Select Update Contact Information."},
        ],
        .9,
    )
    assert refused is False
    assert answer.index("Log in") < answer.index("My Profile") < answer.index("Update Contact")
    assert answer.count("Update Contact Information") == 1


def test_task_compatibility_rejects_card_for_benefit_application() -> None:
    query = classify_intent("What documents do I need to apply for Social Security?")
    match, contradiction = task_match(
        query,
        "Social Security Card replacement documents and proof of identity",
    )
    assert match < 1.0
    assert contradiction == 1.0


def test_follow_up_answer_filters_retirement_application_claims() -> None:
    answer, refused = grounded_answer(
        "How do I change my address with Social Security?\nCURRENT QUESTION: Can I do it online?",
        [
            {"text": "You can update your address online. Log in to my Social Security. Select My Profile."},
            {"text": "Complete the application. Select Start A New Application for retirement benefits."},
        ],
        .9,
    )
    assert refused is False
    assert "online" in answer.lower()
    assert "Start A New Application" not in answer


def test_requirements_answer_does_not_emit_procedure_steps() -> None:
    answer, refused = grounded_answer(
        "What documents do I need to apply for Social Security?",
        [{"text": "You may need proof of identity and documents showing eligibility. Log in to begin the application."}],
        .9,
    )
    assert refused is False
    assert answer.startswith("-")
    assert "Log in to begin" not in answer
