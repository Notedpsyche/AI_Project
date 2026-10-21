"""Export a local, unjudged candidate sheet for human relevance labeling."""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path

from doc2dial_retrieval.search import SearchEngine, result_dicts

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    engine = SearchEngine(ROOT)
    questions = [json.loads(line) for line in (ROOT / "evaluation/question_bank.jsonl").read_text(encoding="utf-8").splitlines() if line]
    output = ROOT / "evaluation/candidates.jsonl"
    latencies: list[float] = []
    with output.open("w", encoding="utf-8") as handle:
        for item in questions:
            started = time.perf_counter()
            systems, _ = engine.search_all(item["query"], item.get("history", []))
            latencies.append((time.perf_counter() - started) * 1000)
            rows = result_dicts(systems["hybrid"][:15])
            handle.write(json.dumps({"query_id": item["query_id"], "query": item["query"], "question_family": item["question_family"], "candidates": [{"chunk_id": row["chunk_id"], "title": row["title"], "source_url": row["source_url"], "text": row["text"]} for row in rows]}, ensure_ascii=False) + "\n")
    print(f"Wrote unjudged candidates to {output}; a human must provide relevance labels")
    ordered = sorted(latencies)
    print(f"Warmed retrieval over {len(ordered)} pilot questions: p50={statistics.median(ordered):.1f} ms, p95={ordered[math.ceil(.95 * len(ordered)) - 1]:.1f} ms (excludes startup, answer composition, browser)")


if __name__ == "__main__":
    main()
