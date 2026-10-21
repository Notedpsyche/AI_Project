# ruff: noqa: E501
"""Report chunk duplication and result-diversity risks without changing chunks."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def main() -> None:
    chunks = [json.loads(line) for line in (ROOT / "data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_text: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        by_text[normalized(chunk["text"])].append(chunk)
    groups = [group for group in by_text.values() if len(group) > 1]
    title_like = [chunk for chunk in chunks if normalized(chunk["text"]) in {normalized(chunk["title"]), normalized(chunk["heading_path"][-1]) if chunk["heading_path"] else ""}]
    report = {
        "chunks": len(chunks),
        "exact_duplicate_groups_remaining": len(groups),
        "exact_duplicate_chunks_beyond_representative": sum(len(group) - 1 for group in groups),
        "repeated_section_text_groups": sum(len({chunk["section_id"] for chunk in group}) > 1 for group in groups),
        "cross_document_exact_groups": sum(len({chunk["doc_id"] for chunk in group}) > 1 for group in groups),
        "short_chunks_under_8_tokens": sum(len(chunk["text"].split()) < 8 for chunk in chunks),
        "title_like_chunks": len(title_like),
        "long_chunks_over_512_tokens": sum(len(chunk["text"].split()) > 512 for chunk in chunks),
        "top_exact_duplicates": [{"count": len(group), "text": group[0]["text"][:240], "chunk_ids": [chunk["chunk_id"] for chunk in group[:10]]} for group in sorted(groups, key=len, reverse=True)[:20]],
    }
    output = ROOT / "results/duplicate_audit.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
