from backend.services.college_query import eligible, resolve_scope
from backend.services.college_select import select_evidence, supports_request
from doc2dial_retrieval.data import Chunk
from doc2dial_retrieval.retrieval import SearchResult, dedupe_results


def row(
    text: str,
    *,
    programme: str = "",
    topics: list[str] | None = None,
    section: str = "Official information",
    year: int | None = 2026,
) -> dict:
    return {
        "chunk_id": f"{programme}-{section}-{text[:12]}",
        "title": "Official IIIT Kottayam source",
        "section": section,
        "heading_path": [section],
        "text": text,
        "programme": programme,
        "admission_year": year,
        "topics": topics or [],
        "semantic_score": 0.8,
        "bm25_score": 4.0,
        "rrf_score": 0.03,
    }


def test_eligibility_rejects_generic_admission_procedure() -> None:
    scope = resolve_scope("What are the eligibility requirements for PhD admission?", [])
    evidence = row("B.Tech admission procedure is through counselling.", programme="PhD", topics=["admissions"])
    assert scope.intent == "eligibility"
    assert supports_request(scope, evidence) is False


def test_deadline_rejects_portal_final_submit_instruction() -> None:
    scope = resolve_scope("When is the final deadline to apply for B.Tech in 2026?", [])
    evidence = row("Select FINAL SUBMIT on the portal after completing all fields.", programme="B.Tech", topics=["admissions", "portal"])
    assert scope.intent == "admission_deadline"
    assert supports_request(scope, evidence) is False


def test_unknown_intent_is_not_supported() -> None:
    scope = resolve_scope("Tell me something interesting", [])
    assert scope.intent == "general"
    assert supports_request(scope, row("The institute has an official website.")) is False


def test_known_admission_process_remains_supported() -> None:
    scope = resolve_scope("How do I apply for B.Tech in 2026?", [])
    evidence = row("B.Tech admission procedure uses JEE Main and JoSAA counselling.", programme="B.Tech", topics=["admissions"])
    assert scope.intent == "admission_process"
    assert supports_request(scope, evidence) is True


def test_comparison_keeps_all_programmes_and_evidence() -> None:
    scope = resolve_scope("Compare the CSE and ECE programmes.", [])
    cse = row("The programme curriculum covers computer science foundations.", programme="B.Tech CSE", topics=["programmes"], section="CSE overview")
    ece = row("The programme curriculum covers electronics foundations.", programme="B.Tech ECE", topics=["programmes"], section="ECE overview")
    assert scope.programmes == ("B.Tech CSE", "B.Tech ECE")
    assert scope.intent == "programme_comparison"
    selected = select_evidence(scope, [cse, ece])
    assert {item["programme"] for item in selected} == {"B.Tech CSE", "B.Tech ECE"}


def test_comparison_rejects_generic_or_unrelated_programme_metadata() -> None:
    scope = resolve_scope("Compare CSE and ECE programmes.", [])
    assert not eligible(row("Generic programme overview", topics=["programmes"]), scope)
    assert not eligible(row("PhD overview", programme="PhD", topics=["programmes"]), scope)
    assert eligible(row("CSE overview", programme="B.Tech CSE", topics=["programmes"]), scope)


def test_follow_up_inherits_fee_semester_and_component() -> None:
    conversation = [{"role": "user", "content": "What is the first-semester B.Tech tuition fee in 2026?"}]
    scope = resolve_scope("How much is that?", conversation)
    assert scope.use_context is True
    assert scope.semesters == (1,)
    assert scope.fee_components == ("tuition fee",)
    assert {"programmes", "admission_year", "semesters", "fee_components"}.issubset(scope.inherited_slots)


def test_explicit_new_programme_and_year_reset_context() -> None:
    conversation = [{"role": "user", "content": "What is the first-semester B.Tech tuition fee in 2026?"}]
    scope = resolve_scope("What are the PhD eligibility requirements for 2027?", conversation)
    assert scope.use_context is False
    assert scope.programmes == ("PhD",)
    assert scope.admission_year == 2027
    assert scope.semesters == ()


def _chunk(chunk_id: str, *, programme: str, year: int, heading: str) -> Chunk:
    return Chunk(chunk_id, "doc", "college", "title", [heading], "section", "Identical evidence text for both routes.", ["1"], programme=programme, admission_year=year, topics=["documents"])


def test_deduplication_preserves_route_and_year_variants() -> None:
    josaa = SearchResult(_chunk("josaa", programme="B.Tech", year=2026, heading="JoSAA reporting"), bm25_rank=1)
    dasa = SearchResult(_chunk("dasa", programme="B.Tech", year=2026, heading="DASA reporting"), bm25_rank=2)
    older = SearchResult(_chunk("older", programme="B.Tech", year=2025, heading="JoSAA reporting"), bm25_rank=3)
    assert [result.chunk.chunk_id for result in dedupe_results([josaa, dasa, older], 3)] == ["josaa", "dasa", "older"]


def test_deduplication_collapses_same_scope_duplicate() -> None:
    first = SearchResult(_chunk("first", programme="B.Tech", year=2026, heading="JoSAA reporting"), bm25_rank=1)
    duplicate = SearchResult(_chunk("duplicate", programme="B.Tech", year=2026, heading="JoSAA reporting"), bm25_rank=2)
    assert [result.chunk.chunk_id for result in dedupe_results([first, duplicate], 2)] == ["first"]
