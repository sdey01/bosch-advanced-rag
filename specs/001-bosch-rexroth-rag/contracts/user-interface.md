# User Interface Contract

## Purpose and scope

This is the user-facing contract for the local Bosch Rexroth Troubleshooting Assistant. The
feature does not define a separate public programmatic API.

## User input

- The user submits one natural-language question about the Bosch Rexroth troubleshooting guide.
- The exact submitted text is retained for answer generation and conversation history.
- The UI identifies the application as the Bosch Rexroth Troubleshooting Assistant.

## Processing outcomes

| Outcome | Required visible behavior |
|---|---|
| Irrelevant query | Show the out-of-scope category and a polite prompt to ask about the guide; do not show retrieval or cache insertion as having occurred. |
| Factual cache miss | Show the category, reasoning, selected route, three alternatives, up to two distinct retrieved passages, answer, and applicable source/page details. Show no reranking as executed. |
| Broad cache miss | Show the category, reasoning, selected route, three alternatives, up to 20 candidates, their available reranking order/scores, selected answer passages, and answer. |
| Cache hit | Show the cached answer and a clear cache-hit status; show similarity when available. Do not imply that expansion, retrieval, reranking, or new generation occurred. |
| Insufficient evidence | State that the guide does not provide sufficient evidence and do not present invented technical guidance as fact. Do not save the response as a reusable cache entry. |
| Cache read failure | Tell the user cache reuse is unavailable and continue the relevant question without a cache hit, if the rest of the pipeline can proceed. |
| Cache write failure | Return a supported answer if available and clearly indicate that the answer was not saved for reuse. |
| Expected operational failure | Show a meaningful, non-sensitive message. Do not expose credentials, sensitive configuration, or raw stack traces. |

## Diagnostics and history

- Show the exact question, predicted category, classifier reasoning, and processing route.
- On a relevant cache miss, display exactly three query alternatives.
- Display each visible source passage's text, source filename, page number when available, and
  relevance score when available.
- For broad queries, distinguish candidate passages, reranked order/scores, and passages used
  for answer generation.
- Show latency for each stage that ran and total response time. A skipped stage is not reported
  as executed.
- Keep distinguishable question/answer pairs available in session conversation history.

## Cache monitoring

Provide a cache panel showing total entries, hits, misses, hit ratio, visible entries with
query/category/time and expandable answer, and the latest interaction's hit/miss status. Show
the closest-match similarity and whether an entry was created or reused when those values are
available. Refresh the displayed cache state after each interaction; a manual refresh may be
provided.

## Layout

Present conversation history, the primary chat and pipeline details, and cache monitoring in a
desktop-usable layout. Empty history and empty cache states remain understandable and usable.
