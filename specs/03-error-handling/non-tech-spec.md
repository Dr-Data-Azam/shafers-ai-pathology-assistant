# Feature: Error Handling and Structured Logging

## Problem Statement
The application uses bare `try/except` blocks throughout its modules and writes error
information to stdout via `print()`. This makes it impossible to trace, filter, or
aggregate errors in production. For a healthcare application where error traceability
is critical, the lack of structured logging and typed exceptions means failures are
silent, undifferentiated, and unauditable — a serious gap when clinical decisions depend
on reliable software behaviour.

## User Story
As a developer or system operator, I want structured logs and typed exceptions so that
I can trace exactly what failed, why, and where — without digging through raw stdout.

## What It Should Do (Acceptance Criteria)
- When an LLM API call fails, the system raises an `LLMError` (not a bare `Exception`)
  containing the provider name, error type, and message — never an error string returned
  from a function
- When the FAISS retriever fails to load or search, the system raises a `RetrieverError`
  with context about the failure point
- When a required config value is missing or invalid at startup, the system raises a
  `ConfigError` before any LLM or retrieval call is attempted
- When any error occurs, a structured log entry is written via Python's `logging` module,
  including timestamp, module name, log level, and error message
- The logging system writes to both a rotating log file (`app.log`) and stderr — never
  to stdout
- The Streamlit UI catches typed exceptions and displays a user-friendly message matched
  to the error type (e.g., "The AI provider is unavailable — please try again." for
  `LLMError`; "Could not retrieve context from the textbook." for `RetrieverError`)
- The CLI catches typed exceptions and exits with a non-zero exit code and a
  human-readable error message on stderr
- All caught exceptions are logged before being re-raised or handled — nothing is
  swallowed silently

## What It Should NOT Do (Constraints)
- Must not change the `ask_question()` function signature or its return type for existing
  callers
- Must not log API keys, tokens, or any credentials — even partially
- Must not suppress or swallow exceptions without logging them first
- Must not change the temperature setting, retrieval parameters, or chunk sizes
- Must not break the existing test suite

## Files Likely Affected
- `exceptions.py` — new file; defines `LLMError`, `RetrieverError`, `ConfigError`
- `rag_system.py` — replace bare try/except with typed raises and structured logging
- `llm_provider_manager.py` — raise `LLMError` on API failures
- `vector_retriever.py` — raise `RetrieverError` on FAISS failures
- `config.py` — raise `ConfigError` on missing or invalid config values
- `streamlit_app.py` — catch typed exceptions and show user-friendly UI messages
- `main_console.py` — catch typed exceptions and exit with proper codes
- `chat_history_manager.py` — add logging for history read/write failures

## Open Questions
- Should the log file path (`app.log`) be configurable via `config.py` or hardcoded?
- Should the logging level be settable via an environment variable (e.g., `LOG_LEVEL=DEBUG`)?
- Should `LLMError` include the raw API response body, or only the error message, to
  avoid accidentally logging sensitive content?
