from __future__ import annotations

import pytest

from src.models import Answer, AnswerStatus, QueryCategory, SourcePassage
from src.rag_pipeline import RAGPipeline


class Classifier:
    def __init__(self, category):
        self.category = category

    def classify(self, question):
        return self.category, f"classified as {self.category.value}"


class Expander:
    def expand(self, question):
        return ("alternate one", "alternate two", "alternate three")


class Retriever:
    def __init__(self, count):
        self.passages = [
            SourcePassage(f"p{index}", f"Evidence {index}", "guide.pdf", index + 1)
            for index in range(count)
        ]

    def retrieve(self, original_question, queries, category):
        return self.passages


class Reranker:
    def rerank(self, question, passages):
        return list(reversed(passages))


class Generator:
    def generate(self, question, passages):
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
        )


@pytest.mark.parametrize(
    ("category", "retrieved_count", "expected_answer", "expected_selected"),
    [
        (QueryCategory.FACTUAL, 7, AnswerStatus.SUPPORTED, 2),
        (QueryCategory.BROAD, 25, AnswerStatus.SUPPORTED, 5),
        (QueryCategory.FACTUAL, 0, AnswerStatus.INSUFFICIENT_EVIDENCE, 0),
        (QueryCategory.IRRELEVANT, 7, AnswerStatus.INSUFFICIENT_EVIDENCE, 0),
    ],
)
def test_end_to_end_answer_route(
    category, retrieved_count, expected_answer, expected_selected
) -> None:
    pipeline = RAGPipeline(
        classifier=Classifier(category),
        expander=Expander(),
        retriever=Retriever(retrieved_count),
        reranker=Reranker(),
        generator=Generator(),
        source_fingerprint="fixture-source",
    )

    result = pipeline.handle("What does the troubleshooting guide explain?")

    assert result.answer.status is expected_answer
    assert len(result.diagnostics.selected_passage_ids) == expected_selected
    assert result.diagnostics.total_duration >= 0
