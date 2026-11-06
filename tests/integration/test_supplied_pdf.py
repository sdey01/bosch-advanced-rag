from __future__ import annotations

import os
from pathlib import Path

import pytest
from langchain_core.documents import Document

from src.config import Settings
from src.document_chunker import chunk_guide
from src.document_loader import load_pdf
from src.embeddings import EmbeddingService
from src.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = PROJECT_ROOT / "Rexroth IndraDrive.pdf"


@pytest.mark.skipif(
    os.getenv("RUN_SUPPLIED_PDF_TEST") != "1",
    reason="Set RUN_SUPPLIED_PDF_TEST=1 to run CPU model and supplied-PDF integration checks.",
)
def test_supplied_pdf_extracts_pages_and_builds_local_index(tmp_path) -> None:
    settings = Settings(
        pdf_path=PDF_PATH,
        vector_store_path=tmp_path / "index",
        semantic_cache_path=tmp_path / "cache.db",
    )
    guide, pages = load_pdf(settings.pdf_path)
    chunks = chunk_guide(pages, settings)
    store = VectorStore.open_or_build(
        settings.vector_store_path,
        chunks,
        source_fingerprint=guide.source_fingerprint,
        embedding_model=settings.embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        embeddings=EmbeddingService(settings.embedding_model),
    )

    assert guide.page_count > 0
    assert chunks
    assert all(chunk.metadata["source_filename"] == PDF_PATH.name for chunk in chunks)
    assert all(chunk.metadata.get("page_number") for chunk in chunks)
    assert store.path.joinpath("index.faiss").is_file()
