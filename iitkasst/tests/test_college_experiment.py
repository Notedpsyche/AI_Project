import json

import pytest

from college_experiment import load_judgments, query_metrics


def test_recall_uses_fraction_of_all_relevant_passages():
    metrics = query_metrics({"a", "b"}, ["a", "x", "y"])
    assert metrics["recall_at_5"] == 0.5
    assert metrics["mrr_at_10"] == 1.0


def test_same_gold_passage_cannot_cross_splits(tmp_path):
    folder = tmp_path / "evaluation"
    folder.mkdir()
    records = [
        {"query_id": "1", "query": "fee", "split": "train", "question_family": "a", "gold_chunk_ids": ["same"], "answerable": True, "answer_fact": "x", "expected_behavior": "answer"},
        {"query_id": "2", "query": "fee?", "split": "test", "question_family": "b", "gold_chunk_ids": ["same"], "answerable": True, "answer_fact": "x", "expected_behavior": "answer"},
    ]
    (folder / "judgments.jsonl").write_text("\n".join(json.dumps(row) for row in records))
    with pytest.raises(ValueError, match="crosses splits"):
        load_judgments(tmp_path)
