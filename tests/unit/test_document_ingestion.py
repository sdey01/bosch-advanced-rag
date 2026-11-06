from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

import src.document_loader as document_loader
from src.document_chunker import chunk_documents


def test_load_pdf_preserves_source_and_one_based_pages(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "guide.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test fixture")
    documents = [
        Document(page_content="Fault diagnosis.", metadata={"page": 0, "source": str(pdf_path)}),
        Document(page_content="Pressure check.", metadata={"page": 1, "source": str(pdf_path)}),
    ]

    class FakeLoader:
        def __init__(self, path: str) -> None:
            assert path == str(pdf_path)

        def load(self) -> list[Document]:
            return documents

    monkeypatch.setattr(document_loader, "PyPDFLoader", FakeLoader)
    guide, loaded = document_loader.load_pdf(pdf_path)

    assert guide.source_filename == "guide.pdf"
    assert guide.page_count == 2
    assert len(guide.source_fingerprint) == 64
    assert [doc.metadata["page_number"] for doc in loaded] == [1, 2]
    assert all(doc.metadata["source_filename"] == "guide.pdf" for doc in loaded)


def test_load_pdf_rejects_empty_extraction(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "guide.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test fixture")

    class EmptyLoader:
        def __init__(self, path: str) -> None:
            _ = path

        def load(self) -> list[Document]:
            return [Document(page_content=" ", metadata={"page": 0})]

    monkeypatch.setattr(document_loader, "PyPDFLoader", EmptyLoader)

    try:
        document_loader.load_pdf(pdf_path)
    except Exception as exc:
        assert "text" in str(exc).lower() or "extract" in str(exc).lower()
    else:
        raise AssertionError("Empty PDF extraction must fail.")


def test_chunk_documents_obeys_size_and_overlap() -> None:
    text = "A" * 2500
    chunks = chunk_documents(
        [Document(page_content=text, metadata={"page_number": 3, "source_filename": "guide.pdf"})]
    )

    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 1024 for chunk in chunks)
    assert all(chunk.metadata["page_number"] == 3 for chunk in chunks)
    assert all(chunk.metadata["source_filename"] == "guide.pdf" for chunk in chunks)
    assert chunks[0].page_content[-64:] == chunks[1].page_content[:64]
