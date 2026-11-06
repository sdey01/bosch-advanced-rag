"""Streamlit user interface for chat, evidence diagnostics, and cache monitoring."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.errors import AppError, user_message_for
from src.models import AnswerStatus, ConversationItem


def render_app(runtime: Any) -> None:
    st.title("Bosch Rexroth Troubleshooting Assistant")
    st.caption(f"Answers grounded in {runtime.source_filename}.")

    history: list[ConversationItem] = st.session_state.setdefault("conversation_history", [])
    left, center, right = st.columns([1.0, 3.0, 1.15], gap="medium")

    with left:
        st.subheader("Conversation history")
        if not history:
            st.caption("Your questions and answers will appear here.")
        for index, item in enumerate(reversed(history), start=1):
            with st.expander(f"Q: {item.question.question_text[:70]}", expanded=False):
                st.markdown("**You**")
                st.write(item.question.question_text)
                st.markdown("**Assistant**")
                st.write(item.answer.answer_text)

    with center:
        with st.form("question_form", clear_on_submit=True):
            question_text = st.text_input(
                "Ask about the troubleshooting guide",
                placeholder="For example: What does this fault code indicate?",
            )
            submitted = st.form_submit_button("Ask")

        if submitted:
            if not question_text.strip():
                st.warning("Enter a question about the guide.")
            else:
                try:
                    item = runtime.pipeline.handle(question_text)
                    history.append(item)
                except AppError as exc:
                    st.error(user_message_for(exc))
                except Exception:
                    st.error(
                        "The request could not be completed. Check the application configuration and try again."
                    )

        if history:
            latest = history[-1]
            st.subheader("Answer")
            st.markdown(f"**Question:** {latest.question.question_text}")
            st.write(latest.answer.answer_text)
            if latest.answer.status is AnswerStatus.CACHED:
                st.info("This answer was reused from the semantic cache.")
            elif latest.diagnostics.cache_outcome == "added":
                st.caption("Supported answer saved for reuse.")
            elif latest.diagnostics.cache_outcome == "write_error":
                st.warning("The answer is supported, but could not be saved for reuse.")
            elif latest.diagnostics.cache_outcome == "read_error":
                st.warning("Cache lookup was unavailable; this answer was processed without cache reuse.")
            if latest.answer.source_references:
                st.caption("Sources: " + "; ".join(latest.answer.source_references))

            if latest.answer.status is AnswerStatus.INSUFFICIENT_EVIDENCE:
                st.info("No supported answer was saved because sufficient guide evidence was unavailable.")

            _render_diagnostics(latest)

    with right:
        _render_cache_panel(
            runtime.cache,
            runtime.source_fingerprint,
            history[-1] if history else None,
        )


def _render_diagnostics(item: ConversationItem) -> None:
    with st.expander("Pipeline diagnostics", expanded=True):
        st.write(f"**Category:** {item.question.category.value}")
        st.write(f"**Classifier reasoning:** {item.question.classification_reason}")
        st.write(f"**Route:** {item.diagnostics.route}")
        st.write(f"**Cache outcome:** {item.diagnostics.cache_outcome}")
        if item.diagnostics.cache_similarity is not None:
            st.write(f"**Closest cache similarity:** {item.diagnostics.cache_similarity:.3f}")

        if item.question.query_alternatives:
            st.markdown("**Query alternatives**")
            for alternative in item.question.query_alternatives:
                st.write(f"- {alternative}")

        if item.diagnostics.retrieved_passages:
            st.markdown("**Retrieved passages**")
            for passage in item.diagnostics.retrieved_passages:
                _render_passage(passage)

        if item.diagnostics.reranked_passages:
            st.markdown("**Broad-query reranking**")
            for position, passage in enumerate(item.diagnostics.reranked_passages, start=1):
                score = (
                    f" | score {passage.rerank_score:.4f}"
                    if passage.rerank_score is not None
                    else ""
                )
                st.write(f"{position}. {passage.source_filename}, page {passage.page_number}{score}")
            st.caption(
                "Passages used for the answer: "
                + ", ".join(item.diagnostics.selected_passage_ids)
            )

        st.markdown("**Stage latency**")
        for stage, seconds in item.diagnostics.stage_durations.items():
            st.write(f"- {stage.replace('_', ' ').title()}: {seconds * 1000:.1f} ms")
        st.write(f"**Total:** {item.diagnostics.total_duration * 1000:.1f} ms")


def _render_passage(passage: Any) -> None:
    page = f"page {passage.page_number}" if passage.page_number is not None else "page unavailable"
    score = (
        f" | similarity {passage.retrieval_score:.4f}"
        if passage.retrieval_score is not None
        else ""
    )
    st.markdown(f"**{passage.source_filename}, {page}{score}**")
    st.write(passage.text)


def _render_cache_panel(
    cache: Any,
    source_fingerprint: str,
    latest: ConversationItem | None,
) -> None:
    st.subheader("Semantic cache")
    st.markdown("**Latest activity**")
    if latest is None:
        st.caption("No cache activity in this session yet.")
    else:
        outcome = latest.diagnostics.cache_outcome
        if outcome == "hit":
            st.write("Cache hit: existing supported answer reused.")
        elif outcome == "added":
            st.write("Cache miss: new supported answer added.")
        elif outcome == "miss":
            st.write("Cache miss: no qualifying entry found.")
        elif outcome == "read_error":
            st.write("Cache lookup failed; this interaction proceeded without reuse.")
        elif outcome == "write_error":
            st.write("The supported answer could not be saved.")
        else:
            st.write("Cache not used for this interaction.")
        if latest.diagnostics.cache_similarity is not None:
            st.write(f"Closest match: {latest.diagnostics.cache_similarity:.3f}")
        if latest.diagnostics.cache_entry_id:
            action = "Reused entry" if outcome == "hit" else "Created entry"
            st.write(f"{action}: {latest.diagnostics.cache_entry_id}")

    try:
        stats = cache.stats()
        entries = cache.list_entries()
    except AppError as exc:
        st.error(user_message_for(exc))
        return

    st.metric("Entries", stats.total_entries)
    st.metric("Hits", stats.hits)
    st.metric("Misses", stats.misses)
    st.metric("Hit ratio", f"{stats.hit_ratio:.1%}")
    if not entries:
        st.caption("No supported answers are cached yet.")
        return

    st.markdown("**Saved entries**")
    for entry in entries:
        stale = entry.source_fingerprint != source_fingerprint
        label = (
            f"{entry.question_text[:70]} (stale source; not reused)"
            if stale
            else entry.question_text[:70]
        )
        with st.expander(label, expanded=False):
            st.write(f"**Category:** {entry.category.value}")
            st.write(f"**Created:** {entry.created_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
            st.write(entry.answer_text)
