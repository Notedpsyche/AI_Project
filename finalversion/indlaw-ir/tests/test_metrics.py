from doc2dial_retrieval.metrics import aggregate_metrics, recall_at_k, reciprocal_rank


def test_recall_and_mrr_use_first_relevant_rank() -> None:
    ranked = ["wrong", "gold", "other"]
    assert recall_at_k(ranked, {"gold"}, 1) is False
    assert recall_at_k(ranked, {"gold"}, 3) is True
    assert reciprocal_rank(ranked, {"gold"}) == 0.5


def test_aggregate_metrics_is_deterministic() -> None:
    rows = [
        {"gold_chunk_ids": ["a"], "systems": {"demo": {"top_ids": ["a", "b", "c"]}}},
        {"gold_chunk_ids": ["z"], "systems": {"demo": {"top_ids": ["x", "z", "y"]}}},
    ]
    expected = {
        "recall_at_1": 0.5,
        "recall_at_3": 1.0,
        "recall_at_5": 1.0,
        "recall_at_10": 1.0,
        "mrr": 0.75,
    }
    assert aggregate_metrics(rows, "demo") == expected
