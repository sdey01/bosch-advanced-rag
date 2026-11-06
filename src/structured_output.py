"""Helpers for validated JSON-only language-model responses."""

from __future__ import annotations

import json
import re
from typing import Any

from src.errors import AppError, ErrorKind


def create_chat_model(settings: Any) -> Any:
    try:
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise AppError(
                ErrorKind.CONFIGURATION,
                "GROQ_API_KEY is missing from the local environment.",
            )
        return ChatGroq(model=settings.llm_model, api_key=settings.groq_api_key)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(ErrorKind.MODEL, "The Groq language model could not be initialized.") from exc


def invoke_json(model: Any, prompt: str) -> dict[str, Any]:
    try:
        response = model.invoke(prompt)
    except Exception as exc:
        raise AppError(ErrorKind.MODEL, "The language-model request failed.") from exc
    content = getattr(response, "content", response)
    if not isinstance(content, str):
        raise AppError(ErrorKind.OUTPUT, "The language model returned an invalid response format.")
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AppError(ErrorKind.OUTPUT, "The language model returned malformed structured output.") from exc
    if not isinstance(result, dict):
        raise AppError(ErrorKind.OUTPUT, "The language model returned an invalid response structure.")
    return result
