"""Reusable fixtures that avoid live providers and heavyweight model downloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.models import QueryCategory, SourcePassage


class FakeChatModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> Any:
        self.calls.append(prompt)
        if not self.responses:
            raise RuntimeError("No configured fake response.")
        return type("FakeResponse", (), {"content": self.responses.pop(0)})()


class FakeEmbeddings:
    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0, 0.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture
def fake_chat_model() -> FakeChatModel:
    return FakeChatModel([])


@pytest.fixture
def fake_embeddings() -> FakeEmbeddings:
    return FakeEmbeddings()


@pytest.fixture
def sample_passage() -> SourcePassage:
    return SourcePassage(
        passage_id="passage-1",
        text="The guide lists a documented troubleshooting check.",
        source_filename="Rexroth IndraDrive.pdf",
        page_number=1,
        embedding=(1.0, 0.0),
    )


@pytest.fixture
def classification_payload() -> dict[str, str]:
    return {
        "category": QueryCategory.FACTUAL.value,
        "reason": "The question asks for a specific detail in the guide.",
    }


@pytest.fixture
def temporary_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "pdf": tmp_path / "guide.pdf",
        "index": tmp_path / "index",
        "cache": tmp_path / "cache.db",
    }
