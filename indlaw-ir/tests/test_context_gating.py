from backend.services.context_service import decide_context


def decision(previous: str, current: str, similarity: float = 0.6):
    return decide_context(
        current,
        [{"role": "user", "content": previous}],
        semantic_similarity=similarity,
    )


def test_address_online_follow_up_uses_context() -> None:
    result = decision("How do I change my address with Social Security?", "Can I do it online?")
    assert result.use_context is True
    assert result.context_turns == 1


def test_same_domain_application_question_is_standalone() -> None:
    result = decision(
        "How do I change my address with Social Security?",
        "What documents do I need to apply for Social Security?",
    )
    assert result.use_context is False
    assert result.effective_query == "What documents do I need to apply for Social Security?"


def test_proof_of_identity_follows_document_task() -> None:
    result = decision(
        "What documents do I need to apply for Social Security?",
        "Do I need proof of identity?",
    )
    assert result.use_context is True


def test_unrelated_vehicle_question_is_standalone() -> None:
    result = decision(
        "What documents do I need to apply for Social Security?",
        "How do I report a problem with a vehicle?",
    )
    assert result.use_context is False


def test_ambiguous_online_question_uses_context() -> None:
    result = decision("How do I change my address?", "What about online?")
    assert result.use_context is True
