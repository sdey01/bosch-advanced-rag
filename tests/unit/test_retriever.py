from __future__ import annotations

from types import SimpleNamespace

from src.models import QueryCategory, SourcePassage
from src.retriever import Retriever


class FakeEmbeddings:
    def embed_query(self, query):
        return [float(len(query)), 1.0]


class FakeVectorStore:
    def __init__(self):
        self.calls = []
        self.passages = [
            SourcePassage(f"p{index}", f"Evidence {index}", "guide.pdf", index + 1)
            for index in range(3)
        ]

    def search(self, embedding, k):
        self.calls.append((embedding, k))
        return [
            (self.passages[0], 0.8),
            (self.passages[1], 0.6),
            (self.passages[2], 0.4),
        ][:k]


def test_retriever_deduplicates_expanded_searches_and_enforces_global_limit() -> None:
    store = FakeVectorStore()
    retriever = Retriever(
        store,
        FakeEmbeddings(),
        SimpleNamespace(factual_top_k=2, broad_top_k=20),
    )

    result = retriever.retrieve(
        "original",
        ("alternative 1", "alternative 2", "alternative 3"),
        QueryCategory.FACTUAL,
    )

    assert len(result) == 2
    assert [item.passage_id for item in result] == ["p0", "p1"]
    assert len(store.calls) == 4
    assert all(call[1] == 2 for call in store.calls)


def test_retriever_does_not_search_for_irrelevant_category() -> None:
    store = FakeVectorStore()
    retriever = Retriever(
        store,
        FakeEmbeddings(),
        SimpleNamespace(factual_top_k=2, broad_top_k=20),
    )

    assert retriever.retrieve("unrelated", (), QueryCategory.IRRELEVANT) == []
    assert store.calls == []
