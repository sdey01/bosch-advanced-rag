from __future__ import annotations

from langchain_core.documents import Document

from src.vector_store import VectorStore


class FakeEmbeddings:
    def __init__(self):
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


def documents(text="Guide evidence"):
    return [
        Document(
            page_content=text,
            metadata={
                "passage_id": "p1",
                "source_filename": "guide.pdf",
                "page_number": 2,
            },
        )
    ]


def open_store(path, fingerprint, docs, embeddings):
    return VectorStore.open_or_build(
        path,
        docs,
        source_fingerprint=fingerprint,
        embedding_model="test-embedding-model",
        chunk_size=1024,
        chunk_overlap=64,
        embeddings=embeddings,
    )


def test_vector_store_persists_and_reuses_matching_manifest(tmp_path) -> None:
    path = tmp_path / "vector_index"
    first_embeddings = FakeEmbeddings()
    built = open_store(path, "source-v1", documents(), first_embeddings)

    second_embeddings = FakeEmbeddings()
    loaded = open_store(path, "source-v1", documents(), second_embeddings)

    assert first_embeddings.calls == 1
    assert second_embeddings.calls == 0
    assert loaded.manifest["source_fingerprint"] == "source-v1"
    result = loaded.search([1.0, 0.0], 1)
    assert result[0][0].source_filename == "guide.pdf"
    assert result[0][0].page_number == 2
    assert result[0][1] > 0.99


def test_vector_store_rebuilds_when_source_fingerprint_changes(tmp_path) -> None:
    path = tmp_path / "vector_index"
    open_store(path, "source-v1", documents(), FakeEmbeddings())

    replacement_embeddings = FakeEmbeddings()
    rebuilt = open_store(
        path,
        "source-v2",
        documents("Updated evidence"),
        replacement_embeddings,
    )

    assert replacement_embeddings.calls == 1
    assert rebuilt.manifest["source_fingerprint"] == "source-v2"
    assert rebuilt.search([1.0, 0.0], 1)[0][0].text == "Updated evidence"
