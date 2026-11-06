"""Generation and validation of exactly three aligned query alternatives."""

from __future__ import annotations

from typing import Any

from src.errors import AppError, ErrorKind
from src.structured_output import create_chat_model, invoke_json


class QueryExpander:
    def __init__(self, model: Any | None = None, settings: Any | None = None) -> None:
        if model is None:
            if settings is None:
                raise ValueError("Settings are required when no model is provided.")
            model = create_chat_model(settings)
        self._model = model

    def expand(self, question: str) -> tuple[str, str, str]:
        prompt = (
            "Generate exactly three distinct alternative phrasings of the original question "
            "about the Bosch Rexroth troubleshooting guide. Preserve the same intent and do "
            "not add new questions. Return only JSON with an alternatives array of exactly "
            f"three non-empty strings.\nOriginal question: {question}"
        )
        last_error: AppError | None = None
        for attempt in range(2):
            try:
                result = invoke_json(self._model, prompt)
                alternatives = result.get("alternatives")
                if (
                    not isinstance(alternatives, list)
                    or len(alternatives) != 3
                    or any(not isinstance(item, str) or not item.strip() for item in alternatives)
                ):
                    raise ValueError("Expected exactly three non-empty alternatives.")
                normalized = tuple(item.strip() for item in alternatives)
                if len({item.casefold() for item in normalized}) != 3:
                    raise ValueError("Alternatives must be distinct.")
                return normalized  # type: ignore[return-value]
            except AppError as exc:
                if exc.kind is ErrorKind.MODEL or attempt == 1:
                    raise
                last_error = exc
            except (ValueError, TypeError) as exc:
                last_error = AppError(ErrorKind.OUTPUT, "Query expansion did not return three distinct alternatives.")
                if attempt == 1:
                    raise last_error from exc
        raise last_error or AppError(ErrorKind.OUTPUT, "Query expansion did not return three alternatives.")
