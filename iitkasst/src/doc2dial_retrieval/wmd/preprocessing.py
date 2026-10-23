"""Deterministic lexical preprocessing shared by WMD cache and queries."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field

_ALIASES = (
    (re.compile(r"\be\s*[-.]?\s*m\s*\.?(?:tech)?\b", re.I), "emtech"),
    (re.compile(r"\bm\s*\.?(?:tech)\b", re.I), "mtech"),
    (re.compile(r"\bb\s*\.?(?:tech)\b", re.I), "btech"),
    (re.compile(r"\bph\s*\.?\s*d\b", re.I), "phd"),
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# The list is deliberately local and versioned rather than inherited from a
# library whose contents can change between cache builds.
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do", "does", "for",
        "from", "has", "have", "how", "i", "in", "is", "it", "its", "me", "my", "of", "on", "or", "our",
        "please", "the", "their", "there", "these", "this", "to", "was", "we", "what", "which", "who",
        "will", "with", "would", "you", "your",
    }
)


@dataclass(frozen=True)
class WmdPreprocessor:
    version: int = 1
    stopwords: frozenset[str] = field(default_factory=lambda: _STOPWORDS)

    def normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text).casefold()
        for pattern, replacement in _ALIASES:
            normalized = pattern.sub(replacement, normalized)
        return normalized

    def tokenize_terms(self, text: str) -> tuple[str, ...]:
        normalized = self.normalize_text(text)
        return tuple(term for term in _TOKEN_RE.findall(normalized) if term not in self.stopwords)

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": self.version, "stopwords": sorted(self.stopwords), "aliases": [pattern.pattern for pattern, _ in _ALIASES]},
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
