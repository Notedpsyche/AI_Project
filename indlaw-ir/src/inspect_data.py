"""Inspect the downloaded archive without assuming a Doc2Dial schema."""

# The notes intentionally embed long observed-schema evidence lines.
# ruff: noqa: E501

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "raw" / "doc2dial"
NOTES = ROOT / "docs" / "data_notes.md"


def shape(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in list(value.items())[:20]}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "item": shape(value[0], depth + 1) if value else None}
    return type(value).__name__


def find_keys(value: Any, names: set[str], path: str = "$") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in names:
                found.append((f"{path}.{key}", item))
            found.extend(find_keys(item, names, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value[:10]):
            found.extend(find_keys(item, names, f"{path}[{index}]"))
    return found


def main() -> None:
    files = sorted(ARCHIVE.glob("*.json"))
    records = []
    for path in files:
        value = json.loads(path.read_text(encoding="utf-8"))
        records.append((path, value))
    domains = Counter()
    lines = ["# Dataset Notes", "", f"Source: `{ARCHIVE}`", "", f"JSON files: **{len(files)}**", ""]
    lines += ["## Files", ""]
    for path, value in records:
        lines.append(f"- `{path.name}`: top-level `{type(value).__name__}`, shape `{json.dumps(shape(value), ensure_ascii=False)[:500]}`")
        for key_path, item in find_keys(value, {"domain", "doc_id", "document_id", "span_id", "grounding", "dialogue", "parent_titles"}):
            lines.append(f"  - `{key_path}`: `{type(item).__name__}`")
        if isinstance(value, dict):
            for key in ("domain", "doc_id", "document_id"):
                item = value.get(key)
                if isinstance(item, str):
                    domains[item] += 1
    lines += ["", "## Observed Top-Level Keys", ""]
    key_counts = Counter(key for _, value in records if isinstance(value, dict) for key in value)
    lines += [f"- `{key}`: {count} files" for key, count in key_counts.items()]
    lines += ["", "## Domain-Like Values", "", *(f"- `{key}`: {count}" for key, count in domains.items())]
    if records:
        lines += ["", "## Complete Example From First File", "", "```json", json.dumps(records[0][1], indent=2, ensure_ascii=False)[:12000], "```"]
    lines += ["", "## Compatibility Finding", "", "This inspection uses the downloaded Doc2Dial release. All downstream code must use the observed document, span, dialogue, and grounding fields documented above."]
    NOTES.parent.mkdir(parents=True, exist_ok=True)
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Inspected {len(files)} JSON files")
    print(f"Notes written to {NOTES}")


if __name__ == "__main__":
    main()
