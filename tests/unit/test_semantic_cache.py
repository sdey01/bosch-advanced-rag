from __future__ import annotations

import sqlite3

import pytest

from src.errors import AppError
from src.models import Answer, AnswerStatus, QueryCategory
from src.semantic_cache import SemanticCache


def add_supported(cache: SemanticCache, question: str = "What does fault E1 mean?"):
    return cache.add(
        question,
        [1.0, 0.0],
        Answer("The guide explains fault E1.", ("p1",), AnswerStatus.SUPPORTED),
        QueryCategory.FACTUAL,
        evidence_metadata=[{"passage_id": "p1", "source_filename": "guide.pdf", "page_number": 2}],
        source_fingerprint="source-v1",
    )


def test_cache_hit_updates_entry_and_aggregate_counts(tmp_path) -> None:
    cache = SemanticCache(tmp_path / "cache.db")
    entry = add_supported(cache)

    lookup = cache.lookup(
        "Explain fault E1",
        [1.0, 0.0],
        threshold=0.90,
        source_fingerprint="source-v1",
    )

    assert lookup.match is not None
    assert lookup.match.entry.entry_id == entry.entry_id
    assert lookup.closest_similarity == pytest.approx(1.0)
    stats = cache.stats()
    assert (stats.total_entries, stats.hits, stats.misses) == (1, 1, 0)
    assert cache.list_entries()[0].hit_count == 1


def test_cache_miss_reports_closest_below_threshold(tmp_path) -> None:
    cache = SemanticCache(tmp_path / "cache.db")
    add_supported(cache)

    lookup = cache.lookup(
        "Could this refer to another fault?",
        [0.0, 1.0],
        threshold=0.90,
        source_fingerprint="source-v1",
    )

    assert lookup.match is None
    assert lookup.closest_similarity == pytest.approx(0.0)
    assert cache.stats().misses == 1


def test_stale_source_entry_is_not_reused(tmp_path) -> None:
    cache = SemanticCache(tmp_path / "cache.db")
    add_supported(cache)

    lookup = cache.lookup(
        "What does fault E1 mean?",
        [1.0, 0.0],
        threshold=0.90,
        source_fingerprint="source-v2",
    )

    assert lookup.match is None


def test_unsupported_answers_cannot_be_cached(tmp_path) -> None:
    cache = SemanticCache(tmp_path / "cache.db")
    with pytest.raises(ValueError):
        cache.add(
            "Question",
            [1.0, 0.0],
            Answer("Not supported.", (), AnswerStatus.INSUFFICIENT_EVIDENCE),
            QueryCategory.FACTUAL,
            evidence_metadata=[],
            source_fingerprint="source-v1",
        )


def test_cache_entries_and_counters_survive_reopening(tmp_path) -> None:
    path = tmp_path / "cache.db"
    first = SemanticCache(path)
    add_supported(first)
    first.lookup("What is E1?", [1.0, 0.0], threshold=0.9, source_fingerprint="source-v1")

    reopened = SemanticCache(path)

    assert len(reopened.list_entries()) == 1
    assert reopened.stats().hits == 1


def test_cache_read_failure_is_reported(tmp_path, monkeypatch) -> None:
    cache = SemanticCache(tmp_path / "cache.db")

    def broken_connect():
        raise sqlite3.OperationalError("sensitive database path")

    monkeypatch.setattr(cache, "_connect", broken_connect)
    with pytest.raises(AppError, match="could not be read"):
        cache.lookup("Question", [1.0], threshold=0.9, source_fingerprint="source-v1")


def test_cache_write_failure_is_reported(tmp_path, monkeypatch) -> None:
    cache = SemanticCache(tmp_path / "cache.db")

    def broken_connect():
        raise sqlite3.OperationalError("sensitive database path")

    monkeypatch.setattr(cache, "_connect", broken_connect)
    with pytest.raises(AppError, match="could not be saved"):
        add_supported(cache)
