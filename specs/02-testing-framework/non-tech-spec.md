# Feature: Testing Framework

## Problem Statement
The project currently has no automated test suite — only a manual `python main_console.py test`
command that hits real APIs. There is no way to verify that individual modules work correctly in
isolation, no coverage measurement, and no safety net against regressions when code changes. This
makes development risky and leaves the `/test` command without a meaningful suite to run.

## User Story
As a developer, I want a complete pytest test suite with mocked dependencies and coverage
reporting so that I can confidently make changes and verify correctness without calling real APIs
or rebuilding the FAISS index.

## What It Should Do (Acceptance Criteria)
- When `pytest` is run (or `/test` is invoked), all tests complete in under 30 seconds
- When any module under test makes an LLM call (OpenAI or Groq), the call is intercepted by a
  mock — no real API is contacted
- When any module under test accesses FAISS, the access is intercepted by a mock — no real index
  file is required on disk
- The test suite includes at least one test file per module: `rag_system`,
  `llm_provider_manager`, `vector_retriever`, `vector_store_creator`, `chat_history_manager`,
  `streamlit_app`, and `main_console`
- A `tests/conftest.py` exists and provides shared fixtures (e.g., mock LLM, mock retriever,
  temp chat history file, patched environment variables)
- When `pytest --cov` is run, a coverage report is produced showing per-module line coverage
- When a test fails, the output clearly identifies which module and which behavior failed
- When the `/test` command is invoked in Claude Code, it runs the full suite and reports
  pass/fail counts with a coverage summary

## What It Should NOT Do (Constraints)
- Must not contact any real external API (OpenAI, Groq, HuggingFace) during test runs
- Must not require `vectorDB/my_FAISS_db` or the source PDF to exist on disk
- Must not modify or overwrite `.env`
- Must not change the behavior of any existing production module
- Must not add test-only imports or test scaffolding into production source files

## Files Likely Affected
- `tests/conftest.py` — new: shared fixtures for mocking LLM, FAISS, and environment variables
- `tests/test_rag_system.py` — new: unit tests for `ask_question()` and RAG orchestration
- `tests/test_llm_provider_manager.py` — new: unit tests for provider loading and LLM abstraction
- `tests/test_vector_retriever.py` — new: unit tests for FAISS retrieval and query expansion
- `tests/test_vector_store_creator.py` — new: unit tests for the PDF-to-FAISS pipeline
- `tests/test_chat_history_manager.py` — new: unit tests for JSON-backed history and stats
- `tests/test_streamlit_app.py` — new: unit tests for UI logic with mocked Streamlit session state
- `tests/test_main_console.py` — new: unit tests for CLI entry points
- `pyproject.toml` — updated: add pytest and coverage configuration (tool.pytest.ini_options, tool.coverage)

## Open Questions
- None.
