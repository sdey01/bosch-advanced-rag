"""LLM-based routing into factual, broad, and irrelevant categories."""

from __future__ import annotations

from typing import Any

from src.errors import AppError, ErrorKind
from src.models import QueryCategory
from src.structured_output import create_chat_model, invoke_json


class QueryClassifier:
    def __init__(self, model: Any | None = None, settings: Any | None = None) -> None:
        if model is None:
            if settings is None:
                raise ValueError("Settings are required when no model is provided.")
            model = create_chat_model(settings)
        self._model = model

    def classify(self, question: str) -> tuple[QueryCategory, str]:
        prompt = (
            "Classify the user's question about the Bosch Rexroth troubleshooting guide. "
            "Return only a JSON object with string fields category and reason. category must "
            "be exactly FACTUAL, BROAD, or IRRELEVANT. FACTUAL asks for a specific guide "
            "detail; BROAD needs information from multiple guide sections; IRRELEVANT is "
            "unrelated to the guide. Examples: 'What does error E001 indicate?' is FACTUAL; "
            "'Explain the troubleshooting steps for pressure faults' is BROAD; "
            "'What is the weather?' is IRRELEVANT.\n"
            f"Question: {question}"
        )
        last_error: AppError | None = None
        for attempt in range(2):
            try:
                result = invoke_json(self._model, prompt)
                category = QueryCategory(str(result.get("category", "")).strip().upper())
                reason = result.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError("Missing classifier reason.")
                return category, reason.strip()
            except AppError as exc:
                if exc.kind is ErrorKind.MODEL or attempt == 1:
                    raise
                last_error = exc
            except (ValueError, TypeError) as exc:
                last_error = AppError(ErrorKind.OUTPUT, "The classifier response was invalid.")
                if attempt == 1:
                    raise last_error from exc
        raise last_error or AppError(ErrorKind.OUTPUT, "The classifier response was invalid.")
