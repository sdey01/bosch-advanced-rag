"""Safe user-facing errors for expected application failures."""

from __future__ import annotations

import re
from enum import StrEnum


class ErrorKind(StrEnum):
    CONFIGURATION = "configuration"
    DOCUMENT = "document"
    INDEX = "index"
    MODEL = "model"
    RETRIEVAL = "retrieval"
    RERANKING = "reranking"
    CACHE = "cache"
    OUTPUT = "output"
    UNKNOWN = "unknown"


class AppError(Exception):
    """An expected failure with a safe message suitable for the user interface."""

    def __init__(self, kind: ErrorKind, user_message: str) -> None:
        super().__init__(user_message)
        self.kind = kind
        self.user_message = user_message


_SECRET_PATTERNS = (
    re.compile(r"(?i)(gsk_[A-Za-z0-9]{8,})"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
)


def redact_secrets(text: str) -> str:
    """Remove recognizable credential values before diagnostic display."""
    redacted = _SECRET_PATTERNS[0].sub("[REDACTED]", text)
    redacted = _SECRET_PATTERNS[1].sub(r"\1[REDACTED]", redacted)
    return _SECRET_PATTERNS[2].sub(r"\1[REDACTED]", redacted)


def user_message_for(error: BaseException) -> str:
    """Return only approved messages; never expose arbitrary exception details."""
    if isinstance(error, AppError):
        return redact_secrets(error.user_message)
    return "The request could not be completed. Check the application configuration and try again."
