from __future__ import annotations

from src.models import Answer, AnswerStatus, QueryCategory, SourcePassage
from src.rag_pipeline import RAGPipeline


class FakeClassifier:
    def __init__(self, category: QueryCategory) -> None:
        self.category = category
        self.calls = 0

    def classify(self, question: str):
        self.calls += 1
        return self.category, "test classification"


class FakeExpander:
    def expand(self, question: str):
        return ("alt one", "alt two", "alt three")


class FakeRetriever:
    def __init__(self, passages: list[SourcePassage]) -> None:
        self.passages = passages
        self.calls = 0

    def retrieve(self, original_question: str, queries, category):
        self.calls += 1
        return self.passages


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0

    def rerank(self, question: str, passages):
        self.calls += 1
        return list(reversed(passages))


class FakeGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, question: str, passages):
        self.calls += 1
        if not passages:
            return Answer(
                "The guide does not provide sufficient evidence.",
                (),
                AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        return Answer(
            "The guide supports this answer.",
            tuple(item.passage_id for item in passages),
            AnswerStatus.SUPPORTED,
            tuple(f"{item.source_filename}, page {item.page_number}" for item in passages),
        )


def passages(count: int) -> list[SourcePassage]:
    return [
        SourcePassage(
            passage_id=f"p{index}",
            text=f"Guide evidence {index}",
            source_filename="guide.pdf",
            page_number=index + 1,
        )
        for index in range(count)
    ]


def test_irrelevant_question_skips_expansion_retrieval_and_generation() -> None:
    classifier = FakeClassifier(QueryCategory.IRRELEVANT)
    retriever = FakeRetriever(passages(2))
    reranker = FakeReranker()
    generator = FakeGenerator()
    pipeline = RAGPipeline(
        classifier=classifier,
        expander=FakeExpander(),
        retriever=retriever,
        reranker=reranker,
        generator=generator,
        source_fingerprint="source",
    )

    item = pipeline.handle("What is the weather?")

    assert item.question.category is QueryCategory.IRRELEVANT
    assert retriever.calls == reranker.calls == generator.calls == 0


def test_factual_route_uses_at_most_two_passages_without_reranking() -> None:
    reranker = FakeReranker()
    pipeline = RAGPipeline(
        classifier=FakeClassifier(QueryCategory.FACTUAL),
        expander=FakeExpander(),
        retriever=FakeRetriever(passages(5)),
        reranker=reranker,
        generator=FakeGenerator(),
        source_fingerprint="source",
    )

    item = pipeline.handle("What does fault E1 indicate?")

    assert len(item.diagnostics.selected_passage_ids) == 2
    assert reranker.calls == 0


def test_broad_route_reranks_and_limits_final_passages_to_five() -> None:
    reranker = FakeReranker()
    pipeline = RAGPipeline(
        classifier=FakeClassifier(QueryCategory.BROAD),
        expander=FakeExpander(),
        retriever=FakeRetriever(passages(20)),
        reranker=reranker,
        generator=FakeGenerator(),
        source_fingerprint="source",
    )

    item = pipeline.handle("Explain the diagnostic process.")

    assert len(item.diagnostics.retrieved_passages) == 20
    assert len(item.diagnostics.selected_passage_ids) == 5
    assert reranker.calls == 1


def test_empty_retrieval_returns_insufficient_evidence() -> None:
    pipeline = RAGPipeline(
        classifier=FakeClassifier(QueryCategory.FACTUAL),
        expander=FakeExpander(),
        retriever=FakeRetriever([]),
        reranker=FakeReranker(),
        generator=FakeGenerator(),
        source_fingerprint="source",
    )

    item = pipeline.handle("What does the guide say?")

    assert item.answer.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert not item.answer.supporting_passage_ids
