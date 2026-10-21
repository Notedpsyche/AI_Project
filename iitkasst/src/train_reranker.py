"""Train an optional compact relevance reranker from human-labeled query passages."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from backend.services.college_select import features
from college_experiment import ROOT, corpus_hash, evaluate, load_judgments
from doc2dial_retrieval.search import SearchEngine, result_dicts

FEATURE_NAMES = ["semantic", "log_bm25", "relative_bm25", "rrf", "title_overlap", "body_overlap"]


def main() -> None:
    judgments = load_judgments()
    train = [item for item in judgments if item["split"] == "train" and item["answerable"]]
    if len(train) < 5:
        raise ValueError("At least five human-judged answerable training questions are required even for a pilot")
    engine = SearchEngine(ROOT)
    vectors: list[list[float]] = []
    labels: list[int] = []
    covered = 0
    for item in train:
        systems, _ = engine.search_all(item["query"], item.get("history", []))
        candidates = result_dicts(systems["hybrid"])
        max_bm25 = max((float(row.get("bm25_score") or 0.0) for row in candidates), default=1.0)
        positives = set(item["gold_chunk_ids"])
        pool = [row for row in candidates if row["chunk_id"] in positives]
        if not pool:
            continue  # A reranker cannot recover evidence the retriever did not find.
        covered += 1
        pool += [row for row in candidates if row["chunk_id"] not in positives][:5]
        for row in pool:
            row["section"] = row["heading_path"][-1] if row["heading_path"] else row["title"]
            vectors.append(features(item["query"], row, max_bm25))
            labels.append(int(row["chunk_id"] in positives))
    if covered < 5 or len(set(labels)) < 2:
        raise ValueError("Too few retrieved positive/negative examples for a defensible pilot")
    scaler = StandardScaler().fit(vectors)
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42).fit(scaler.transform(vectors), labels)
    weights = classifier.coef_[0] / scaler.scale_
    intercept = float(classifier.intercept_[0] - np.dot(weights, scaler.mean_))
    artifact = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_sha256": corpus_hash(),
        "feature_names": FEATURE_NAMES,
        "weights": weights.tolist(),
        "intercept": intercept,
        "training_queries": len(train),
        "retrieved_positive_queries": covered,
        "training_pairs": len(labels),
        "deploy": False,
        "note": "Candidate model only. Independently review held-out ranking and answer safety before deployment.",
    }
    out = ROOT / "models/college_reranker.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    for split in ("dev", "test"):
        subset = [item for item in judgments if item["split"] == split]
        if subset:
            summary, _ = evaluate(engine, subset, artifact)
            print(split, json.dumps(summary))
    print(f"Saved non-deployed candidate reranker: {out}")


if __name__ == "__main__":
    main()
