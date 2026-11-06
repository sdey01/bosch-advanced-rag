from __future__ import annotations

from src.models import Answer, AnswerStatus, QueryCategory, SourcePassage
from src.rag_pipeline import RAGPipeline
from src.semantic_cache import SemanticCache


class FakeClassifier:
    def classify(self, question: str):
        return QueryCategory.FACTUAL, "specific guide fact"


class FakeExpander:
    def __init__(self) -> None:
        self.calls = 0

    def expand(self, question: str):
        self.calls += 1
        return ("one", "two", "three")


class FakeEmbeddings:
    def embed_query(self, question: str):
        return [1.0, 0.0]


class FakeRetriever:
    def __init__(self, passage: SourcePassage) -> None:
        self.passage = passage
        self.calls = 0

    def retrieve(self, original_question, queries, category):
        self.calls += 1
        return [self.passage]


class FakeReranker:
    def rerank(self, question, passages):
        raise AssertionError("Factual questions must not be reranked.")


class FakeGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, question, passages):
        self.calls += 1
        return Answer(
            "The supported answer.",
            ("p1",),
            AnswerStatus.SUPPORTED,
            ("guide.pdf, page 1",),
        )


def test_cache_hit_reuses_answer_and_skips_later_stages(tmp_path) -> None:
    passage = SourcePassage("p1", "Document evidence", "guide.pdf", 1)
    expander = FakeExpander()
    retriever = FakeRetriever(passage)
    generator = FakeGenerator()
    pipeline = RAGPipeline(
        classifier=FakeClassifier(),
        expander=expander,
        retriever=retriever,
        reranker=FakeReranker(),
        generator=generator,
        cache=SemanticCache(tmp_path / "cache.db"),
        embeddings=FakeEmbeddings(),
        source_fingerprint="source-v1",
    )

    first = pipeline.handle("What does fault E1 mean?")
    second = pipeline.handle("What does fault E1 mean?")

    assert first.diagnostics.cache_outcome == "added"
    assert second.diagnostics.cache_outcome == "hit"
    assert second.answer.status is AnswerStatus.CACHED
    assert "query_expansion" not in second.diagnostics.stage_durations
    assert "vector_retrieval" not in second.diagnostics.stage_durations
    assert "answer_generation" not in second.diagnostics.stage_durations
    assert expander.calls == retriever.calls == generator.calls == 1


def test_cache_miss_does_not_match_below_threshold(tmp_path) -> None:
    passage = SourcePassage("p1", "Document evidence", "guide.pdf", 1)
    cache = SemanticCache(tmp_path / "cache.db")
    cache.add(
        "Question about pressure",
        [1.0, 0.0],
        Answer("Supported.", ("p1",), AnswerStatus.SUPPORTED),
        QueryCategory.FACTUAL,
        evidence_metadata=[{"passage_id": "p1", "source_filename": "guide.pdf", "page_number": 1}],
        source_fingerprint="source-v1",
    )
    pipeline = RAGPipeline(
        classifier=FakeClassifier(),
        expander=FakeExpander(),
        retriever=FakeRetriever(passage),
        reranker=FakeReranker(),
        generator=FakeGenerator(),
        cache=cache,
        embeddings=type("DifferentEmbedding", (), {"embed_query": lambda self, question: [0.0, 1.0]})(),
        source_fingerprint="source-v1",
    )

    item = pipeline.handle("Unrelated question")

    assert item.diagnostics.cache_outcome == "added"
    assert item.answer.status is AnswerStatus.SUPPORTED
