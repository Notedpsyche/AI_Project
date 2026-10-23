from doc2dial_retrieval.wmd.config import WmdConfig
from doc2dial_retrieval.wmd.preprocessing import WmdPreprocessor
from doc2dial_retrieval.wmd.representation import build_document_measure, build_query_measure


def config() -> WmdConfig:
    return WmdConfig("model", "revision", "cache", "chunks")


def test_preprocessing_normalizes_abbreviations_and_keeps_numbers() -> None:
    terms = WmdPreprocessor().tokenize_terms("B.Tech, e-M.Tech, Ph.D. fees for 2026")
    assert terms == ("btech", "emtech", "phd", "fees", "2026")


def test_preprocessing_is_consistent_for_query_and_document() -> None:
    preprocessor = WmdPreprocessor()
    query = build_query_measure("What is B.Tech fee in 2026?", preprocessor, config())
    document = build_document_measure({"title": "B.Tech", "heading_path": ["Fees"], "text": "Fee for 2026"}, preprocessor, config())
    assert "btech" in query.terms and "btech" in document.terms
    assert "2026" in query.terms and "2026" in document.terms


def test_measure_mass_and_caps_are_deterministic() -> None:
    small = WmdConfig("model", "revision", "cache", "chunks", query_token_limit=2, title_token_limit=1, heading_token_limit=1, passage_token_limit=1)
    preprocessor = WmdPreprocessor()
    query = build_query_measure("tuition tuition fee 2026", preprocessor, small)
    document = build_document_measure({"title": "B.Tech fee", "heading_path": ["First semester fee"], "text": "tuition fee 2026 2027"}, preprocessor, small)
    assert query.terms == ("tuition",)
    assert query.counts == (2,)
    assert query.masses().tolist() == [1.0]
    assert sum(document.counts) == 3
