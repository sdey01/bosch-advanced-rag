"""Local CPU cross-encoder for broad-query candidate ordering."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Sequence

from src.errors import AppError, ErrorKind
from src.models import SourcePassage


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device="cpu")


class Reranker:
    def __init__(
        self,
        model_name: str,
        *,
        model: Any | None = None,
        top_k: int = 5,
    ) -> None:
        if top_k < 1:
            raise ValueError("Rerank top-k must be at least one.")
        self.model_name = model_name
        self.top_k = top_k
        try:
            self._model = model or _load_cross_encoder(model_name)
        except Exception as exc:
            raise AppError(ErrorKind.RERANKING, "The local cross-encoder could not be loaded.") from exc

    def rerank(self, question: str, passages: Sequence[SourcePassage]) -> list[SourcePassage]:
        if not passages:
            return []
        try:
            pairs = [(question, passage.text) for passage in passages]
            scores = self._model.predict(pairs)
            ranked = [
                (passage, float(score))
                for passage, score in zip(passages, scores)
            ]
            if len(ranked) != len(passages):
                raise ValueError("Cross-encoder returned an unexpected number of scores.")
            ranked.sort(key=lambda item: item[1], reverse=True)
            from dataclasses import replace

            return [replace(passage, rerank_score=score) for passage, score in ranked]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorKind.RERANKING, "Broad-query passage reranking failed.") from exc
