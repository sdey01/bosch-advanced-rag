# Implementation Plan: Bosch Rexroth Troubleshooting Assistant

**Branch**: `001-bosch-rexroth-rag` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-bosch-rexroth-rag/spec.md`

## Summary

Deliver a local, desktop-oriented assistant that answers Bosch Rexroth guide questions with
traceable document evidence. Ingest and index the supplied PDF with page metadata; classify
questions, check a persistent semantic cache, and, on relevant cache misses, expand the query
and route retrieval by category. Factual questions use at most two passages; broad questions
rank up to 20 candidates and use up to five by default. Generate answers from the original
question and selected evidence, then display conversation, evidence, cache activity, and
stage-level latency. The selected components and model requirements follow the PRD; see
[research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Streamlit; LangChain PDF and text-splitting integrations; Groq
client integration; sentence-transformers; FAISS; PyPDF; python-dotenv; pytest for tests.
Resolve compatible package versions during implementation and record them in the project
dependency manifest.

**Storage**: Local FAISS index for guide passages; persistent SQLite semantic cache; in-memory
application-session conversation history; an index manifest records the source fingerprint,
embedding model, and chunking settings. The source PDF currently present is
`Rexroth IndraDrive.pdf`.

**Testing**: pytest unit and integration tests plus manual end-to-end Streamlit validation
against the supplied PDF and Groq service. Mock external calls for isolated tests; use real
services only for explicit integration validation.

**Target Platform**: Windows desktop, launched locally from the project root.

**Project Type**: Local interactive web application with a Python retrieval and answer pipeline.

**Performance Goals**: Record elapsed time for every executed pipeline stage and total
interaction latency. Avoid repeated local model loading and index construction; a cache hit
skips expansion, retrieval, ranking, and generation. The PRD specifies no numeric latency SLA.

**Constraints**: Use GPT-OSS 120B through Groq for all LLM operations. Run
`sentence-transformers/all-MiniLM-L6-v2` embeddings and
`cross-encoder/ms-marco-MiniLM-L-6-v2` reranking locally on CPU. Preserve existing
environment credentials. Chunk the PDF at size 1024 with overlap 64 and retain source/page
metadata. Use at most two factual passages; broad retrieval considers up to 20 candidates and
defaults to five final passages. Cache only successful, evidence-supported relevant answers.
On cache read failure continue without cache reuse and report the issue; on write failure
return a supported answer but report that it was not saved. Do not reuse cache entries whose
evidence belongs to an older source fingerprint.

**Scale/Scope**: Single local application for questions about the supplied troubleshooting
guide; user concurrency and document-corpus growth targets are not specified.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle or requirement | Design compliance |
|---|---|
| Document-Grounded Answers | Answers use retrieved guide passages; insufficient evidence is stated, and irrelevant queries bypass retrieval and caching. |
| Secret and Configuration Protection | Credentials remain in local environment configuration; configuration is centralized and secret values are not displayed. |
| Modular, Minimal Architecture | Pipeline responsibilities are separated into small modules; fixed PRD models and tools are retained. |
| Transparent Retrieval and Diagnostics | The UI exposes classification, route, expansions, evidence, applicable ranking, cache outcomes, and stage latency. |
| Reliability, Validation, and Performance | Expected failures receive user-safe messages; tests cover pipeline behavior; CPU models, persistent index, and cache are reused. |
| Additional Constraints | Python 3.12, local FAISS/SQLite storage, page metadata, retrieval limits, and desktop Streamlit UI are included. |
| Development Workflow | Tests target classification, expansion, routing, cache behavior, grounding, diagnostics, and the supplied PDF end to end. |

**Gate result**: PASS. No constitution conflicts or unjustified complexity are identified.

## Project Structure

### Documentation (this feature)

```text
specs/001-bosch-rexroth-rag/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── user-interface.md
└── tasks.md                 # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
app.py
src/
├── config.py
├── document_loader.py
├── document_chunker.py
├── embeddings.py
├── vector_store.py
├── query_classifier.py
├── query_expansion.py
├── retriever.py
├── reranker.py
├── semantic_cache.py
├── response_generator.py
└── rag_pipeline.py
tests/
├── unit/
└── integration/
data/                         # Optional managed location; do not overwrite the supplied PDF
vector_store/
cache/
requirements.txt
README.md
.env.example
```

**Structure Decision**: Use the modular single-project layout recommended by the PRD. Keep
the Streamlit entry point at the root and isolate document processing, pipeline stages, cache,
and configuration under `src/`. Organize tests by unit and integration scope. Use the existing
root-level `Rexroth IndraDrive.pdf` as the initial source unless configuration selects another
guide; do not move or overwrite user data.

## Phase 0: Outline & Research

The fixed technology choices and processing limits come from `PRD.md` and the project
constitution. Research decisions about pipeline orchestration, grounding, persistence,
failure behavior, observability, and validation are recorded in [research.md](./research.md).
No product-level clarification is required to proceed; no numeric latency SLA or concurrency
target is specified, so stage timing is measured without inventing a hard service-level target.

## Phase 1: Design & Contracts

- [data-model.md](./data-model.md) defines guide, passage, question, answer, cache,
  diagnostics, and conversation records with validation rules and relationships.
- [contracts/user-interface.md](./contracts/user-interface.md) describes the user-facing
  question flow, diagnostics, cache monitoring, and user-safe error behavior. The application
  does not specify a separate public programmatic API.
- [quickstart.md](./quickstart.md) defines Windows setup, launch, automated checks, and
  end-to-end scenarios for validating the feature.

**Post-design gate result**: PASS. The design preserves source attribution and evidence
grounding, uses local persistence and CPU inference where required, avoids work on cache hits,
and keeps user-visible behavior measurable and testable.

## Complexity Tracking

No constitution violations or unjustified complexity require tracking.
