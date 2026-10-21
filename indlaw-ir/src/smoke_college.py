"""Check the 20 reviewed pilot behaviors against a running local backend.

This is a functional smoke test, not a human relevance judgment or benchmark.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

# Required answer fragments are verified against the 2026-10-08 local source
# snapshot. Refusal and clarification cases check behavior, not answer facts.
EXPECTATIONS = {
    "q001": (False, ("JEE", "JoSAA", "https://admission.iiitkottayam.ac.in/")),
    "q002": (False, ("JEE",)),
    "q003": (False, ("https://admission.iiitkottayam.ac.in/",)),
    "q004": (True, ("specify", "document checklist")),
    "q005": (False, ("1,59,800",)),
    "q006": (False, ("37,500",)),
    "q007": (False, ("Caution Deposit", "14,000")),
    "q008": (True, ("couldn't verify",)),
    "q009": (False, ("no direct financial assistance",)),
    "q010": (False, ("State Government",)),
    "q011": (False, ("providing all necessary documents",)),
    "q012": (False, ("Artificial Intelligence and Data Science",)),
    "q013": (False, ("Mathematics and Computing",)),
    "q014": (False, ("Computer Science foundation",)),
    "q015": (False, ("Signal Processing",)),
    "q016": (False, ("Cyber security",)),
    "q017": (True, ("couldn't verify",)),
    "q018": (True, ("couldn't verify",)),
    "q019": (True, ("couldn't verify",)),
    "q020": (True, ("specify", "payment instructions")),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    bank = [json.loads(line) for line in (ROOT / "evaluation/question_bank.jsonl").read_text(encoding="utf-8").splitlines() if line]
    items = [item for item in bank if item["query_id"] in EXPECTATIONS]
    if {item["query_id"] for item in items} != set(EXPECTATIONS):
        raise ValueError("A reviewed pilot question is missing from the question bank")
    failures: list[str] = []
    for item in items:
        payload = json.dumps({"message": item["query"], "conversation": item.get("history", [])}).encode()
        request = Request(args.base_url.rstrip("/") + "/api/chat", payload, {"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        refused, fragments = EXPECTATIONS[item["query_id"]]
        answer = result["answer"].casefold()
        issues = [fragment for fragment in fragments if fragment.casefold() not in answer]
        if result["refused"] != refused:
            issues.append(f"refused={result['refused']}, expected {refused}")
        if item["query_id"] == "q007" and "1,59,800" in answer:
            issues.append("tuition leaked into caution-deposit answer")
        if item["query_id"] == "q020" and not result["context_used"]:
            issues.append("follow-up context was lost")
        if issues:
            failures.append(f"{item['query_id']}: {', '.join(issues)}")
        else:
            print(f"{item['query_id']}: pass")
    if failures:
        raise SystemExit("Pilot smoke failed:\n" + "\n".join(failures))
    print(f"Pilot smoke: {len(items)}/{len(items)} expected behaviors passed; not a quality benchmark")


if __name__ == "__main__":
    main()
