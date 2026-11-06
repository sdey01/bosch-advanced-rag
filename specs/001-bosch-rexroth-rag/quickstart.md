# Quickstart: Validation Guide

This guide validates the planned Bosch Rexroth Troubleshooting Assistant from a Windows
PowerShell session opened at the repository root.

## Prerequisites

- Python 3.12 is available through the Windows Python launcher (`py -3.12`).
- The supplied `Rexroth IndraDrive.pdf` is present at the repository root or the application
  is configured to use another readable Bosch Rexroth troubleshooting PDF.
- A valid Groq API key is available in the existing local environment configuration. Preserve
  any existing `.env` file; never paste or print its secret value.
- Internet access is available for Groq requests and initial local-model downloads. Embedding
  and reranking inference execute locally on CPU.

## Environment and launch

Create and populate the project virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ensure the local environment configuration contains the required Groq credential without
overwriting existing values. Configure the source PDF path and cache threshold if they differ
from their documented defaults. Launch the application:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Automated validation

Run unit and integration checks in the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected result: tests cover the three classification outcomes, exactly three relevant-query
alternatives, factual/broad limits, broad-only reranking, evidence-only answers, cache hit/miss
and persistence behavior, safe errors, and diagnostics. Unit tests use controlled provider
responses; integration tests that require Groq credentials or the supplied PDF identify those
prerequisites explicitly.

## End-to-end scenarios

1. **Factual answer**: Ask a specific question answerable from the guide. Confirm the answer
   displays source/page evidence, no more than two passages are used, and reranking is not
   shown as executed.
2. **Broad answer**: Ask a question requiring multiple guide sections. Confirm exactly three
   alternatives, no more than 20 candidates, visible reranking, and at most five answer
   passages by default.
3. **Insufficient evidence**: Ask for a fact absent from the source. Confirm the answer states
   the evidence is insufficient and the result is not added to the cache.
4. **Irrelevant question**: Ask an unrelated question. Confirm the out-of-scope response and
   that retrieval and cache insertion do not occur.
5. **Cache reuse**: Ask a supported question, then repeat it. Confirm the second interaction
   is labeled a hit, returns the saved answer, increments the hit count, and skips expansion,
   retrieval, reranking, and generation. Restart the application and confirm the entry and
   counters remain visible. Change or replace the source PDF and confirm stale-source entries
   are not reused.
6. **Failure behavior**: With a missing/invalid credential or unavailable source, confirm the
   UI displays a safe explanatory message without secrets, stack traces, or a cache entry.
   Simulate cache read/write failures and confirm the app reports the cache issue, proceeds
   uncached when possible, and does not claim a new answer was saved.

## Related design

- Data and lifecycle definitions: [data-model.md](./data-model.md)
- UI behavior: [contracts/user-interface.md](./contracts/user-interface.md)
- Research decisions: [research.md](./research.md)
