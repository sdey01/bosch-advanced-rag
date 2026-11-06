"""Reusable local CPU sentence-transformer embeddings."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from sentence_transformers import SentenceTransformer

from src.errors import AppError, ErrorKind


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name, device="cpu")


class EmbeddingService:
    def __init__(self, model_name: str, model: object | None = None) -> None:
        self.model_name = model_name
        try:
            self._model = model or _load_model(model_name)
        except Exception as exc:
            raise AppError(ErrorKind.MODEL, "The local embedding model could not be loaded.") from exc

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed an empty question.")
        return self._encode([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("Cannot embed an empty passage.")
        return self._encode(list(texts))

    def _encode(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.tolist()
        except Exception as exc:
            raise AppError(ErrorKind.MODEL, "Local embedding generation failed.") from exc
