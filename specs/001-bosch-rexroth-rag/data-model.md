# Data Model: Bosch Rexroth Troubleshooting Assistant

This design describes logical records and validation; it does not prescribe a database schema.

## Guide

Represents the source troubleshooting PDF.

| Field | Meaning | Validation |
|---|---|---|
| `source_path` | Location of the source PDF | Must resolve to a readable PDF before ingestion |
| `source_filename` | Original filename shown to users | Required for every indexed passage |
| `source_fingerprint` | Identity of the indexed source revision | Recomputed when checking whether the persisted index is stale |
| `page_count` | Number of pages processed | Non-negative; empty extraction is an error state |
| `index_manifest` | Source fingerprint, embedding model identifier, and chunking settings for the persisted index | All values must match current configuration before index reuse |

**Relationships**: One guide has zero or more source passages. Each passage retains its source
filename and original page reference.

## Source Passage

Represents a retrievable portion of a guide page.

| Field | Meaning | Validation |
|---|---|---|
| `passage_id` | Stable identity within the indexed guide | Unique within the index |
| `text` | Extracted passage text | Non-empty after normalization |
| `source_filename` | Guide filename | Required |
| `page_number` | Original PDF page | Preserve the loader's page numbering convention consistently |
| `embedding` | Local vector representation | Generated using the configured embedding model |
| `retrieval_score` | Similarity score for an interaction | Optional; shown only when available |
| `rerank_score` | Cross-encoder relevance score | Optional; applicable to broad-query reranking only |

## Question

Represents one user submission and its classification.

| Field | Meaning | Validation |
|---|---|---|
| `question_text` | Exact text submitted by the user | Required and retained unchanged for answer generation |
| `category` | `FACTUAL`, `BROAD`, or `IRRELEVANT` | Exactly one allowed value |
| `classification_reason` | Explanation of the category | Displayed when returned; malformed output is an error |
| `query_alternatives` | Intent-preserving alternate formulations | Exactly three for a relevant cache miss; none for irrelevant or cache-hit routes |

## Answer

Represents a generated or reused response.

| Field | Meaning | Validation |
|---|---|---|
| `answer_text` | User-facing response to the original question | Required for successful or cached responses |
| `supporting_passage_ids` | Evidence used for the answer | Must identify available guide evidence for cache eligibility |
| `status` | `SUPPORTED`, `INSUFFICIENT_EVIDENCE`, `ERROR`, or `CACHED` | `CACHED` denotes reuse; unsupported and error answers are not cacheable |
| `source_references` | Source filenames and page references | Include whenever available |

## Cache Entry

Represents a successfully answered, relevant question available for semantic reuse.

| Field | Meaning | Validation |
|---|---|---|
| `entry_id` | Cache record identity | Unique |
| `question_text` | Original successful question | Required |
| `question_embedding` | Local semantic representation | Same embedding model as query and guide |
| `answer_text` | Previously supported answer | Required; failed or unsupported answers are excluded |
| `category` | Original question category | `FACTUAL` or `BROAD` only |
| `created_at` | Entry creation time | Stored consistently for display |
| `evidence_metadata` | Supporting passage/source references | Retain available evidence information |
| `source_fingerprint` | Source revision used to produce the evidence | Must match the currently indexed source for reuse |
| `hit_count` | Number of times this entry was reused | Non-negative; increased on a qualifying hit |

**Match rule**: A cache candidate is reusable only when the question is relevant and its
similarity meets the configured threshold and its evidence fingerprint matches the current
guide. A miss, stale-source entry, or below-threshold candidate cannot return that answer.
Cache hit/miss totals remain available across application restarts. On cache read failure, the
assistant continues without cache reuse and reports the failure; on write failure, a supported
answer can be returned with an explicit not-saved status.

## Interaction Diagnostics

Represents observable processing for one submitted question.

| Field | Meaning | Validation |
|---|---|---|
| `route` | Irrelevant, factual, broad, cache-hit, or error path | Must match the stages that actually ran |
| `cache_outcome` | Hit, miss, or not applicable | Irrelevant questions do not enter semantic cache lookup |
| `cache_similarity` | Closest candidate score, when available | Optional |
| `stage_durations` | Elapsed time for each executed stage | Non-negative; skipped stages are absent/not-run |
| `total_duration` | End-to-end elapsed time | Non-negative and displayed for each interaction |
| `cache_entry_id` | Entry created or reused, when applicable | Optional |

## Conversation Item

Represents one question-answer pair visible during the current application session.

| Field | Meaning | Validation |
|---|---|---|
| `question` | Associated user question | Required |
| `answer` | Associated assistant response | Required, including a safe user-facing failure response where applicable |
| `diagnostics` | Processing details for the interaction | Linked to the same question |

**Lifecycle**: A submission is classified; irrelevant questions terminate with an out-of-scope
response. Relevant questions enter cache lookup. A hit returns a cached answer; a miss proceeds
through expansion, retrieval and (for broad questions) reranking. Malformed model output may
receive one bounded retry; persistent failure is shown explicitly. Empty or insufficient
evidence results in abstention. The answer is shown with diagnostics and is added to the cache
only when successful and supported by guide evidence.
