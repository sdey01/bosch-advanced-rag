# Bosch Rexroth Troubleshooting Assistant

Ask questions about the Bosch Rexroth troubleshooting guide and receive answers grounded in
the source document, with retrieval evidence and pipeline diagnostics.

## Requirements

- Windows with Python 3.12 available via the Python launcher.
- A Groq API key for GPT-OSS 120B.
- The source guide PDF. The default is `Rexroth IndraDrive.pdf` in the project root.
- Internet access for Groq requests and initial local model downloads. Embeddings and broad
  query reranking run locally on CPU.

## Setup

From the project root, create a virtual environment and install dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `GROQ_API_KEY` in the existing local `.env` file. Preserve existing `.env` values and
never commit or display credentials. `.env.example` lists supported setting names; copy
individual non-secret defaults only as needed rather than overwriting an existing `.env`.

The application settings include:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-oss-120b` | Groq model for classification, query expansion, and answers |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local CPU embeddings |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Local CPU ranking for broad questions |
| `PDF_PATH` | `Rexroth IndraDrive.pdf` | Source troubleshooting guide |
| `VECTOR_STORE_PATH` | `vector_store/faiss_index` | Persistent local retrieval index |
| `SEMANTIC_CACHE_PATH` | `cache/semantic_cache.db` | Persistent local answer cache |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1024` / `64` | Source passage sizing |
| `FACTUAL_TOP_K` / `BROAD_TOP_K` | `2` / `20` | Factual passages / broad candidates |
| `RERANK_TOP_K` | `5` | Broad answer context size after ranking |
| `QUERY_EXPANSION_COUNT` | `3` | Required number of alternative queries |
| `SEMANTIC_CACHE_THRESHOLD` | `0.90` | Initial semantic match threshold; validate with representative question pairs |

The local FAISS index is reused only while the PDF fingerprint, embedding model, and chunk
settings match its manifest. A changed source or setting triggers a rebuild. The persistent cache associates answers with a fingerprint of the PDF content and embedding
model, so entries grounded in an older source or a different embedding space are not reused.
Factual questions use no more than two passages and skip reranking; broad questions rank up to
20 candidates and use up to the configured final passage count.

## Run

Launch Streamlit from the project root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Test

Run unit and integration tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The supplied-PDF integration check is opt-in because it loads the local embedding model and
builds an index:

```powershell
$env:RUN_SUPPLIED_PDF_TEST = "1"
.\.venv\Scripts\python.exe -m pytest tests\integration\test_supplied_pdf.py
Remove-Item Env:\RUN_SUPPLIED_PDF_TEST
```

See [the feature quickstart](specs/001-bosch-rexroth-rag/quickstart.md) for detailed
end-to-end validation scenarios and expected behavior.
