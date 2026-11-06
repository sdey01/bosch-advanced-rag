"""Orchestration for classification, optional cache, retrieval, and grounded answers."""

from __future__ import annotations

from typing import Any

from src.diagnostics import InteractionTimer
from src.errors import AppError, ErrorKind
from src.models import (
    Answer,
    AnswerStatus,
    CacheLookupResult,
    ConversationItem,
    InteractionDiagnostics,
    QueryCategory,
    Question,
    SourcePassage,
)


class RAGPipeline:
    def __init__(
        self,
        *,
        classifier: Any,
        expander: Any,
        retriever: Any,
        reranker: Any,
        generator: Any,
        source_fingerprint: str,
        cache: Any | None = None,
        embeddings: Any | None = None,
        cache_threshold: float = 0.90,
        rerank_top_k: int = 5,
    ) -> None:
        self.classifier = classifier
        self.expander = expander
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.source_fingerprint = source_fingerprint
        self.cache = cache
        self.embeddings = embeddings
        self.cache_threshold = cache_threshold
        self.rerank_top_k = rerank_top_k

    def handle(self, question_text: str) -> ConversationItem:
        timer = InteractionTimer()

        with timer.measure("classification"):
            category, reason = self.classifier.classify(question_text)
        if not isinstance(category, QueryCategory):
            raise AppError(
                ErrorKind.OUTPUT,
                "The classifier returned an unsupported query category.",
            )

        if category is QueryCategory.IRRELEVANT:
            question = Question(question_text, category, reason)
            answer = Answer(
                "Sorry, this question appears to be outside the scope of the Bosch Rexroth troubleshooting guide. Please ask a question related to the document.",
                (),
                AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
            return self._item(question, answer, "irrelevant", "not_applicable", timer)

        cache_outcome = "not_applicable"
        cache_match = None
        closest_similarity: float | None = None
        cache_embedding: list[float] | None = None
        if self.cache is not None and self.embeddings is not None:
            try:
                with timer.measure("cache_lookup"):
                    cache_embedding = self.embeddings.embed_query(question_text)
                    lookup: CacheLookupResult = self.cache.lookup(
                        question_text,
                        cache_embedding,
                        threshold=self.cache_threshold,
                        source_fingerprint=self.source_fingerprint,
                    )
                    cache_match = lookup.match
                    closest_similarity = lookup.closest_similarity
                    cache_outcome = "hit" if cache_match is not None else "miss"
            except AppError:
                cache_outcome = "read_error"
            if cache_match is not None:
                entry = cache_match.entry
                evidence = entry.evidence_metadata
                passage_ids = tuple(
                    str(item["passage_id"])
                    for item in evidence
                    if item.get("passage_id") is not None
                )
                answer = Answer(
                    entry.answer_text,
                    passage_ids,
                    AnswerStatus.CACHED,
                    tuple(
                        f"{item.get('source_filename')}, page {item.get('page_number')}"
                        if item.get("page_number") is not None
                        else str(item.get("source_filename", ""))
                        for item in evidence
                    ),
                )
                question = Question(question_text, category, reason, cache_hit=True)
                return self._item(
                    question,
                    answer,
                    "cache_hit",
                    cache_outcome,
                    timer,
                    cache_similarity=cache_match.similarity,
                    cache_entry_id=entry.entry_id,
                )

        with timer.measure("query_expansion"):
            alternatives = self.expander.expand(question_text)
        question = Question(question_text, category, reason, tuple(alternatives))

        with timer.measure("vector_retrieval"):
            retrieved = self.retriever.retrieve(
                question_text,
                (question_text, *alternatives),
                category,
            )
        retrieval_limit = 2 if category is QueryCategory.FACTUAL else 20
        retrieved = list(retrieved[:retrieval_limit])

        ranked: list[SourcePassage] = []
        selected = retrieved
        if category is QueryCategory.BROAD and retrieved:
            with timer.measure("reranking"):
                ranked = list(self.reranker.rerank(question_text, retrieved))
            selected = ranked[: self.rerank_top_k]

        if not selected:
            answer = Answer(
                "The troubleshooting guide does not provide sufficient evidence to answer this question.",
                (),
                AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        else:
            with timer.measure("answer_generation"):
                answer = self.generator.generate(question_text, selected)

        if (
            answer.status is AnswerStatus.SUPPORTED
            and answer.supporting_passage_ids
            and self.cache is not None
            and cache_embedding is not None
            and cache_outcome != "read_error"
        ):
            evidence_by_id = {passage.passage_id: passage for passage in selected}
            evidence_metadata = [
                {
                    "passage_id": passage_id,
                    "source_filename": evidence_by_id[passage_id].source_filename,
                    "page_number": evidence_by_id[passage_id].page_number,
                }
                for passage_id in answer.supporting_passage_ids
                if passage_id in evidence_by_id
            ]
            try:
                entry = self.cache.add(
                    question_text,
                    cache_embedding,
                    answer,
                    category,
                    evidence_metadata=evidence_metadata,
                    source_fingerprint=self.source_fingerprint,
                )
                cache_outcome = "added"
                cache_entry_id = entry.entry_id
            except AppError:
                cache_outcome = "write_error"
                cache_entry_id = None
        else:
            cache_entry_id = None

        return self._item(
            question,
            answer,
            category.value.lower(),
            cache_outcome,
            timer,
            retrieved=retrieved,
            ranked=ranked,
            selected=selected,
            cache_similarity=(
                cache_match.similarity if cache_match is not None else closest_similarity
            ),
            cache_entry_id=cache_entry_id,
        )

    @staticmethod
    def _item(
        question: Question,
        answer: Answer,
        route: str,
        cache_outcome: str,
        timer: InteractionTimer,
        *,
        retrieved: list[SourcePassage] | None = None,
        ranked: list[SourcePassage] | None = None,
        selected: list[SourcePassage] | None = None,
        cache_similarity: float | None = None,
        cache_entry_id: str | None = None,
    ) -> ConversationItem:
        diagnostics = InteractionDiagnostics(
            route=route,
            cache_outcome=cache_outcome,
            cache_similarity=cache_similarity,
            stage_durations=dict(timer.stage_durations),
            total_duration=timer.total_duration,
            cache_entry_id=cache_entry_id,
            retrieved_passages=tuple(retrieved or ()),
            reranked_passages=tuple(ranked or ()),
            selected_passage_ids=tuple(item.passage_id for item in (selected or ())),
        )
        return ConversationItem(question, answer, diagnostics)
