"""Configuration for the isolated BERT + WMD experiment."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WmdConfig:
    model_id: str
    revision: str
    cache_dir: str
    chunks_path: str
    encoder_layer: int = 11
    query_token_limit: int = 32
    title_token_limit: int = 12
    heading_token_limit: int = 20
    passage_token_limit: int = 32
    candidate_limit: int = 15
    batch_size: int = 64
    device: str = "auto"
    preprocessing_version: int = 1

    @property
    def document_token_limit(self) -> int:
        return self.title_token_limit + self.heading_token_limit + self.passage_token_limit

    def fingerprint(self) -> str:
        payload = repr(sorted(asdict(self).items())).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def load_wmd_config(root: Path, path: str = "configs/wmd_experiment.yaml") -> WmdConfig:
    raw: dict[str, Any] = yaml.safe_load((root / path).read_text(encoding="utf-8"))
    return WmdConfig(**raw)
