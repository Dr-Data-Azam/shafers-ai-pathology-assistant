# Feature: Configuration Refactor

## Problem Statement
Configuration values — file paths (e.g. `vectorDB/my_FAISS_db`), model parameters
(e.g. `temperature=0.3`, `max_tokens=1500`), and retrieval settings (e.g. `k=12`,
`lambda_mult=0.7`, chunk size/overlap) — are hardcoded at the point of use across
multiple source files. This makes the application fragile: changing one value requires
hunting across modules, and deploying to a different environment (e.g. different vector
DB path or a different model) requires code edits rather than environment-variable changes.

## User Story
As a developer running the Shafer's AI Pathology Assistant, I want all configuration
in one place so that I can change paths, model parameters, or retrieval settings by
editing `.env` (or environment variables) without touching source code.

## What It Should Do (Acceptance Criteria)
- When the application starts, it reads all configuration values from a single
  `config.py` module that uses Pydantic Settings.
- When a required value (e.g. `OPENAI_API_KEY`) is missing from the environment,
  the app exits on startup with a clear validation error naming the missing field —
  before any LLM or retrieval call is attempted.
- When all required values are present, the app starts normally and behaves identically
  to before the refactor (same answers, same retrieval, same history).
- When a value is not set in `.env`, the system uses the documented default (e.g.
  `temperature=0.3`, `k=12`) so the app works out of the box with only the API keys set.
- When a developer wants to override a setting (e.g. change the vector DB path), they
  set the corresponding environment variable and restart; no code change is needed.
- All modules that previously hardcoded a value import it from `config.py` instead —
  there are no remaining hardcoded literals for paths, model params, or retrieval params.

## What It Should NOT Do (Constraints)
- Must not change any externally observable behavior: answers, retrieval results, chat
  history format, and UI layout must remain identical to before the refactor.
- Must not modify or overwrite `.env` or `.env.example`.
- Must not delete or regenerate the `vectorDB/` directory or its contents.
- Must not change the `temperature` value from `0.3` (it becomes the default in config,
  not a new value).
- Must not require any new required environment variables beyond those already listed in
  `.env.example` (`OPENAI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACEHUB_ACCESS_TOKEN`).
- Must not introduce classes or object-oriented patterns into modules that are currently
  functional — only `config.py` may use a Pydantic `BaseSettings` model.

## Files Likely Affected
- `config.py` — new file; defines the Pydantic Settings model with all config fields and defaults
- `llm_provider_manager.py` — replace hardcoded `temperature`, `max_tokens`, and model name literals with imports from `config.py`
- `vector_retriever.py` — replace hardcoded `k=12`, `lambda_mult=0.7`, and DB path with imports from `config.py`
- `vector_store_creator.py` — replace hardcoded chunk size, overlap, and output path with imports from `config.py`
- `rag_system.py` — replace any hardcoded paths or prompt-related parameters with imports from `config.py`
- `streamlit_app.py` — replace any hardcoded config references with imports from `config.py`
- `main_console.py` — replace any hardcoded config references with imports from `config.py`

## Open Questions
- None identified. All values to centralize are already known from the codebase.
