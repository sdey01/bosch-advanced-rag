"""Local FAISS index persistence with source/configuration manifest validation."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Protocol, Sequence

import faiss
import numpy as np
from langchain_core.documents import Document

from src.errors import AppError, ErrorKind
from src.models import SourcePassage


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...


class VectorStore:
    def __init__(
        self,
        path: Path,
        index: faiss.Index,
        passages: list[SourcePassage],
        manifest: dict[str, object],
    ) -> None:
        self.path = path
        self._index = index
        self.passages = passages
        self.manifest = manifest

    @classmethod
    def open_or_build(
        cls,
        path: Path,
        documents: Sequence[Document],
        *,
        source_fingerprint: str,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        embeddings: EmbeddingProvider,
        force_rebuild: bool = False,
    ) -> "VectorStore":
        target = Path(path).expanduser().resolve()
        expected = {
            "source_fingerprint": source_fingerprint,
            "embedding_model": embedding_model,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        if not force_rebuild and target.is_dir():
            try:
                store = cls._load(target)
                if store.manifest == expected:
                    return store
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
                pass

        return cls._build_and_replace(target, documents, expected, embeddings)

    @classmethod
    def _load(cls, path: Path) -> "VectorStore":
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        raw_passages = json.loads((path / "passages.json").read_text(encoding="utf-8"))
        passages = [
            SourcePassage(
                passage_id=item["passage_id"],
                text=item["text"],
                source_filename=item["source_filename"],
                page_number=item.get("page_number"),
            )
            for item in raw_passages
        ]
        index = faiss.read_index(str(path / "index.faiss"))
        if index.ntotal != len(passages):
            raise ValueError("Persisted index and passage metadata do not match.")
        return cls(path, index, passages, manifest)

    @classmethod
    def _build_and_replace(
        cls,
        target: Path,
        documents: Sequence[Document],
        manifest: dict[str, object],
        embeddings: EmbeddingProvider,
    ) -> "VectorStore":
        texts = [document.page_content for document in documents if document.page_content.strip()]
        source_documents = [document for document in documents if document.page_content.strip()]
        if not texts:
            raise AppError(ErrorKind.INDEX, "No guide passages are available to index.")
        try:
            vectors = np.asarray(embeddings.embed_documents(texts), dtype=np.float32)
            if vectors.ndim != 2 or vectors.shape[0] != len(source_documents) or vectors.shape[1] == 0:
                raise ValueError("Embedding count or dimensions did not match the guide passages.")
            if not np.isfinite(vectors).all():
                raise ValueError("Embedding values must be finite.")
            faiss.normalize_L2(vectors)
            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)

            passages = []
            for position, document in enumerate(source_documents):
                passage_id = str(document.metadata.get("passage_id") or f"passage-{position + 1}")
                passages.append(
                    SourcePassage(
                        passage_id=passage_id,
                        text=document.page_content,
                        source_filename=str(document.metadata.get("source_filename", "")),
                        page_number=document.metadata.get("page_number"),
                    )
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorKind.INDEX, "The guide could not be embedded for retrieval.") from exc

        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.with_name(f"{target.name}.staging-{uuid.uuid4().hex}")
        backup = target.with_name(f"{target.name}.backup-{uuid.uuid4().hex}")
        moved_existing = False
        try:
            staging.mkdir()
            faiss.write_index(index, str(staging / "index.faiss"))
            (staging / "passages.json").write_text(
                json.dumps(
                    [
                        {
                            "passage_id": passage.passage_id,
                            "text": passage.text,
                            "source_filename": passage.source_filename,
                            "page_number": passage.page_number,
                        }
                        for passage in passages
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (staging / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            if target.exists():
                os.replace(target, backup)
                moved_existing = True
            os.replace(staging, target)
        except Exception as exc:
            if moved_existing and backup.exists() and not target.exists():
                os.replace(backup, target)
            raise AppError(ErrorKind.INDEX, "The local retrieval index could not be saved.") from exc
        finally:
            if staging.exists():
                shutil.rmtree(staging)

        if backup.exists():
            shutil.rmtree(backup)
        return cls(target, index, passages, dict(manifest))

    def search(self, query_embedding: Sequence[float], k: int) -> list[tuple[SourcePassage, float]]:
        if k <= 0 or not self.passages:
            return []
        vector = np.asarray([query_embedding], dtype=np.float32)
        if vector.shape[1] != self._index.d:
            raise AppError(ErrorKind.RETRIEVAL, "Question embedding does not match the guide index.")
        if not np.isfinite(vector).all():
            raise AppError(ErrorKind.RETRIEVAL, "Question embedding is invalid.")
        faiss.normalize_L2(vector)
        scores, indices = self._index.search(vector, min(k, len(self.passages)))
        results: list[tuple[SourcePassage, float]] = []
        for score, index in zip(scores[0], indices[0]):
            if index < 0:
                continue
            passage = self.passages[int(index)]
            results.append((passage, float(score)))
        return results
