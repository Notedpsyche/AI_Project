from doc2dial_retrieval.data import parse_parent_titles, tokenize


def test_stringified_parent_titles_are_safe_and_normalized() -> None:
    assert parse_parent_titles("['A', 'B']") == ["A", "B"]


def test_invalid_parent_titles_fail_clearly() -> None:
    try:
        parse_parent_titles("{'not': 'a list'}")
    except ValueError as error:
        assert "list" in str(error)
    else:
        raise AssertionError("invalid parent_titles should fail")


def test_tokenizer_punctuation_is_consistent() -> None:
    assert tokenize("Documents, and documents.") == ["documents", "and", "documents"]
