from __future__ import annotations

from src.models import SourcePassage
from src.reranker import Reranker


class FakeCrossEncoder:
    def __init__(self, scores):
        self.scores = scores
        self.pairs = None

    def predict(self, pairs):
        self.pairs = pairs
        return self.scores


def test_reranker_orders_candidates_by_original_question_score() -> None:
    passages = [
        SourcePassage("p1", "less relevant", "guide.pdf", 1),
        SourcePassage("p2", "more relevant", "guide.pdf", 2),
    ]
    model = FakeCrossEncoder([0.1, 0.9])

    ranked = Reranker("local-model", model=model).rerank("original question", passages)

    assert [item.passage_id for item in ranked] == ["p2", "p1"]
    assert ranked[0].rerank_score == 0.9
    assert model.pairs[0] == ("original question", "less relevant")
