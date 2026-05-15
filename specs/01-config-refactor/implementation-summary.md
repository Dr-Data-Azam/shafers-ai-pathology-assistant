# Implementation Summary: Config Refactor

**Branch:** `feature/config-refactor`
**Status:** Complete — all 8 tasks done, 5/5 tests passing

---

## What Was Built

A single `config.py` module now owns every configuration value in the app. All previously
hardcoded literals — file paths, model names, temperature, retrieval parameters, chunk sizes —
are declared once in `AppConfig` with documented defaults and loaded from `.env` at startup.

---

## Files Changed

| File | Change |
|------|--------|
| `config.py` | **Created.** `AppConfig(BaseSettings)` with 16 fields; `get_config()` cached via `@lru_cache` |
| `pyproject.toml` | Added `pydantic-settings>=2.0`; `pytest>=9.0.3` as dev dependency |
| `vector_store_creator.py` | Removed `DATA_PATH`/`DB_PATH` constants; `embedding_model` global refactored to lazy `get_embedding_model()` |
| `vector_retriever.py` | Removed `DB_PATH`/`RETRIEVER_PATH` constants; all retrieval params (`k`, `fetch_k`, `lambda_mult`, `max_context_docs`) from config |
| `llm_provider_manager.py` | Model names, `temperature`, `max_tokens`, `timeout` in `load_llm()` from config |
| `rag_system.py` | Three path literals in `get_system_info()` replaced with config values |
| `chat_history_manager.py` | `CHAT_HISTORY_PATH` constant removed; each function reads `get_config().chat_history_path` |
| `tests/test_config.py` | **Created.** 5 unit tests — defaults, validation, single-key variants, env override |

---

## Config Fields Reference

| Field | Default | Env Var Override |
|-------|---------|-----------------|
| `db_path` | `vectorDB/my_FAISS_db` | `DB_PATH` |
| `retriever_path` | `vectorDB/retriever.pkl` | `RETRIEVER_PATH` |
| `data_path` | `data/` | `DATA_PATH` |
| `chat_history_path` | `chat_history.json` | `CHAT_HISTORY_PATH` |
| `embedding_model` | `sentence-transformers/all-MiniLM-L6-v2` | `EMBEDDING_MODEL` |
| `openai_model` | `gpt-4o` | `OPENAI_MODEL` |
| `groq_model` | `llama-3.1-8b-instant` | `GROQ_MODEL` |
| `temperature` | `0.3` | `TEMPERATURE` |
| `max_tokens` | `1500` | `MAX_TOKENS` |
| `llm_timeout` | `60` | `LLM_TIMEOUT` |
| `retriever_k` | `12` | `RETRIEVER_K` |
| `retriever_fetch_k` | `25` | `RETRIEVER_FETCH_K` |
| `retriever_lambda_mult` | `0.7` | `RETRIEVER_LAMBDA_MULT` |
| `max_context_docs` | `20` | `MAX_CONTEXT_DOCS` |
| `chunk_size` | `500` | `CHUNK_SIZE` |
| `chunk_overlap` | `50` | `CHUNK_OVERLAP` |

API keys (`OPENAI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACEHUB_ACCESS_TOKEN`) are also read
from `.env`. At least one LLM key must be set or the app fails on startup with a clear error.

---

## Key Design Decisions

- **All API keys are `Optional[str] = None`** — preserves the existing "at least one key"
  behavior; a model validator raises `ValidationError` if neither LLM key is set.
- **`get_config()` uses `@lru_cache`** — consistent with the codebase's lazy singleton pattern
  (`_llm_openai`, `_llm_groq`, `_retriever`). Cleared via `get_config.cache_clear()` in tests.
- **`embedding_model` moved to `get_embedding_model()`** — the only external caller
  (`vector_retriever.py`) is updated. No public API changes.
- **No module-level `get_config()` calls** — all calls are inside functions, keeping modules
  individually testable without touching the real `.env`.

---

## Behavior Unchanged

- App answers, retrieval results, chat history format, and UI layout are identical.
- No new required env vars. All three existing keys remain optional-individually,
  with the same "at least one LLM key" rule as before.
- Temperature stays at `0.3` (now the default in config, not a new value).

---

## Test Results

```
tests/test_config.py::test_defaults_applied_with_both_keys   PASSED
tests/test_config.py::test_missing_both_llm_keys_raises      PASSED
tests/test_config.py::test_only_openai_key_is_sufficient      PASSED
tests/test_config.py::test_only_groq_key_is_sufficient        PASSED
tests/test_config.py::test_env_var_overrides_default          PASSED

5 passed in 0.14s
```
