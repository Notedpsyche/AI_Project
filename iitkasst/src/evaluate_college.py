"""Run fair, equal-cutoff retrieval evaluation on human-reviewed queries."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from college_experiment import ROOT, corpus_hash, evaluate, load_judgments
from doc2dial_retrieval.search import SearchEngine


def main() -> None:
    items = load_judgments()
    engine = SearchEngine(ROOT)
    model_path = ROOT / "models/college_reranker.json"
    reranker = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else None
    outputs = {}
    details = []
    for split in ("train", "dev", "test"):
        subset = [item for item in items if item["split"] == split]
        if subset:
            outputs[split], rows = evaluate(engine, subset, reranker)
            details.extend(rows)
    report = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_sha256": corpus_hash(),
        "model": engine.config["model"]["name"],
        "cutoffs": {"recall": 5, "mrr": 10, "ndcg": 10},
        "reranker_present": reranker is not None,
        "note": "Answer support and abstention require independent human review; not inferred from ranking metrics.",
        "splits": outputs,
    }
    out_dir = ROOT / "results/college"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "rankings.jsonl").write_text("\n".join(json.dumps(row) for row in details) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
