"""Curated, local-only collection of public IIIT Kottayam applicant material."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Comment
from pypdf import PdfReader

from .data import Chunk

YEAR_RE = re.compile(r"\b20(?:2[0-9]|3[0-9])\b")
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
MAX_BYTES = 10_000_000


def _official(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (
        parsed.hostname == "iiitkottayam.ac.in"
        or (parsed.hostname or "").endswith(".iiitkottayam.ac.in")
    )


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported source manifest schema")
    sources = payload["sources"]
    if not sources or len({item["id"] for item in sources}) != len(sources):
        raise ValueError("Manifest must contain unique source IDs")
    for item in sources:
        if not _official(item["fetch_url"]) or not _official(item["source_url"]):
            raise ValueError(f"Non-official source URL: {item['id']}")
        if item["document_type"] not in {"html", "pdf"}:
            raise ValueError(f"Unsupported document type: {item['id']}")
    return sources


def collect_sources(manifest: Path, raw_dir: Path, delay_seconds: float = 0.5) -> list[dict]:
    """Fetch only allowlisted URLs; never publish the downloaded bytes."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    inventory: list[dict] = []
    for item in load_manifest(manifest):
        suffix = ".pdf" if item["document_type"] == "pdf" else ".html"
        destination = raw_dir / f"{item['id']}{suffix}"
        request = Request(item["fetch_url"], headers={"User-Agent": "IIITK-Applicant-Assistant/0.1 (local academic project)"})
        with urlopen(request, timeout=30) as response:
            if not _official(response.url):
                raise ValueError(f"Redirect left institute domain: {item['id']}")
            content_type = response.headers.get_content_type()
            expected = "application/pdf" if suffix == ".pdf" else "text/html"
            if content_type != expected:
                raise ValueError(f"Unexpected type for {item['id']}: {content_type}")
            content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError(f"Source exceeds {MAX_BYTES} bytes: {item['id']}")
        destination.write_bytes(content)
        inventory.append({
            **item,
            "raw_file": destination.name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "byte_count": len(content),
        })
        time.sleep(delay_seconds)
    (raw_dir / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory


def _clean(text: str) -> str:
    return " ".join(text.split())


def _split_words(text: str, max_words: int) -> list[str]:
    words = text.split()
    parts = [words[index:index + max_words] for index in range(0, len(words), max_words)]
    if len(parts) > 1 and len(parts[-1]) < min(30, max_words // 4):
        parts[-2].extend(parts.pop())
    return [" ".join(part) for part in parts]


def _table_rows(soup: BeautifulSoup) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for table in list(soup.find_all("table")):
        heading = table.find_previous(list(HEADING_TAGS))
        section = _clean(heading.get_text(" ", strip=True)) if heading else "Table"
        parent = table.find_previous("h4")
        if parent:
            parent_text = _clean(parent.get_text(" ", strip=True))
            if parent_text and parent_text != section:
                section = parent_text + " — " + section
        if "documents" in section.lower():
            opening = _clean(" ".join(row.get_text(" ", strip=True) for row in table.find_all("tr")[:3]))
            label = _clean(heading.get_text(" ", strip=True)) if heading else "Documents"
            if re.search(r"downloaded from\s+DASA\s+website", opening, re.I):
                section = "Admission 2026 [DASA] — " + label
            elif re.search(r"downloaded from\s+JoSAA\s+website", opening, re.I):
                section = "Admission 2026 [JoSAA/CSAB] — " + label
        headers: list[str] = []
        for tr in table.find_all("tr"):
            raw_cells = [_clean(cell.get_text(" ", strip=True)) for cell in tr.find_all(["td", "th"], recursive=False)]
            if not any(raw_cells):
                continue
            if tr.find("th") or (not raw_cells[0] and len(raw_cells) > 1):
                headers = [cell for cell in raw_cells[1:] if cell]
                continue
            cells = [cell for cell in raw_cells if cell]
            # Some fee tables place two distinct charges in one HTML row.
            # An embedded text label starts a new fact, not a later semester cell.
            label_starts = [0] + [
                index for index in range(2, len(cells) - 1)
                if re.search(r"[A-Za-z]", cells[index]) and not re.search(r"\d", cells[index])
            ]
            for start, end in zip(label_starts, [*label_starts[1:], len(cells)]):
                label = cells[start]
                values = cells[start + 1:end]
                if start:
                    row = f"{label}; Amount: {'; '.join(values)}"
                else:
                    labeled = [f"{headers[index] if index < len(headers) else f'Column {index + 1}'}: {value}" for index, value in enumerate(values)]
                    row = f"{label}; " + "; ".join(labeled) if labeled else label
                if len(row.split()) >= 4:
                    rows.append((section, row))
        table.decompose()
    return rows


def extract_html(content: bytes) -> list[tuple[str, str]]:
    soup = BeautifulSoup(content, "html.parser")
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for tag in soup.find_all(["script", "style", "noscript", "nav", "footer", "form", "iframe", "svg"]):
        tag.decompose()
    root = soup.select_one(".container") or soup.body or soup
    rows = _table_rows(root)
    sections: list[tuple[str, str]] = []
    heading = "Overview"
    buffer: list[str] = []
    def flush() -> None:
        nonlocal buffer
        text = _clean(" ".join(buffer))
        if len(text.split()) >= 8:
            sections.extend((heading, part) for part in _split_words(text, 220))
        buffer = []
    # Splitting on visible line boundaries keeps labels and their facts together.
    heading_texts = {_clean(tag.get_text(" ", strip=True)) for tag in root.find_all(HEADING_TAGS)}
    for line in root.get_text("\n", strip=True).splitlines():
        line = _clean(line)
        if not line or line == "insert_link":
            continue
        if line in heading_texts:
            flush()
            heading = line
        else:
            buffer.append(line)
            if len(" ".join(buffer).split()) >= 180:
                flush()
    flush()
    return sections + rows


def extract_pdf(content: bytes) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    reader = PdfReader(BytesIO(content))
    for number, page in enumerate(reader.pages, 1):
        text = _clean(page.extract_text() or "")
        if len(text.split()) < 8:
            continue
        sections.extend((f"Page {number}", part) for part in _split_words(text, 220))
    return sections


def _semantic_sections(section: str, text: str) -> list[tuple[str, str]]:
    """Separate recurring programme-list, admission, and fee blocks in site HTML."""
    admission = re.search(r"\bAdmission to the B\.Tech/B\.Tech-MS programme\b", text, re.I)
    if admission and re.search(r"\bB\.Tech/B\.Tech-MS\s*\(1\)", text[:admission.start()], re.I):
        programmes = text[:admission.start()].strip(" .")
        remainder = text[admission.start():].strip()
        fee = re.search(r"\(1\)\s*Fee Structure", remainder, re.I)
        if fee:
            remainder = remainder[:fee.start()].strip(" .")
        parts = []
        if programmes:
            parts.append(("Available B.Tech programmes", programmes))
        if remainder:
            parts.append(("B.Tech admission procedure", remainder))
        return parts
    if admission and "admission" not in section.lower():
        return [("B.Tech admission procedure", text)]
    return [(section, text)]


def _chunk_topics(source_topics: list[str], section: str, text: str) -> list[str]:
    combined = f"{section} {text}".lower()
    if re.search(r"\b(documents?|certificates?)\b.*\b(required|verification|reporting|ready|produced)\b", combined):
        return ["documents"]
    topics: set[str] = set()
    if re.search(r"\b(fee|tuition|payment|pay|deposit|mess advance)\b", combined):
        topics.add("fees")
    if re.search(r"\b(portal|dashboard|log\s*in|login|final submit|application preview)\b", combined):
        topics.add("portal")
    if re.search(r"\b(scholarships?|financial assistance|national scholarship portal)\b", combined):
        topics.add("scholarships")
    if ("available b.tech programmes" in section.lower()
            or re.search(r"\bB\.Tech(?:\.|\s)+(?:in|programme|program)\b", combined, re.I)
            or re.search(r"\b(?:e-?M\.Tech|M\.Tech|PhD)\b", combined, re.I)
            or "curriculum" in combined):
        topics.add("programmes")
    if re.search(r"\b(admission|jee|josaa|csab|dasa|reporting|counselling)\b", combined):
        topics.add("admissions")
    if re.search(r"\bplacements?|recruiters?|career outcomes?\b", combined):
        topics.add("placements")
    if re.search(r"\bdepartments?|faculty divisions?\b", combined):
        topics.add("departments")
    if re.search(r"\b(hostels?|campus facilities|library|laborator(?:y|ies)|sports facilities)\b", combined):
        topics.add("facilities")
    return sorted(topics or set(source_topics))


def build_college_chunks(raw_dir: Path) -> list[Chunk]:
    inventory = json.loads((raw_dir / "inventory.json").read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    seen: set[tuple[str, str, int | None, str]] = set()
    for source in inventory:
        content = (raw_dir / source["raw_file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise ValueError(f"Source changed after collection: {source['id']}")
        extracted = extract_pdf(content) if source["document_type"] == "pdf" else extract_html(content)
        parts = [part for section, text in extracted for part in _semantic_sections(section, text)]
        for section, text in parts:
            text = _clean(text)
            text_fingerprint = hashlib.sha256(text.casefold().encode()).hexdigest()
            fingerprint = hashlib.sha256((section + "\n" + text).casefold().encode()).hexdigest()
            key = (source["programme"], text_fingerprint, source["admission_year"], section)
            if key in seen:
                continue
            seen.add(key)
            other_years = {int(year) for year in YEAR_RE.findall(text)} - ({source["admission_year"]} if source["admission_year"] else set())
            chunks.append(Chunk(
                chunk_id=f"{source['id']}::{fingerprint[:16]}",
                doc_id=source["id"],
                domain="iiitk",
                title=source["title"],
                heading_path=[source["title"], section],
                section_id=fingerprint[:16],
                text=text,
                span_ids=[],
                source_url=source["source_url"],
                programme=source["programme"],
                admission_year=source["admission_year"],
                retrieved_at=source["retrieved_at"],
                document_type=source["document_type"],
                source_sha256=source["sha256"],
                year_conflict=bool(other_years),
                topics=_chunk_topics(source.get("topics", []), section, text),
            ))
    if not chunks:
        raise ValueError("No usable text was extracted from the curated sources")
    return chunks
