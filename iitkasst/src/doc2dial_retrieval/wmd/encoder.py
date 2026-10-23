"""Lazy pinned BERT encoder for paper-inspired vocabulary word vectors."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from .config import WmdConfig


@dataclass(frozen=True)
class EncodedWords:
    words: tuple[str, ...]
    vectors: np.ndarray
    rejected: tuple[str, ...]


class BertWordEncoder:
    """Encode each surface word independently and retain layer-11 [CLS]."""

    def __init__(self, config: WmdConfig, device: str | None = None, local_files_only: bool = False):
        self.config = config
        requested = device or config.device
        self.device = "cuda" if requested == "auto" and torch.cuda.is_available() else (requested if requested != "auto" else "cpu")
        self.local_files_only = local_files_only
        self._tokenizer = None
        self._model = None

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "model_id": self.config.model_id,
            "revision": self.config.revision,
            "encoder_layer": self.config.encoder_layer,
            "selector": "encoder_layer_11_cls",
            "dimension": 768,
        }

    def _load(self) -> None:
        if self._model is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_id,
            revision=self.config.revision,
            local_files_only=self.local_files_only,
            use_fast=True,
        )
        self._model = AutoModel.from_pretrained(
            self.config.model_id,
            revision=self.config.revision,
            local_files_only=self.local_files_only,
        ).to(self.device)
        self._model.eval()
        if int(self._model.config.hidden_size) != 768 or int(self._model.config.num_hidden_layers) != 12:
            raise ValueError("Pinned BERT model has an unexpected architecture")

    def _accepted_words(self, words: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        self._load()
        assert self._tokenizer is not None
        accepted: list[str] = []
        rejected: list[str] = []
        for word in words:
            token_ids = self._tokenizer(word, add_special_tokens=False)["input_ids"]
            if not token_ids or self._tokenizer.unk_token_id in token_ids:
                rejected.append(word)
            else:
                accepted.append(word)
        return tuple(accepted), tuple(rejected)

    def _encode_accepted(self, words: tuple[str, ...]) -> np.ndarray:
        if not words:
            return np.empty((0, 768), dtype=np.float32)
        assert self._tokenizer is not None and self._model is not None
        encoded: list[np.ndarray] = []
        for start in range(0, len(words), self.config.batch_size):
            batch = words[start : start + self.config.batch_size]
            tokens = self._tokenizer(list(batch), padding=True, truncation=True, max_length=32, return_tensors="pt")
            tokens = {key: value.to(self.device) for key, value in tokens.items()}
            with torch.inference_mode():
                output = self._model(**tokens, output_hidden_states=True, return_dict=True)
            vector = output.hidden_states[-2][:, 0, :].detach().float().cpu().numpy()
            encoded.append(vector)
        matrix = np.vstack(encoded).astype(np.float32, copy=False)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if not np.isfinite(matrix).all() or np.any(norms <= 1e-12):
            raise ValueError("BERT produced invalid word vectors")
        return matrix / norms

    def encode_words(self, words: Iterable[str]) -> EncodedWords:
        unique = tuple(dict.fromkeys(words))
        accepted, rejected = self._accepted_words(unique)
        try:
            vectors = self._encode_accepted(accepted)
        except torch.cuda.OutOfMemoryError:
            if self.device != "cuda":
                raise
            torch.cuda.empty_cache()
            assert self._model is not None
            self.device = "cpu"
            self._model = self._model.to(self.device)
            vectors = self._encode_accepted(accepted)
        return EncodedWords(accepted, vectors, rejected)
