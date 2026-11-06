"""PDF ingestion with stable source fingerprints and original page metadata."""

from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from src.errors import AppError, ErrorKind
from src.models import Guide


def fingerprint_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise AppError(ErrorKind.DOCUMENT, "The guide PDF could not be read.") from exc
    return digest.hexdigest()


def load_pdf(path: Path) -> tuple[Guide, list[Document]]:
    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.is_file():
        raise AppError(ErrorKind.DOCUMENT, "The configured guide PDF could not be found.")
    try:
        loaded_documents = PyPDFLoader(str(pdf_path)).load()
    except Exception as exc:
        raise AppError(ErrorKind.DOCUMENT, "The guide PDF could not be opened or read.") from exc

    documents: list[Document] = []
    for document in loaded_documents:
        if not document.page_content.strip():
            continue
        metadata = dict(document.metadata)
        raw_page = metadata.get("page")
        try:
            page_number = int(raw_page) + 1 if raw_page is not None else None
        except (TypeError, ValueError):
            page_number = None
        metadata["page_number"] = page_number
        metadata["source_filename"] = pdf_path.name
        metadata["source"] = str(pdf_path)
        documents.append(Document(page_content=document.page_content, metadata=metadata))

    if not documents:
        raise AppError(ErrorKind.DOCUMENT, "The guide PDF did not contain extractable text.")

    guide = Guide(
        source_path=pdf_path,
        source_filename=pdf_path.name,
        source_fingerprint=fingerprint_file(pdf_path),
        page_count=len(loaded_documents),
    )
    return guide, documents
