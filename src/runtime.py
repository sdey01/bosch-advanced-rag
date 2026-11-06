"""Application runtime assembly for local retrieval and Groq inference."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from src.config import ConfigurationError, Settings
from src.document_chunker import chunk_guide
from src.document_loader import load_pdf
from src.embeddings import EmbeddingService
from src.errors import AppError, ErrorKind
from src.query_classifier import QueryClassifier
from src.query_expansion import QueryExpander
from src.rag_pipeline import RAGPipeline
from src.reranker import Reranker
from src.response_generator import ResponseGenerator
from src.retriever import Retriever
from src.semantic_cache import SemanticCache
from src.structured_output import create_chat_model
from src.vector_store import VectorStore


def cache_source_fingerprint(pdf_fingerprint: str, embedding_model: str) -> str:
    identity = f"{pdf_fingerprint}\0{embedding_model}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


@dataclass(slots=True)
class Runtime:
    settings: Settings
    pipeline: RAGPipeline
    cache: SemanticCache
    source_filename: str
    source_fingerprint: str


def build_runtime(settings: Settings | None = None) -> Runtime:
    try:
        active_settings = settings or Settings.from_env()
    except ConfigurationError as exc:
        raise AppError(ErrorKind.CONFIGURATION, str(exc)) from exc

    embeddings = EmbeddingService(active_settings.embedding_model)
    guide, pages = load_pdf(active_settings.pdf_path)
    chunks = chunk_guide(pages, active_settings)
    vector_store = VectorStore.open_or_build(
        active_settings.vector_store_path,
        chunks,
        source_fingerprint=guide.source_fingerprint,
        embedding_model=active_settings.embedding_model,
        chunk_size=active_settings.chunk_size,
        chunk_overlap=active_settings.chunk_overlap,
        embeddings=embeddings,
    )
    cache = SemanticCache(active_settings.semantic_cache_path)
    model: Any = create_chat_model(active_settings)
    classifier = QueryClassifier(model=model)
    expander = QueryExpander(model=model)
    generator = ResponseGenerator(model=model)
    reranker = Reranker(
        active_settings.reranker_model,
        top_k=active_settings.rerank_top_k,
    )
    pipeline = RAGPipeline(
        classifier=classifier,
        expander=expander,
        retriever=Retriever(vector_store, embeddings, active_settings),
        reranker=reranker,
        generator=generator,
        source_fingerprint=cache_source_fingerprint(
            guide.source_fingerprint,
            active_settings.embedding_model,
        ),
        cache=cache,
        embeddings=embeddings,
        cache_threshold=active_settings.semantic_cache_threshold,
        rerank_top_k=active_settings.rerank_top_k,
    )
    return Runtime(
        active_settings,
        pipeline,
        cache,
        guide.source_filename,
        pipeline.source_fingerprint,
    )
