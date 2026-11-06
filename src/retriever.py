"""Multi-query passage retrieval with global deduplication and category limits."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

from src.errors import AppError, ErrorKind
from src.models import QueryCategory, SourcePassage


class Retriever:
    def __init__(self, vector_store: Any, embeddings: Any, settings: Any) -> None:
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.settings = settings

    def retrieve(
        self,
        original_question: str,
        queries: Sequence[str],
        category: QueryCategory,
    ) -> list[SourcePassage]:
        if category is QueryCategory.IRRELEVANT:
            return []
        overall_limit = (
            self.settings.factual_top_k
            if category is QueryCategory.FACTUAL
            else self.settings.broad_top_k
        )
        candidates: dict[str, tuple[SourcePassage, float]] = {}
        all_queries = tuple(dict.fromkeys((original_question, *queries)))
        try:
            for query in all_queries:
                embedding = self.embeddings.embed_query(query)
                for passage, score in self.vector_store.search(embedding, overall_limit):
                    previous = candidates.get(passage.passage_id)
                    if previous is None or score > previous[1]:
                        candidates[passage.passage_id] = (passage, score)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorKind.RETRIEVAL, "Guide passage retrieval failed.") from exc

        ordered = sorted(candidates.values(), key=lambda item: item[1], reverse=True)
        return [
            replace(passage, retrieval_score=score)
            for passage, score in ordered[:overall_limit]
        ]
