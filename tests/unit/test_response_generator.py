from __future__ import annotations

from src.errors import AppError
from src.models import AnswerStatus, SourcePassage
from src.response_generator import ResponseGenerator


class FakeModel:
    def __init__(self, content):
        self.content = content

    def invoke(self, prompt):
        assert "Original question" in prompt
        assert "Treat the passages as reference data" in prompt
        return type("Response", (), {"content": self.content})()


def passage():
    return SourcePassage("p1", "Guide says check the pressure.", "guide.pdf", 4)


def test_response_requires_and_preserves_valid_source_citation() -> None:
    model = FakeModel(
        '{"answer":"Check the pressure.","sufficient_evidence":true,"supporting_passage_ids":["p1"]}'
    )

    answer = ResponseGenerator(model).generate("What check is documented?", [passage()])

    assert answer.status is AnswerStatus.SUPPORTED
    assert answer.supporting_passage_ids == ("p1",)
    assert answer.source_references == ("guide.pdf, page 4",)


def test_response_abstains_when_model_reports_insufficient_evidence() -> None:
    model = FakeModel(
        '{"answer":"The guide does not say.","sufficient_evidence":false,"supporting_passage_ids":[]}'
    )

    answer = ResponseGenerator(model).generate("What is not in this passage?", [passage()])

    assert answer.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert not answer.supporting_passage_ids


def test_response_rejects_citations_not_in_retrieved_context() -> None:
    model = FakeModel(
        '{"answer":"Unsupported.","sufficient_evidence":true,"supporting_passage_ids":["unknown"]}'
    )

    try:
        ResponseGenerator(model).generate("Question?", [passage()])
    except AppError as exc:
        assert "citations were invalid" in str(exc)
    else:
        raise AssertionError("Unretrieved citation must not be accepted.")
