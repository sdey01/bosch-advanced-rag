from __future__ import annotations

from src.models import QueryCategory
from src.query_classifier import QueryClassifier
from src.query_expansion import QueryExpander


class FakeModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return type("Response", (), {"content": next(self.responses)})()


def test_classifier_parses_allowed_category_and_reason() -> None:
    model = FakeModel(['{"category":"FACTUAL","reason":"Specific guide fact."}'])

    category, reason = QueryClassifier(model).classify("What does fault E1 indicate?")

    assert category is QueryCategory.FACTUAL
    assert reason == "Specific guide fact."


def test_classifier_retries_once_for_malformed_output() -> None:
    model = FakeModel(["not json", '{"category":"BROAD","reason":"Needs several sections."}'])

    category, _ = QueryClassifier(model).classify("Explain the troubleshooting sequence.")

    assert category is QueryCategory.BROAD
    assert len(model.prompts) == 2


def test_expander_returns_exactly_three_alternatives() -> None:
    model = FakeModel(
        [
            '{"alternatives":["Pressure cause one?","Pressure cause two?","Pressure cause three?"]}'
        ]
    )

    alternatives = QueryExpander(model).expand("Why is hydraulic pressure low?")

    assert len(alternatives) == 3
    assert len(set(alternatives)) == 3
    assert "Why is hydraulic pressure low?" in model.prompts[0]


def test_expander_rejects_wrong_count_after_bounded_retry() -> None:
    model = FakeModel(
        [
            '{"alternatives":["one","two"]}',
            '{"alternatives":["still one","still two"]}',
        ]
    )

    try:
        QueryExpander(model).expand("Why is pressure low?")
    except Exception as exc:
        assert "three" in str(exc).lower() or "expansion" in str(exc).lower()
    else:
        raise AssertionError("Expansion must fail if it cannot produce exactly three items.")

    assert len(model.prompts) == 2


def test_classifier_does_not_retry_provider_failure() -> None:
    class FailedModel:
        def invoke(self, prompt):
            raise RuntimeError("private provider details")

    from src.errors import AppError

    try:
        QueryClassifier(FailedModel()).classify("Question")
    except AppError as exc:
        assert "language-model request failed" in str(exc)
        assert "private provider details" not in str(exc)
    else:
        raise AssertionError("Provider failure must be surfaced as a safe application error.")
