"""Application configuration loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """Raised when a required setting is missing or invalid."""


def _project_path(value: str | None, default: str) -> Path:
    path = Path(value or default).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True, slots=True)
class Settings:
    groq_api_key: str | None = field(default=None, repr=False)
    llm_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    pdf_path: Path = PROJECT_ROOT / "Rexroth IndraDrive.pdf"
    vector_store_path: Path = PROJECT_ROOT / "vector_store" / "faiss_index"
    semantic_cache_path: Path = PROJECT_ROOT / "cache" / "semantic_cache.db"
    chunk_size: int = 1024
    chunk_overlap: int = 64
    factual_top_k: int = 2
    broad_top_k: int = 20
    rerank_top_k: int = 5
    query_expansion_count: int = 3
    semantic_cache_threshold: float = 0.90

    @classmethod
    def from_env(cls, *, require_api_key: bool = True) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        api_key = os.getenv("GROQ_API_KEY") or None
        if require_api_key and not api_key:
            raise ConfigurationError("GROQ_API_KEY is missing from the local environment.")

        try:
            threshold = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.90"))
            rerank_top_k = int(os.getenv("RERANK_TOP_K", "5"))
            chunk_size = int(os.getenv("CHUNK_SIZE", "1024"))
            chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "64"))
            factual_top_k = int(os.getenv("FACTUAL_TOP_K", "2"))
            broad_top_k = int(os.getenv("BROAD_TOP_K", "20"))
            query_expansion_count = int(os.getenv("QUERY_EXPANSION_COUNT", "3"))
        except ValueError as exc:
            raise ConfigurationError("A numeric application setting has an invalid value.") from exc

        if not 0.0 <= threshold <= 1.0:
            raise ConfigurationError("SEMANTIC_CACHE_THRESHOLD must be between 0 and 1.")
        if (
            chunk_size < 1
            or not 0 <= chunk_overlap < chunk_size
            or factual_top_k < 1
            or broad_top_k < 1
            or rerank_top_k < 1
        ):
            raise ConfigurationError("Chunk and retrieval limits must be positive and valid.")
        if query_expansion_count != 3:
            raise ConfigurationError("QUERY_EXPANSION_COUNT must remain exactly 3.")

        return cls(
            groq_api_key=api_key,
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            reranker_model=os.getenv(
                "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
            pdf_path=_project_path(os.getenv("PDF_PATH"), "Rexroth IndraDrive.pdf"),
            vector_store_path=_project_path(
                os.getenv("VECTOR_STORE_PATH"), "vector_store/faiss_index"
            ),
            semantic_cache_path=_project_path(
                os.getenv("SEMANTIC_CACHE_PATH"), "cache/semantic_cache.db"
            ),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            factual_top_k=factual_top_k,
            broad_top_k=broad_top_k,
            rerank_top_k=rerank_top_k,
            query_expansion_count=query_expansion_count,
            semantic_cache_threshold=threshold,
        )
