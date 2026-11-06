# Feature Specification: Bosch Rexroth Troubleshooting Assistant

**Feature Branch**: `001-bosch-rexroth-rag`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "create specs md now", interpreted in the context of `PRD.md` as a request to create the product specification for the Bosch Rexroth troubleshooting assistant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a Document-Supported Troubleshooting Answer (Priority: P1)

A technician or other guide user asks a question about the Bosch Rexroth troubleshooting guide and receives a clear answer supported by relevant passages from that guide. If the guide does not provide enough evidence, the response says so rather than guessing. A question outside the guide's scope receives a polite explanation.

**Why this priority**: Reliable, source-grounded answers are the central user benefit.

**Independent Test**: Ask a direct question with an answer in the guide, a multi-part troubleshooting question, an unanswerable question, and an unrelated question. Verify answers cite available source pages, unsupported answers do not invent facts, and unrelated questions are identified as outside scope.

**Acceptance Scenarios**:

1. **Given** a question about a specific fact covered by the guide, **When** the user submits it, **Then** the assistant returns a concise answer supported by up to two relevant source passages and shows their source and page details when available.
2. **Given** a question requiring information from multiple parts of the guide, **When** the user submits it, **Then** the assistant considers a broader set of candidate passages, prioritizes the most relevant passages, and answers using the original question and selected evidence.
3. **Given** the guide contains no sufficient evidence for a question, **When** the user submits it, **Then** the assistant clearly states that it cannot answer from the available guide and does not invent a procedure, specification, or error-code meaning.
4. **Given** a question unrelated to the guide, **When** the user submits it, **Then** the assistant explains that the question is outside scope and does not search the guide or save the question as a reusable answer.

---

### User Story 2 - Reuse Answers for Similar Questions (Priority: P2)

A user asks a question that has already been answered, or asks a sufficiently similar question, and can receive the earlier supported response without waiting for the full answer process to run again. Users can inspect the cache's contents and activity.

**Why this priority**: Reusing successful answers reduces repeated work while preserving a responsive experience and allowing users to see when reuse occurs.

**Independent Test**: Ask a supported question, then repeat it and ask a semantically similar question. Verify qualifying matches return the saved answer, update hit statistics, and skip further expansion, retrieval, ranking, and answer generation. Verify a clearly different question is a miss and an unsuccessful answer is not saved.

**Acceptance Scenarios**:

1. **Given** a relevant question with no qualifying prior match, **When** the assistant completes a supported answer, **Then** it records the question, answer, category, timestamp, and available evidence metadata for later reuse.
2. **Given** a relevant question with a sufficiently similar saved entry, **When** the user submits it, **Then** the assistant returns the saved answer, marks the interaction as a cache hit, and updates the hit count.
3. **Given** a relevant question with no sufficiently similar saved entry, **When** the user submits it, **Then** the assistant marks a cache miss and proceeds to answer it from the guide.
4. **Given** the application is restarted, **When** a user opens cache monitoring, **Then** previously saved entries and cumulative hit/miss counts remain available.

---

### User Story 3 - Inspect the Answer Process (Priority: P3)

A user reviews the current interaction and prior conversation to understand how the answer was produced, which guide passages were considered, and whether a cached response was reused.

**Why this priority**: Inspectable evidence and diagnostics help users assess the answer and make the system's behavior understandable.

**Independent Test**: Submit factual, broad, irrelevant, cache-hit, and cache-miss questions. Verify conversation history and the applicable classification, route, expansions, evidence, ranking, cache activity, and latency details appear for each interaction.

**Acceptance Scenarios**:

1. **Given** a newly submitted question, **When** the assistant processes it, **Then** the interface shows the exact question, predicted category, reason, and selected route.
2. **Given** a relevant cache miss, **When** processing completes, **Then** the interface shows exactly three query alternatives, retrieved passages and available source/page/relevance details, plus ranking details when applicable.
3. **Given** any processed interaction, **When** the user inspects diagnostics, **Then** the interface shows measured latency for applicable processing stages and the total response time.
4. **Given** the user has asked multiple questions in the current session, **When** they inspect conversation history, **Then** each question and its corresponding answer can be distinguished and reviewed.
5. **Given** cache entries exist, **When** the user views cache monitoring, **Then** they can inspect entry queries, expandable answers, categories, timestamps, total entries, hit/miss counts, hit ratio, and recent cache activity.

### Edge Cases

- The source guide is missing, unreadable, or contains no extractable text.
- A query classifier returns malformed or unexpected content, or a language-model request fails, times out, or is rate limited.
- Query expansion fails or returns a number of alternatives other than three.
- No relevant passages are found, or fewer than the requested number of passages are available.
- A saved answer is only moderately similar to a new question and falls below the configured matching threshold.
- A cache read or write fails; the user must receive a meaningful error and a failed or unsupported response must not be stored.
- A local retrieval index is unavailable or cannot be refreshed after the source guide changes.
- A cache hit must not be presented as if new retrieval or answer generation occurred.
- A source page reference is unavailable; the answer may omit the page reference but must still identify available source information.
- Cache entries or conversation history are empty, and the dashboard must still render usefully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to submit natural-language questions about the Bosch Rexroth troubleshooting guide.
- **FR-002**: The assistant MUST classify each submitted question as exactly one of `FACTUAL`, `BROAD`, or `IRRELEVANT`, and make its category and reasoning visible.
- **FR-003**: The assistant MUST identify an `IRRELEVANT` question as outside the guide's scope without performing guide retrieval or saving it as a reusable answer.
- **FR-004**: For each relevant cache-miss question, the assistant MUST generate exactly three alternative formulations that preserve the original question's intent. Retrieval MUST consider those alternatives together with the original question.
- **FR-005**: For a `FACTUAL` question, the assistant MUST use no more than two distinct source passages in its answer context and MUST NOT apply broad-query reranking.
- **FR-006**: For a `BROAD` question, the assistant MUST consider up to 20 candidate passages, rank them by relevance to the original question, and use up to five top-ranked passages by default. The final passage count MUST be configurable.
- **FR-007**: Answers MUST be generated in response to the original question and MUST rely only on evidence from the guide. The assistant MUST explain when evidence is insufficient and MUST NOT invent technical guidance.
- **FR-008**: Answers MUST preserve relevant technical terminology and include source page references whenever available. The interface MUST show the source passage, source filename, page number, and retrieval relevance information when available.
- **FR-009**: The assistant MUST check the cache for relevant questions before generating alternatives or retrieving passages. A qualifying cache hit MUST return the saved answer and skip expansion, retrieval, ranking, and new answer generation.
- **FR-010**: Cache matching MUST use a configurable similarity threshold and MUST NOT return a saved answer below that threshold. The cache MUST only match questions within the guide's subject domain.
- **FR-011**: The cache MUST store only successful answers supported by sufficient guide evidence. Each entry MUST retain the original question, answer, question category, creation time, and available evidence metadata.
- **FR-012**: The cache MUST persist between application restarts and support adding and viewing entries, hit/miss counters, hit ratio, and visibility of cache activity after each interaction.
- **FR-013**: The interface MUST provide a central question-and-answer experience, session conversation history, and a cache-monitoring area usable on standard desktop screens.
- **FR-014**: For each interaction, the interface MUST show the original question, category, reasoning, selected route, relevant alternatives, retrieved passages, applicable ranking details, cache outcome, and total response time. It MUST show stage-specific latency for the stages that ran.
- **FR-015**: The application MUST provide clear user-facing messages for missing or invalid service credentials, service failures, malformed classification, expansion failure, source-document errors, index or model loading failures, empty retrieval, and cache read/write failures.
- **FR-016**: User-facing errors MUST NOT reveal credentials, sensitive configuration values, or raw stack traces.
- **FR-017**: The source document's filename and original page metadata MUST remain associated with each passage shown as evidence.
- **FR-018**: The application MUST reuse its persistent retrieval index when the source document is unchanged and provide a way to rebuild it when the source document changes.
- **FR-019**: Users MUST be able to inspect previous questions and corresponding answers for the duration of the application session.
- **FR-020**: The cache display MUST distinguish an entry reused from a newly created entry and show the closest-match score when available.

### Key Entities

- **Guide**: The Bosch Rexroth troubleshooting source document and its filename, pages, and update state.
- **Source Passage**: A portion of the guide with its text, source filename, page reference, and retrieval or ranking relevance details when available.
- **Question**: A user's submitted text, its classification and reasoning, and any intent-preserving alternative formulations.
- **Answer**: The response to the original question, its supporting passages, and whether it is supported, insufficiently supported, or reused from cache.
- **Cache Entry**: A reusable supported question-and-answer record with category, creation time, evidence metadata, and similarity match information.
- **Interaction Diagnostics**: The route taken, applicable processing-stage durations, cache outcome, and total elapsed response time for one question.
- **Conversation Item**: A question and its corresponding answer retained for the current application session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a representative test set containing all three question categories, 100% of submitted questions are assigned one of the defined categories and the result is visible to the user.
- **SC-002**: For every relevant cache miss, exactly three intent-preserving alternatives are displayed; irrelevant questions produce zero alternatives and zero guide-retrieval attempts.
- **SC-003**: 100% of factual-query test responses use no more than two distinct source passages, and broad-query tests consider no more than 20 candidates and use no more than the default five ranked passages.
- **SC-004**: In tests with sufficient source evidence, every technical answer is supported by displayed guide evidence and includes a page reference whenever the source page is available; in tests without sufficient evidence, zero unsupported procedures, specifications, or error-code meanings are asserted.
- **SC-005**: 100% of qualifying cache-hit test interactions return the saved answer, update hit statistics, and perform no expansion, retrieval, ranking, or new answer generation.
- **SC-006**: After a restart, 100% of entries and hit/miss counts recorded before shutdown remain available.
- **SC-007**: For 100% of tested interactions, total latency is displayed; latency for every stage that ran is also displayed, and stages skipped on cache hits are not represented as executed.
- **SC-008**: A user can submit a question, identify the resulting answer and evidence, and review prior question-answer pairs in one desktop session without encountering an unhandled expected failure.

## Assumptions

- The product answers questions only about the Bosch Rexroth troubleshooting guide supplied for the application; general-purpose assistance is out of scope.
- The guide is available as a readable PDF, and its content is the authoritative source for technical answers.
- The interface and source guide are primarily used in English.
- Conversation history is retained for the current application session; cache entries and aggregate cache statistics persist across application restarts.
- Cache similarity threshold and final broad-answer passage count are configurable; broad-answer passage count defaults to five.
- A missing or unreadable guide, unavailable model service, or empty evidence set is reported to the user rather than treated as a successful answer.
- Service credentials are supplied through the existing local environment configuration, which the application must preserve.
- Product and validation requirements are derived from `PRD.md`; details that do not affect user-visible behavior remain implementation choices for the planning phase.
