"""Evaluate agent-reviewed development regressions; never report as a held-out benchmark."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.college_answer import grounded_answer  # noqa: E402
from backend.services.college_query import resolve_scope  # noqa: E402
from backend.services.college_select import select_evidence  # noqa: E402
from doc2dial_retrieval.search import SearchEngine, result_dicts  # noqa: E402


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def citation_supported(answer: str, evidence: list[dict]) -> bool:
    claims = re.findall(r"•\s*(.*?)\s*\[(\d+)\]", answer, re.S)
    if not claims:
        return False
    for claim, rank_text in claims:
        rank = int(rank_text)
        if rank < 1 or rank > len(evidence):
            return False
        support = str(evidence[rank - 1].get("section", "")) + " " + str(evidence[rank - 1]["text"])
        if _compact(claim) not in _compact(support):
            return False
    return True


def main() -> None:
    cases = [json.loads(line) for line in (ROOT / "evaluation/development_regressions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    engine = SearchEngine(ROOT)
    original_cutoff = engine.config["search"]["final_top_k"]
    engine.config["search"]["final_top_k"] = 10
    rows = []
    categories: dict[str, list[dict]] = defaultdict(list)
    try:
        for case in cases:
            scope = resolve_scope(case["query"], case.get("history", []))
            systems, _ = engine.search_all(case["query"], case.get("history", []))
            fused = result_dicts(systems["hybrid"])
            for item in fused:
                item["section"] = item["heading_path"][-1] if item["heading_path"] else item["title"]
                item["span_id"] = ""
            evidence = select_evidence(scope, fused, top_k=3)
            for rank, item in enumerate(evidence, 1):
                item["rank"] = rank
            answer, refused = grounded_answer(scope, evidence)
            answer_folded = answer.casefold()
            missing = [fragment for fragment in case["required_fragments"] if fragment.casefold() not in answer_folded]
            forbidden = [fragment for fragment in case["forbidden_fragments"] if fragment.casefold() in answer_folded]
            expected_answer = case["expected_behavior"] == "answer"
            cited = citation_supported(answer, evidence) if not refused else True
            behavior_ok = (expected_answer and not refused) or (not expected_answer and refused)
            correct = behavior_ok and not missing and not forbidden and cited
            gold = set(case["gold_chunk_ids"])
            fused_ids = [item["chunk_id"] for item in fused[:10]]
            selected_ids = [item["chunk_id"] for item in evidence]
            retrieval_recall = len(gold.intersection(fused_ids)) / len(gold) if gold else None
            row = {
                "query_id": case["query_id"],
                "category": case["category"],
                "query": case["query"],
                "expected_behavior": case["expected_behavior"],
                "scope": {"topic": scope.topic, "intent": scope.intent, "programme": scope.programme, "admission_year": scope.admission_year},
                "fused_top_10": fused_ids,
                "selected_evidence": selected_ids,
                "gold_chunk_ids": sorted(gold),
                "retrieval_recall_at_10": retrieval_recall,
                "selected_gold_hit": bool(gold.intersection(selected_ids)) if gold else None,
                "answer": answer,
                "refused": refused,
                "citation_supported": cited,
                "missing_fragments": missing,
                "forbidden_fragments_present": forbidden,
                "correct": correct,
                "failure_type": (
                    "unnecessary_abstention" if expected_answer and refused
                    else "unsupported_answer" if not expected_answer and not refused
                    else "irrelevant_answer" if expected_answer and not refused and (missing or forbidden)
                    else "citation_failure" if not cited
                    else ""
                ),
            }
            rows.append(row)
            categories[case["category"]].append(row)
    finally:
        engine.config["search"]["final_top_k"] = original_cutoff
    answered = [row for row in rows if row["expected_behavior"] == "answer"]
    report = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "label": "agent-reviewed development regression; not an independent accuracy benchmark",
        "cases": len(rows),
        "correct": sum(row["correct"] for row in rows),
        "answer_cases": len(answered),
        "retrieval_recall_at_10": sum(row["retrieval_recall_at_10"] for row in answered) / len(answered),
        "selected_evidence_hit_rate": sum(row["selected_gold_hit"] for row in answered) / len(answered),
        "unsupported_answers": sum(row["failure_type"] == "unsupported_answer" for row in rows),
        "irrelevant_answers": sum(row["failure_type"] == "irrelevant_answer" for row in rows),
        "unnecessary_abstentions": sum(row["failure_type"] == "unnecessary_abstention" for row in rows),
        "citation_failures": sum(row["failure_type"] == "citation_failure" for row in rows),
        "categories": {
            category: {"cases": len(items), "correct": sum(item["correct"] for item in items)}
            for category, items in sorted(categories.items())
        },
    }
    output = ROOT / "results/college/development_regression.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": report, "rows": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["correct"] != report["cases"]:
        print("Failures:")
        for row in rows:
            if not row["correct"]:
                print(f"- {row['query_id']} [{row['failure_type'] or 'expectation_mismatch'}]: {row['answer']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
