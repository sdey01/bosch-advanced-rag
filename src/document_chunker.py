"""Recursive chunking that preserves page-level source metadata."""

from __future__ import annotations

import hashlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Settings


def chunk_documents(
    documents: list[Document],
    *,
    chunk_size: int = 1024,
    chunk_overlap: int = 64,
) -> list[Document]:
    if chunk_size < 1:
        raise ValueError("Chunk size must be positive.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        source = str(chunk.metadata.get("source_filename", ""))
        page = str(chunk.metadata.get("page_number", "unknown"))
        start = str(chunk.metadata.get("start_index", index))
        digest = hashlib.sha256(
            f"{source}\0{page}\0{start}\0{chunk.page_content}".encode("utf-8")
        ).hexdigest()[:20]
        chunk.metadata["passage_id"] = f"passage-{digest}"
    return chunks


def chunk_guide(documents: list[Document], settings: Settings) -> list[Document]:
    return chunk_documents(
        documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
