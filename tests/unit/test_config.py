from __future__ import annotations

import pytest

from src.config import ConfigurationError, Settings


def test_settings_loads_required_models_and_retrieval_defaults(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    for key in ("LLM_MODEL", "EMBEDDING_MODEL", "RERANKER_MODEL", "SEMANTIC_CACHE_THRESHOLD"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.llm_model == "openai/gpt-oss-120b"
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert settings.chunk_size == 1024
    assert settings.chunk_overlap == 64
    assert settings.factual_top_k == 2
    assert settings.broad_top_k == 20
    assert settings.rerank_top_k == 5
    assert settings.query_expansion_count == 3
    assert "test-secret" not in repr(settings)


def test_settings_require_key_and_validate_threshold(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        Settings.from_env()

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setenv("SEMANTIC_CACHE_THRESHOLD", "1.5")
    with pytest.raises(ConfigurationError, match="between 0 and 1"):
        Settings.from_env()
