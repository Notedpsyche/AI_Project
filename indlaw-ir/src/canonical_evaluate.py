"""Run one canonical, reproducible Doc2Dial retrieval evaluation."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

import torch
import yaml

from doc2dial_retrieval.data import load_dialogues, tokenize
from doc2dial_retrieval.metrics import aggregate_metrics
from doc2dial_retrieval.search import SearchEngine

ROOT = Path(__file__).resolve().parents[1]
MODES = ("bm25", "semantic", "hybrid")


def validation_examples(root: Path, limit: int = 200) -> list[dict]:
    """Select the first 200 grounded validation turns deterministically."""
    dialogues = load_dialogues(root / "data/raw/doc2dial", "validation")
    chunks = [
        json.loads(line)
        for line in (root / "data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    span_to_chunk = {
        (chunk["doc_id"], span_id): chunk["chunk_id"]
        for chunk in chunks
        for span_id in chunk["span_ids"]
    }
    chunk_text = {chunk["chunk_id"]: chunk["text"] for chunk in chunks}
    examples = []
    for domain in sorted(dialogues):
        for doc_id in sorted(dialogues[domain]):
            for dialogue in dialogues[domain][doc_id]:
                history: list[dict[str, str]] = []
                for turn in dialogue.get("turns", []):
                    references = [
                        ref
                        for ref in turn.get("references", [])
                        if ref.get("label") in {"precondition", "solution"}
                    ]
                    gold = sorted(
                        {
                            span_to_chunk[(doc_id, str(ref["sp_id"]))]
                            for ref in references
                            if (doc_id, str(ref["sp_id"])) in span_to_chunk
                        }
                    )
                    if gold:
                        query_tokens = set(tokenize(turn["utterance"]))
                        gold_tokens = set(tokenize(" ".join(chunk_text[item] for item in gold)))
                        examples.append(
                            {
                                "query_id": f"{dialogue['dial_id']}:{turn['turn_id']}",
                                "domain": domain,
                                "doc_id": doc_id,
                                "query": turn["utterance"],
                                "history": list(history),
                                "gold_chunk_ids": gold,
                                "difficulty": {
                                    "conversational": bool(history),
                                    "short_query": len(query_tokens) <= 4,
                                    "long_query": len(query_tokens) >= 20,
                                    "lexical_overlap": len(query_tokens & gold_tokens) >= 2,
                                },
                            }
                        )
                    history.extend([{"role": turn["role"], "content": turn["utterance"]}])
                    if len(examples) >= limit:
                        return examples
    return examples


def load_config(root: Path, config_path: str) -> dict:
    return yaml.safe_load((root / config_path).read_text(encoding="utf-8"))


def evaluate_model(
    root: Path, config_path: str, examples: list[dict], model_key: str
) -> tuple[dict, list[dict]]:
    engine = SearchEngine(root, config_path)
    engine.config["search"]["final_top_k"] = 10
    built_queries = [
        engine.build_query(
            example["query"], example["history"], engine.config["query"]["history_turns"]
        )
        for example in examples
    ]
    encode_start = time.perf_counter()
    query_vectors = engine.dense.encode_queries(built_queries, batch_size=64)
    embedding_seconds = time.perf_counter() - encode_start
    rows = []
    latencies = []
    for example, query_vector in zip(examples, query_vectors):
        start = time.perf_counter()
        systems, best_score = engine.search_all(example["query"], example["history"], query_vector)
        latencies.append(time.perf_counter() - start)
        row = dict(example)
        row["systems"] = {}
        for mode, results in systems.items():
            row["systems"][f"{model_key}_{mode}"] = {
                "top_ids": [result.chunk.chunk_id for result in results],
                "results": [result.as_dict() for result in results],
                "best_semantic_cosine": best_score,
            }
        rows.append(row)
    metrics = {}
    for mode in MODES:
        metrics[f"{model_key}_{mode}"] = aggregate_metrics(
            [
                {
                    "gold_chunk_ids": row["gold_chunk_ids"],
                    "systems": {mode: row["systems"][f"{model_key}_{mode}"]},
                }
                for row in rows
            ],
            mode,
        )
    timing = {
        "embedding_generation_seconds": embedding_seconds,
        "average_query_retrieval_seconds": statistics.mean(latencies),
        "median_query_retrieval_seconds": statistics.median(latencies),
        "p95_query_retrieval_seconds": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)],
    }
    return {"metrics": metrics, "timing": timing, "config": load_config(root, config_path)}, rows


def merge_rows(examples: list[dict], model_rows: list[tuple[str, list[dict]]]) -> list[dict]:
    merged = {row["query_id"]: dict(row) for row in examples}
    for model_key, rows in model_rows:
        for row in rows:
            merged[row["query_id"]].setdefault("systems", {}).update(row["systems"])
    return list(merged.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    examples = validation_examples(ROOT, args.limit)
    model_runs = []
    rows_by_model = []
    model_configs = (
        ("bge_small", "configs/config.yaml"),
        ("bge_base", "configs/config_bge_base.yaml"),
    )
    for model_key, config_path in model_configs:
        summary, rows = evaluate_model(ROOT, config_path, examples, model_key)
        model_runs.append({"model": model_key, **summary})
        rows_by_model.append((model_key, rows))
    rows = merge_rows(examples, rows_by_model)
    all_metrics = {}
    for run in model_runs:
        all_metrics.update(run["metrics"])
    canonical = {
        "experiment_id": "canonical_doc2dial_bge_comparison_001",
        "date": str(date.today()),
        "dataset": "Doc2Dial v1.0.1",
        "num_queries": len(examples),
        "chunk_count": 14738,
        "evaluation": {
            "gold_labels": "precondition_or_solution_span_references",
            "cutoffs": [1, 3, 5, 10],
            "rrf_k": 60,
            "dense_top_k": 50,
            "bm25_top_k": 50,
            "final_top_k": 10,
            "history_turns": 3,
        },
        "runtime": {
            "pytorch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE",
        },
        "runs": model_runs,
        "metrics": all_metrics,
    }
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "canonical_evaluation.json").write_text(
        json.dumps(canonical, indent=2) + "\n", encoding="utf-8"
    )
    (results_dir / "canonical_evaluation_details.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
    )
    print(json.dumps(canonical, indent=2))


if __name__ == "__main__":
    main()
