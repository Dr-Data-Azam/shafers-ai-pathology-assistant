# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-based Q&A system for Shafer's Textbook of Oral Pathology (7th Edition). Answers oral pathology questions using semantic retrieval over the textbook + LLM generation. Supports OpenAI GPT-4o and Groq Llama 3.1 as interchangeable providers.

## Setup & Running

**Prerequisites**: Python 3.13, uv package manager, `.env` with API keys (see `.env.example`)

```bash
# Install dependencies (use uv, not pip directly)
uv sync

# One-time: build vector database from PDF
# Place Shafer's PDF in data/ directory first
python vector_store_creator.py

# Run web UI
streamlit run streamlit_app.py

# Run CLI
python main_console.py

# Test both providers
python main_console.py test
```

**Environment variables required**: `OPENAI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACEHUB_ACCESS_TOKEN`

## Architecture

Seven modules, functional style (no classes), global instance caching:

```
streamlit_app.py        ← Web UI (main entry point)
main_console.py         ← CLI alternative
rag_system.py           ← Core RAG orchestration; ask_question() is the primary API
llm_provider_manager.py ← OpenAI/Groq abstraction with lazy-initialized globals
vector_retriever.py     ← FAISS retriever with MMR search + query expansion
vector_store_creator.py ← One-time PDF → FAISS pipeline
chat_history_manager.py ← JSON-backed persistent history (last 100 interactions)
```

**Data flow**: PDF → `vector_store_creator.py` → `vectorDB/my_FAISS_db` → `vector_retriever.py` (MMR, k=12, query expansion) → `rag_system.py` (adaptive prompt + LLM) → `chat_history_manager.py`

**Key paths (hardcoded)**:
- `vectorDB/my_FAISS_db` — FAISS index (git-ignored)
- `vectorDB/retriever.pkl` — cached retriever
- `data/` — source PDFs (git-ignored)
- `chat_history.json` — interaction log (git-ignored)

## LLM Providers

`llm_provider_manager.py` holds module-level globals `_llm_openai` and `_llm_groq` initialized on first call to `load_llm()`. Temperature is fixed at 0.3. Both providers share the same retriever and prompt logic in `rag_system.py`.

## Vector Retrieval

`vector_retriever.py` uses FAISS with MMR (`lambda_mult=0.7` for diversity) and auto-generates related search terms via `generate_related_terms()` before retrieval. Retrieved docs are grouped by source page before being passed as context.

## No Tests or CI

There is no test suite. Manual testing: `python main_console.py test` runs a sample question against both providers.
