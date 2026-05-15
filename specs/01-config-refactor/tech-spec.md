# Technical Design: Config Refactor

## Summary
A new `config.py` module introduces a Pydantic Settings `AppConfig` class that loads all
configuration — paths, model parameters, and retrieval settings — from `.env` with sensible
defaults. Every module that previously hardcoded a value is updated to call `get_config()` instead.
No function signatures or external behaviors change; the refactor is purely internal plumbing.

## Implementation Tasks

- [x] Task 1: Add pydantic-settings dependency
      What: Add `pydantic-settings>=2.0` to `pyproject.toml` and run `uv sync`
      Where: `pyproject.toml` → `[project].dependencies`
      How: Append the dependency string to the list. Run `uv sync` to install.

- [x] Task 2: Create config.py
      What: Define `AppConfig(BaseSettings)` with all 16 config fields and `get_config()` accessor
      Where: `config.py` (new file, project root)
      How: Declare all API keys as `Optional[str] = None`. Declare all other fields with
      their current hardcoded values as defaults (e.g. `temperature: float = 0.3`,
      `retriever_k: int = 12`). Add a `@model_validator(mode="after")` that raises
      `ValueError("At least one of OPENAI_API_KEY or GROQ_API_KEY must be set")` if both
      are None. Decorate `get_config()` with `@lru_cache(maxsize=1)`.

- [x] Task 3: Update vector_store_creator.py
      What: Replace module-level constants and hardcoded literals with config values;
      refactor `embedding_model` to a lazy `get_embedding_model()` function
      Where: `vector_store_creator.py` → `load_pdf_files()`, `create_chunks()`, `build_vector_store()`,
      and the new `get_embedding_model()` function
      How: Remove `DATA_PATH`, `DB_PATH` constants. Move `embedding_model` to a
      `_embedding_model = None` global + `get_embedding_model()` function that lazy-inits it
      using `get_config().embedding_model`. Replace all literal usages with `get_config()` calls.

- [x] Task 4: Update vector_retriever.py
      What: Replace module-level `DB_PATH`/`RETRIEVER_PATH` constants and retrieval params with
      config; switch embedding import from variable to function call
      Where: `vector_retriever.py` → `get_retriever()`, `get_comprehensive_context()`
      How: Remove `DB_PATH`, `RETRIEVER_PATH` constants. Change
      `from vector_store_creator import embedding_model` to
      `from vector_store_creator import get_embedding_model`. Replace `embedding_model` usage
      in `FAISS.load_local(...)` with `get_embedding_model()`. Replace `k=12`, `fetch_k=25`,
      `lambda_mult=0.7`, and `len(all_docs) < 20` with `get_config()` calls.

- [x] Task 5: Update llm_provider_manager.py
      What: Replace model name strings, temperature, max_tokens, and timeout literals
      Where: `llm_provider_manager.py` → `load_llm()`
      How: Call `get_config()` at the top of `load_llm()` and read
      `cfg.openai_model`, `cfg.groq_model`, `cfg.temperature`, `cfg.max_tokens`, `cfg.llm_timeout`.
      Replace all four literals in both the OpenAI and Groq branches.

- [x] Task 6: Update rag_system.py
      What: Replace three path literals in `get_system_info()` with config values
      Where: `rag_system.py` → `get_system_info()`
      How: Import `get_config` and replace `"vectorDB/my_FAISS_db"`, `"vectorDB/retriever.pkl"`,
      and `"chat_history.json"` with `cfg.db_path`, `cfg.retriever_path`, `cfg.chat_history_path`.

- [x] Task 7: Update chat_history_manager.py
      What: Replace module-level `CHAT_HISTORY_PATH` constant with config value
      Where: `chat_history_manager.py` → `save_chat_history()`, `load_chat_history()`,
      `clear_chat_history()`
      How: Remove `CHAT_HISTORY_PATH = "chat_history.json"`. In each function that references
      it, call `get_config().chat_history_path` instead.

- [x] Task 8: Write tests/test_config.py
      What: Unit tests for config loading, defaults, validation, and env var override
      Where: `tests/test_config.py` (new file)
      How: Use `monkeypatch.setenv` + `AppConfig(_env_file=None)` to bypass the real `.env`.
      Clear `get_config` lru_cache between tests. 5 test cases: defaults, missing both keys
      raises ValidationError, only-OpenAI works, only-Groq works, env var override works.

## Files to Modify
| File | What Changes |
|------|-------------|
| `pyproject.toml` | Added `pydantic-settings>=2.0`; `pytest>=9.0.3` as dev dep |
| `vector_store_creator.py` | Removed `DATA_PATH`/`DB_PATH` constants; `embedding_model` → `get_embedding_model()`; `get_config()` for chunk params and paths |
| `vector_retriever.py` | Removed `DB_PATH`/`RETRIEVER_PATH` constants; `get_embedding_model()` call; `get_config()` for retrieval params |
| `llm_provider_manager.py` | `get_config()` for model names, temperature, max_tokens, timeout in `load_llm()` |
| `rag_system.py` | `get_config()` for three path checks in `get_system_info()` |
| `chat_history_manager.py` | Removed `CHAT_HISTORY_PATH`; `get_config().chat_history_path` inside each function |

## Files Created
| File | Purpose |
|------|---------|
| `config.py` | Pydantic Settings model; single source of truth for all config |
| `tests/test_config.py` | 5 pytest unit tests for config loading and validation |

## New Dependencies
| Package | Version | Why Needed |
|---------|---------|------------|
| `pydantic-settings` | `>=2.0` | `BaseSettings` for env-file loading — separate package from pydantic v2 |

## Breaking Changes
None. All function signatures are unchanged. The `embedding_model` module-level variable in
`vector_store_creator.py` is replaced by `get_embedding_model()` — the only internal caller
(`vector_retriever.py`) is updated in Task 4.

## Data Flow
No change to the data flow. Config values are now read once (lazily, on first `get_config()`
call) and cached for the process lifetime via `@lru_cache`. All modules receive the same
`AppConfig` instance.

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| All defaults are applied correctly | Unit | `AppConfig(_env_file=None)` + `monkeypatch.setenv` for API keys |
| Missing both LLM keys raises `ValidationError` | Unit | `AppConfig(_env_file=None)` with no LLM keys in env |
| Only `OPENAI_API_KEY` set — loads successfully | Unit | `AppConfig(_env_file=None)` + `monkeypatch.setenv` |
| Only `GROQ_API_KEY` set — loads successfully | Unit | `AppConfig(_env_file=None)` + `monkeypatch.setenv` |
| Env var `RETRIEVER_K` overrides default | Unit | `AppConfig(_env_file=None)` + `monkeypatch.setenv("RETRIEVER_K", "8")` |

Minimum coverage target: 80% on `config.py`. Achieved: 100% (all branches exercised).
