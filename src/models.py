"""Shared domain records and protocols for the troubleshooting assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Protocol, Sequence


class QueryCategory(StrEnum):
    FACTUAL = "FACTUAL"
    BROAD = "BROAD"
    IRRELEVANT = "IRRELEVANT"


class AnswerStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ERROR = "ERROR"
    CACHED = "CACHED"


@dataclass(frozen=True, slots=True)
class Guide:
    source_path: Path
    source_filename: str
    source_fingerprint: str
    page_count: int

    def __post_init__(self) -> None:
        if not self.source_path.is_file():
            raise ValueError("Guide source path must resolve to a readable PDF before ingestion.")
        if not self.source_filename.strip():
            raise ValueError("Guide source filename is required.")
        if not self.source_fingerprint:
            raise ValueError("Guide source fingerprint is required.")
        if self.page_count < 0:
            raise ValueError("Guide page count must be non-negative.")


@dataclass(frozen=True, slots=True)
class SourcePassage:
    passage_id: str
    text: str
    source_filename: str
    page_number: int | None
    embedding: tuple[float, ...] | None = field(default=None, repr=False)
    retrieval_score: float | None = None
    rerank_score: float | None = None

    def __post_init__(self) -> None:
        if not self.passage_id:
            raise ValueError("Passage ID must be unique within the index.")
        if not self.text.strip():
            raise ValueError("Passage text must be non-empty after normalization.")
        if not self.source_filename.strip():
            raise ValueError("Passage source filename is required.")
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("Page numbers must follow a one-based convention.")


@dataclass(frozen=True, slots=True)
class Question:
    question_text: str
    category: QueryCategory
    classification_reason: str
    query_alternatives: tuple[str, ...] = ()
    cache_hit: bool = False

    def __post_init__(self) -> None:
        if not self.question_text.strip():
            raise ValueError("Question text is required.")
        if not isinstance(self.category, QueryCategory):
            raise ValueError("Question category must be a defined category.")
        if not isinstance(self.classification_reason, str) or not self.classification_reason.strip():
            raise ValueError("Classifier reasoning must be present when returned.")
        if self.category is QueryCategory.IRRELEVANT and self.query_alternatives:
            raise ValueError("Irrelevant questions cannot have query alternatives.")
        if self.cache_hit and self.query_alternatives:
            raise ValueError("Cache-hit questions cannot have query alternatives.")
        if self.query_alternatives and len(self.query_alternatives) != 3:
            raise ValueError("A relevant cache miss requires exactly three alternatives.")


@dataclass(frozen=True, slots=True)
class Answer:
    answer_text: str
    supporting_passage_ids: tuple[str, ...]
    status: AnswerStatus
    source_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.answer_text.strip():
            raise ValueError("Answer text is required.")
        if self.status is AnswerStatus.SUPPORTED and not self.supporting_passage_ids:
            raise ValueError("A supported answer must identify guide evidence.")
        if self.status in {AnswerStatus.ERROR, AnswerStatus.INSUFFICIENT_EVIDENCE}:
            if self.status is AnswerStatus.ERROR and self.supporting_passage_ids:
                raise ValueError("Error answers cannot be cached as supported responses.")


@dataclass(frozen=True, slots=True)
class CacheEntry:
    entry_id: str
    question_text: str
    question_embedding: tuple[float, ...] = field(repr=False)
    answer_text: str
    category: QueryCategory
    created_at: datetime
    evidence_metadata: tuple[dict[str, object], ...]
    source_fingerprint: str
    hit_count: int = 0

    def __post_init__(self) -> None:
        if not self.entry_id or not self.question_text.strip() or not self.answer_text.strip():
            raise ValueError("Cache entry ID, question, and answer are required.")
        if self.category not in {QueryCategory.FACTUAL, QueryCategory.BROAD}:
            raise ValueError("Cache entries are only allowed for relevant question categories.")
        if self.hit_count < 0:
            raise ValueError("Cache entry hit count must be non-negative.")


@dataclass(frozen=True, slots=True)
class InteractionDiagnostics:
    route: str
    cache_outcome: str = "not_applicable"
    cache_similarity: float | None = None
    stage_durations: dict[str, float] = field(default_factory=dict)
    total_duration: float = 0.0
    cache_entry_id: str | None = None
    retrieved_passages: tuple[SourcePassage, ...] = ()
    reranked_passages: tuple[SourcePassage, ...] = ()
    selected_passage_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.route:
            raise ValueError("Diagnostics route must match the executed processing stages.")
        if self.total_duration < 0 or any(value < 0 for value in self.stage_durations.values()):
            raise ValueError("Diagnostic durations must be non-negative.")


@dataclass(frozen=True, slots=True)
class ConversationItem:
    question: Question
    answer: Answer
    diagnostics: InteractionDiagnostics

    def __post_init__(self) -> None:
        if not self.diagnostics.route:
            raise ValueError("Conversation diagnostics must be linked to the question.")


@dataclass(frozen=True, slots=True)
class CacheStats:
    total_entries: int
    hits: int
    misses: int

    @property
    def hit_ratio(self) -> float:
        attempts = self.hits + self.misses
        return self.hits / attempts if attempts else 0.0


@dataclass(frozen=True, slots=True)
class CacheMatch:
    entry: CacheEntry
    similarity: float


@dataclass(frozen=True, slots=True)
class CacheLookupResult:
    match: CacheMatch | None
    closest_similarity: float | None = None
    closest_entry_id: str | None = None


class CacheService(Protocol):
    def lookup(
        self,
        question: str,
        embedding: Sequence[float],
        *,
        threshold: float,
        source_fingerprint: str,
    ) -> CacheLookupResult: ...

    def add(
        self,
        question: str,
        embedding: Sequence[float],
        answer: Answer,
        category: QueryCategory,
        *,
        evidence_metadata: Sequence[dict[str, object]],
        source_fingerprint: str,
    ) -> CacheEntry: ...

    def list_entries(self) -> list[CacheEntry]: ...

    def stats(self) -> CacheStats: ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
