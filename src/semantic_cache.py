"""Persistent SQLite semantic cache with source-aware similarity matching."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Sequence

from src.errors import AppError, ErrorKind
from src.models import (
    Answer,
    AnswerStatus,
    CacheEntry,
    CacheLookupResult,
    CacheMatch,
    CacheStats,
    QueryCategory,
)


class SemanticCache:
    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        entry_id TEXT PRIMARY KEY,
                        question_text TEXT NOT NULL,
                        question_embedding TEXT NOT NULL,
                        answer_text TEXT NOT NULL,
                        category TEXT NOT NULL CHECK (category IN ('FACTUAL', 'BROAD')),
                        created_at TEXT NOT NULL,
                        evidence_metadata TEXT NOT NULL,
                        source_fingerprint TEXT NOT NULL,
                        hit_count INTEGER NOT NULL DEFAULT 0 CHECK (hit_count >= 0)
                    );
                    CREATE TABLE IF NOT EXISTS cache_stats (
                        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                        hits INTEGER NOT NULL DEFAULT 0,
                        misses INTEGER NOT NULL DEFAULT 0
                    );
                    INSERT OR IGNORE INTO cache_stats (singleton, hits, misses)
                    VALUES (1, 0, 0);
                    """
                )
        except sqlite3.Error as exc:
            raise AppError(ErrorKind.CACHE, "The semantic cache could not be initialized.") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def lookup(
        self,
        question: str,
        embedding: Sequence[float],
        *,
        threshold: float,
        source_fingerprint: str,
    ) -> CacheLookupResult:
        if not 0 <= threshold <= 1:
            raise ValueError("Cache similarity threshold must be between zero and one.")
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM cache_entries
                    WHERE source_fingerprint = ?
                    """,
                    (source_fingerprint,),
                ).fetchall()
                scored: list[tuple[sqlite3.Row, float]] = []
                for row in rows:
                    stored = json.loads(row["question_embedding"])
                    similarity = self._cosine_similarity(embedding, stored)
                    if similarity is not None:
                        scored.append((row, similarity))
                closest = max(scored, key=lambda item: item[1], default=None)
                if closest is not None and closest[1] >= threshold:
                    row, similarity = closest
                    connection.execute(
                        "UPDATE cache_entries SET hit_count = hit_count + 1 WHERE entry_id = ?",
                        (row["entry_id"],),
                    )
                    connection.execute(
                        "UPDATE cache_stats SET hits = hits + 1 WHERE singleton = 1"
                    )
                    return CacheLookupResult(
                        CacheMatch(self._entry_from_row(row), similarity),
                        closest_similarity=similarity,
                        closest_entry_id=row["entry_id"],
                    )
                connection.execute(
                    "UPDATE cache_stats SET misses = misses + 1 WHERE singleton = 1"
                )
                return CacheLookupResult(
                    None,
                    closest_similarity=closest[1] if closest is not None else None,
                    closest_entry_id=closest[0]["entry_id"] if closest is not None else None,
                )
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AppError(ErrorKind.CACHE, "The semantic cache could not be read.") from exc

    def add(
        self,
        question: str,
        embedding: Sequence[float],
        answer: Answer,
        category: QueryCategory,
        *,
        evidence_metadata: Sequence[dict[str, object]],
        source_fingerprint: str,
    ) -> CacheEntry:
        if answer.status is not AnswerStatus.SUPPORTED or not answer.supporting_passage_ids:
            raise ValueError("Only successful answers supported by guide evidence can be cached.")
        if category not in {QueryCategory.FACTUAL, QueryCategory.BROAD}:
            raise ValueError("Irrelevant questions cannot be added to the cache.")
        if not evidence_metadata:
            raise ValueError("Cached answers must retain their supporting evidence metadata.")
        entry = CacheEntry(
            entry_id=uuid.uuid4().hex,
            question_text=question,
            question_embedding=tuple(float(value) for value in embedding),
            answer_text=answer.answer_text,
            category=category,
            created_at=datetime.now().astimezone(),
            evidence_metadata=tuple(dict(item) for item in evidence_metadata),
            source_fingerprint=source_fingerprint,
        )
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO cache_entries (
                        entry_id, question_text, question_embedding, answer_text, category,
                        created_at, evidence_metadata, source_fingerprint, hit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.entry_id,
                        entry.question_text,
                        json.dumps(entry.question_embedding),
                        entry.answer_text,
                        entry.category.value,
                        entry.created_at.isoformat(),
                        json.dumps(entry.evidence_metadata),
                        entry.source_fingerprint,
                        entry.hit_count,
                    ),
                )
        except sqlite3.Error as exc:
            raise AppError(ErrorKind.CACHE, "The supported answer could not be saved to the cache.") from exc
        return entry

    def list_entries(self) -> list[CacheEntry]:
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT * FROM cache_entries ORDER BY created_at DESC"
                ).fetchall()
            return [self._entry_from_row(row) for row in rows]
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AppError(ErrorKind.CACHE, "The semantic cache entries could not be listed.") from exc

    def stats(self) -> CacheStats:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT hits, misses FROM cache_stats WHERE singleton = 1"
                ).fetchone()
                count = connection.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            return CacheStats(total_entries=int(count), hits=int(row["hits"]), misses=int(row["misses"]))
        except sqlite3.Error as exc:
            raise AppError(ErrorKind.CACHE, "The semantic cache statistics could not be read.") from exc

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float | None:
        if not left or len(left) != len(right):
            return None
        left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
        right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
        if left_norm == 0 or right_norm == 0:
            return None
        dot = sum(float(a) * float(b) for a, b in zip(left, right))
        return max(-1.0, min(1.0, dot / (left_norm * right_norm)))

    @staticmethod
    def _entry_from_row(row: sqlite3.Row) -> CacheEntry:
        return CacheEntry(
            entry_id=row["entry_id"],
            question_text=row["question_text"],
            question_embedding=tuple(json.loads(row["question_embedding"])),
            answer_text=row["answer_text"],
            category=QueryCategory(row["category"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            evidence_metadata=tuple(json.loads(row["evidence_metadata"])),
            source_fingerprint=row["source_fingerprint"],
            hit_count=int(row["hit_count"]),
        )
