# Research: Bosch Rexroth Troubleshooting Assistant

## Retrieval and routing

**Decision**: Classify each submission as `FACTUAL`, `BROAD`, or `IRRELEVANT` before other
query processing. Irrelevant submissions stop without retrieval or cache insertion. For each
relevant cache miss, generate exactly three alternatives and search with the original plus
alternatives. Deduplicate candidates and enforce a single overall limit of two passages for
factual queries or 20 candidates for broad queries. Rerank only broad-query candidates against
the original question; select at most five by default.

**Rationale**: This follows the PRD routing order and prevents multiple expanded searches from
silently exceeding the stated retrieval limits. Scoring and deduplication rules must be
consistent so the final candidate set has one unambiguous limit.

**Alternatives considered**: Treating each expansion as an independent question with a separate
top-k allowance was rejected because it can exceed the required overall limit. Reranking factual
queries was rejected because the PRD explicitly excludes it.

## Answer grounding and cache eligibility

**Decision**: Send the original question and selected passages to the required GPT-OSS 120B
answer generator. Require it to use only those passages, preserve technical terminology, cite
available source pages, and explicitly say when the evidence is insufficient. Cache only a
successfully generated answer when supporting guide evidence is present; never cache irrelevant,
failed, or unsupported outcomes.

**Rationale**: The source guide is the authority for technical claims. Reusing an unsupported
answer would make the cache a path for repeating fabricated guidance.

**Alternatives considered**: Generating from model knowledge when retrieval is empty was
rejected. Caching all completed model responses, regardless of evidence, was also rejected.

## Semantic-cache behavior and persistence

**Decision**: Use a local persistent cache with the question representation, answer, category,
timestamp, and available evidence metadata. Compare relevant questions using the configured
similarity threshold (initial PRD value 0.90); count hits and misses and expose entries and
activity. Perform classification before cache lookup, and on a qualifying hit return the
stored response without expansion, retrieval, reranking, or answer generation.

**Rationale**: This preserves the PRD's classification and routing order while avoiding
unnecessary pipeline work. A configurable threshold supports empirical tuning and reduces
unrelated matches.

**Alternatives considered**: Exact-string-only matching was rejected because the PRD requires
semantic matching. An in-memory-only cache was rejected because entries must survive restarts.
Using a below-threshold nearest match was rejected because it risks returning an unrelated
answer.

On a cache read failure, report that caching is temporarily unavailable and continue the
relevant request without a cache hit. If saving a completed supported answer fails, return the
answer and clearly report that it was not saved. Validate the threshold using representative
paraphrase and near-miss pairs; 0.90 is an initial value, not a calibrated guarantee.

## PDF ingestion and local index lifecycle

**Decision**: Extract all readable PDF pages, preserve filename and original page number on
every passage, and split text with the PRD's 1024-character size and 64-character overlap.
Generate query and document embeddings with the same local CPU embedding model. Persist the
FAISS index and reuse it while the source file, embedding model, and chunking settings are
unchanged. Store a manifest with the source fingerprint, embedding model identifier, and
chunking settings. Detect a mismatch and rebuild the index, validating the replacement before
switching from the previous index. Associate cached evidence with a cache-source fingerprint
derived from the PDF content fingerprint and embedding model identifier so a source update or
embedding-model change cannot silently reuse stale answers. Keep the existing root-level
`Rexroth IndraDrive.pdf` intact as the initial source.

**Rationale**: Page/source attribution is needed for evidence display and answer citations.
Index reuse avoids repeated parsing and embedding, while source-change detection prevents
stale retrieval results.

**Alternatives considered**: Rebuilding the index on every launch was rejected by the PRD.
Cloud embedding was rejected because embeddings must be local and CPU-based. Moving or
overwriting the supplied PDF was rejected to preserve user data.

## Model, integration, and failure handling

**Decision**: Use Groq GPT-OSS 120B for classification, expansion, and answer generation.
Run the specified sentence-transformer embedding model and cross-encoder locally on CPU.
Present safe, actionable errors for missing credentials, provider failures, malformed
classification, document/index/model errors, empty retrieval, and cache I/O failures. Never
render credentials or raw stack traces.

**Rationale**: These are fixed project requirements. Explicit failure states prevent an
infrastructure problem from becoming a plausible but unsupported technical answer.

**Alternatives considered**: Substituting models or silently falling back to mock answers was
rejected by the PRD and constitution. Exposing raw exceptions in the UI was rejected to protect
secrets and maintain a usable experience.

## Structured output and failure policy

**Decision**: Validate classifier and expansion outputs against their required structures. A
single bounded retry may be used for malformed model output; if classification remains invalid
or expansion does not yield exactly three alternatives, stop that route and show an explicit
error rather than silently substituting different behavior. Missing source/index or an
unavailable required broad-query reranker is a visible processing failure. An empty evidence
set produces an explicit abstention.

**Rationale**: Bounded retries can recover transient formatting errors without permitting
unbounded calls or changing routing requirements. Silent fallbacks could make diagnostics and
answer provenance misleading.

**Alternatives considered**: Silently using the original query after expansion failure,
continuing broad retrieval without required reranking, or fabricating an answer without
evidence were rejected.

## Observability and validation

**Decision**: Measure elapsed time for each stage that executes and total interaction time.
Report a cache hit as a distinct route, with only classification and cache lookup marked as
executed. Validate behavior using isolated unit tests, mocked provider interactions, and
end-to-end scenarios against the supplied guide and real provider configuration.

**Rationale**: Stage-level metrics and cache visibility are explicit product requirements.
Mocked unit tests remain deterministic; end-to-end checks validate document and service
integration without making every test depend on external availability.

**Alternatives considered**: Reporting only aggregate latency was rejected because it hides
which stage ran. Using live provider calls for all tests was rejected because failures and
latency would be nondeterministic.

Use labeled paraphrase and near-miss question pairs to evaluate the configurable cache
threshold. Do not invent a numeric retrieval-score sufficiency cutoff: calibrate any such
policy against the actual guide and a reviewed answer set.

## Unspecified operational targets

**Decision**: Measure and display latency but do not assign an unprovided latency SLA, user
concurrency limit, or corpus-size target.

**Rationale**: The PRD requests stage and total timings but provides no numeric performance
target or deployment scale.

**Alternatives considered**: Inventing service-level numbers would create unsupported
acceptance requirements. Product owners can add these targets through a future spec amendment.
