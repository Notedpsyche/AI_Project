from evaluate_wmd import ndcg, recall, reciprocal_rank


def test_ranking_metrics_use_gold_chunk_ids_and_grades() -> None:
    rows = [{"chunk_id": "wrong"}, {"chunk_id": "best"}, {"chunk_id": "partial"}]
    gold = {"best", "partial"}
    assert recall(rows, gold, 2) == 0.5
    assert reciprocal_rank(rows, gold) == 0.5
    assert 0.0 < ndcg(rows, {"best": 3, "partial": 1}) < 1.0
