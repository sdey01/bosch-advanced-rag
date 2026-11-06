import streamlit as st

from src.models import (
    Answer,
    AnswerStatus,
    CacheStats,
    ConversationItem,
    InteractionDiagnostics,
    QueryCategory,
    Question,
    SourcePassage,
)
from src.ui import render_app


class FakeCache:
    def stats(self):
        return CacheStats(total_entries=0, hits=0, misses=0)

    def list_entries(self):
        return []


class FakePipeline:
    def handle(self, question_text):
        question = Question(
            question_text,
            QueryCategory.BROAD,
            "The question needs a multi-step explanation.",
            ("alternative one", "alternative two", "alternative three"),
        )
        retrieved = SourcePassage(
            "p1",
            "A supported troubleshooting passage.",
            "guide.pdf",
            1,
            retrieval_score=0.8,
            rerank_score=0.9,
        )
        answer = Answer(
            "A source-supported answer.",
            ("p1",),
            AnswerStatus.SUPPORTED,
            ("guide.pdf, page 1",),
        )
        diagnostics = InteractionDiagnostics(
            route="broad",
            cache_outcome="miss",
            cache_similarity=0.42,
            stage_durations={"classification": 0.01, "reranking": 0.02},
            total_duration=0.03,
            retrieved_passages=(retrieved,),
            reranked_passages=(retrieved,),
            selected_passage_ids=("p1",),
        )
        return ConversationItem(question, answer, diagnostics)


class FakeRuntime:
    source_filename = "guide.pdf"
    source_fingerprint = "fixture-source"
    cache = FakeCache()
    pipeline = FakePipeline()


st.set_page_config(page_title="UI test", layout="wide")
render_app(FakeRuntime())
