"""Doc2Dial loading, normalization, and structure-aware chunking."""

# Compact schema normalization code contains deliberate evidence-field lines.
# ruff: noqa: E501, E702

from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def parse_parent_titles(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, list):
            raise ValueError("parent_titles string must represent a list")
        return [str(item) for item in parsed if str(item).strip()]
    raise ValueError(f"Unsupported parent_titles value: {type(value).__name__}")


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    domain: str
    title: str
    heading_path: list[str]
    section_id: str
    text: str
    span_ids: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_documents(raw_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    path = raw_dir / "doc2dial_doc.json"
    return json.loads(path.read_text(encoding="utf-8"))["doc_data"]


def load_dialogues(raw_dir: Path, split: str) -> dict[str, dict[str, list[dict[str, Any]]]]:
    path = raw_dir / f"doc2dial_dial_{split}.json"
    return json.loads(path.read_text(encoding="utf-8"))["dial_data"]


def _split_text(text: str, max_tokens: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    parts: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in sentences:
        words = sentence.split()
        if current and count + len(words) > max_tokens:
            parts.append(" ".join(current))
            current, count = [], 0
        if len(words) > max_tokens:
            for start in range(0, len(words), max_tokens):
                if current:
                    parts.append(" ".join(current)); current, count = [], 0
                parts.append(" ".join(words[start : start + max_tokens]))
        else:
            current.extend(words)
            count += len(words)
    if current:
        parts.append(" ".join(current))
    return [part for part in parts if part.strip()]


def build_chunks(raw_dir: Path, max_tokens: int = 512) -> tuple[list[Chunk], dict[str, int]]:
    documents = load_documents(raw_dir)
    chunks: list[Chunk] = []
    exact_keys: set[tuple[str, str]] = set()
    duplicate_count = 0
    section_count = 0
    span_seen: set[tuple[str, str]] = set()
    for domain, domain_docs in documents.items():
        for doc_id, document in domain_docs.items():
            sections: dict[str, dict[str, Any]] = {}
            for span_id, span in document.get("spans", {}).items():
                key = (doc_id, str(span_id))
                if key in span_seen:
                    raise ValueError(f"Duplicate span identity: {key}")
                span_seen.add(key)
                section_id = str(span.get("id_sec", ""))
                section = sections.setdefault(section_id, {"spans": [], "title": span.get("title", ""), "parents": span.get("parent_titles", [])})
                section["spans"].append((str(span_id), span))
            for section_id, section in sections.items():
                section_count += 1
                title = str(section["title"] or document.get("title", ""))
                heading_path = parse_parent_titles(section["parents"])
                if title and (not heading_path or heading_path[-1] != title):
                    heading_path = [*heading_path, title]
                text = " ".join(str(span.get("text_sec") or span.get("text_sp") or "").strip() for _, span in section["spans"])
                text = " ".join(text.split())
                if not text:
                    continue
                for part_no, part in enumerate(_split_text(text, max_tokens), 1):
                    chunk_id = f"{doc_id}::{section_id}::{part_no}"
                    key = (doc_id, " ".join(tokenize(part)))
                    if key in exact_keys:
                        duplicate_count += 1
                        continue
                    exact_keys.add(key)
                    chunks.append(Chunk(chunk_id, doc_id, domain, str(document.get("title", title)), heading_path, section_id, part, [str(item[0]) for item in section["spans"]]))
    return chunks, {"sections_seen": section_count, "exact_duplicates_removed": duplicate_count, "span_keys_seen": len(span_seen)}


def write_chunks(chunks: list[Chunk], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(chunk.as_dict(), ensure_ascii=False) for chunk in chunks) + "\n", encoding="utf-8")
