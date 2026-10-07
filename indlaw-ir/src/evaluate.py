"""Evaluate BM25, semantic, and hybrid Recall@5 on validation grounding."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

from doc2dial_retrieval.data import load_dialogues
from doc2dial_retrieval.search import SearchEngine

ROOT = Path(__file__).resolve().parents[1]


def validation_examples(limit: int = 200) -> list[dict]:
    dialogues = load_dialogues(ROOT / "data/raw/doc2dial", "validation")
    chunks = [json.loads(line) for line in (ROOT / "data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    span_to_chunk = {(chunk["doc_id"], span_id): chunk["chunk_id"] for chunk in chunks for span_id in chunk["span_ids"]}
    examples = []
    for domain in sorted(dialogues):
        for doc_id in sorted(dialogues[domain]):
            for dialogue in dialogues[domain][doc_id]:
                history: list[dict[str, str]] = []
                for turn in dialogue.get("turns", []):
                    references = [ref for ref in turn.get("references", []) if ref.get("label") in {"precondition", "solution"}]
                    gold = sorted({span_to_chunk[(doc_id, str(ref["sp_id"]))] for ref in references if (doc_id, str(ref["sp_id"])) in span_to_chunk})
                    if gold:
                        examples.append({"query_id": f"{dialogue['dial_id']}:{turn['turn_id']}", "domain": domain, "doc_id": doc_id, "query": turn["utterance"], "history": list(history), "gold_chunk_ids": gold})
                    history.extend([{"role": turn["role"], "content": turn["utterance"]}])
                    if len(examples) >= limit:
                        return examples
    return examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--output-stem", default="evaluation")
    args = parser.parse_args()
    engine = SearchEngine(ROOT, args.config)
    examples = validation_examples()
    built_queries = [
        engine.build_query(example["query"], example["history"], engine.config["query"]["history_turns"])
        for example in examples
    ]
    query_vectors = engine.dense.encode_queries(built_queries)
    results = []
    for example, query_vector in zip(examples, query_vectors):
        row = {**example, "systems": {}}
        systems, best_score = engine.search_all(example["query"], example["history"], query_vector)
        for mode, hits in systems.items():
            ids = [hit.chunk.chunk_id for hit in hits]
            row["systems"][mode] = {"top5": ids, "best_semantic_cosine": best_score, "recall_at_5": bool(set(ids) & set(example["gold_chunk_ids"]))}
        results.append(row)
    metrics = {mode: sum(row["systems"][mode]["recall_at_5"] for row in results) / len(results) for mode in ("bm25", "semantic", "hybrid")}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / f"results/{args.output_stem}.json").write_text(json.dumps({"num_queries": len(results), **{f"{mode}_recall_at_5": value for mode, value in metrics.items()}}, indent=2) + "\n", encoding="utf-8")
    (ROOT / f"results/{args.output_stem}_details.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    (ROOT / f"results/{args.output_stem}_demo_queries.json").write_text(json.dumps(results[:10], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"num_queries": len(results), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
