# Technical Design: Error Handling and Structured Logging

## Summary
Adds a typed exception hierarchy (`LLMError`, `RetrieverError`, `ConfigError`) and
Python `logging` wired to a rotating file + stderr across all seven application modules.
Bare `try/except` blocks and `print()`-based error output are replaced with structured
log entries and typed raises, so that failures in a healthcare context are traceable,
filterable, and auditable without changing the public API of `ask_question()`.

---

## Implementation Tasks
Tasks are ordered — complete them in sequence.

- [ ] Task 1: Create `exceptions.py`
      What: Define the custom exception hierarchy for the entire app
      Where: `exceptions.py` (new file, project root)
      How: Create `PathologyAppError(Exception)` as the base. Subclass it with
      `LLMError(provider: str, message: str)`, `RetrieverError(message: str)`, and
      `ConfigError(message: str)`. Each stores its arguments as instance attributes.

- [ ] Task 2: Add logging fields and `configure_logging()` to `config.py`
      What: Make log level and log file path configurable; provide a setup function
      Where: `config.py` → `AppConfig` class + new `configure_logging()` function
      How: Add `log_level: str = "INFO"` and `log_file: str = "app.log"` fields to
      `AppConfig` (read from env vars `LOG_LEVEL`, `LOG_FILE`). Add
      `configure_logging(cfg: AppConfig) -> None` that attaches a
      `RotatingFileHandler` (10 MB, 3 backups) and a `StreamHandler(sys.stderr)` to
      the root logger with format:
      `"%(asctime)s | %(name)s | %(levelname)s | %(message)s"`.

- [ ] Task 3: Replace `ValueError` with `ConfigError` in `config.py` validator
      What: Make the API-key validator raise a typed exception
      Where: `config.py` → `require_at_least_one_llm_key()` model validator
      How: Import `ConfigError` from `exceptions.py`. Change `raise ValueError(...)` to
      `raise ConfigError(...)` with the same message.

- [ ] Task 4: Update `llm_provider_manager.py` — add logger and raise `LLMError`
      What: Replace bare `Exception` raises with `LLMError`; add structured logging
      Where: `llm_provider_manager.py` → `load_llm()` and `validate_provider()`
      How: Add `logger = logging.getLogger(__name__)`. In each `except` block that
      currently raises `Exception("Failed to load ...")`, log with `logger.error(...)`
      then raise `LLMError(provider=provider, message=str(e))`. Also raise `LLMError`
      (not bare `Exception`) from `validate_provider()` for invalid provider names.

- [ ] Task 5: Update `vector_retriever.py` — add logger and raise `RetrieverError`
      What: Replace `FileNotFoundError` and print-based errors with typed exception
      and structured logging
      Where: `vector_retriever.py` → `get_retriever()` and `get_comprehensive_context()`
      How: Add `logger = logging.getLogger(__name__)`. Replace the `FileNotFoundError`
      raise in `get_retriever()` with `RetrieverError`. Replace
      `print(f"Error searching for term ...")` with `logger.warning(...)`. Replace
      `print("Loading vector database...")` with `logger.info(...)`.

- [ ] Task 6: Update `chat_history_manager.py` — replace `print()` with `logger`
      What: Route all error output through the logging system
      Where: `chat_history_manager.py` → `save_chat_history()`, `load_chat_history()`,
      `clear_chat_history()`
      How: Add `logger = logging.getLogger(__name__)`. Replace each
      `print(f"Error ...")` call with `logger.error(...)`. Return behaviour (True/False)
      stays the same — history errors are non-fatal.

- [ ] Task 7: Update `rag_system.py` — propagate exceptions; add logging
      What: Stop catching and returning errors as strings; let typed exceptions surface
      Where: `rag_system.py` → `ask_question()`
      How: Add `logger = logging.getLogger(__name__)`. Remove the broad `try/except
      Exception` that wraps the function body and returns `f"Error: {str(e)}"`. Add
      `logger.info(...)` at question receipt and `logger.debug(...)` at retrieval and
      LLM steps. Individual modules already raise `LLMError` / `RetrieverError` —
      they propagate naturally. `ask_question()` signature and success return type
      are unchanged.

- [ ] Task 8: Update `streamlit_app.py` — typed exception handling + logging init
      What: Show user-friendly messages per exception type; initialise logging at startup
      Where: `streamlit_app.py` → module-level startup block + `render_main_chat()`
      How: Call `configure_logging(get_config())` once at module load. Replace the
      generic `except Exception as e: st.error(f"Error: {str(e)}")` with three typed
      clauses: `LLMError` → "The AI provider is unavailable — please try again or
      switch providers."; `RetrieverError` → "Could not retrieve context from the
      textbook — the vector database may need rebuilding."; `ConfigError` →
      "Configuration error — please check your .env file.". Log each at ERROR level
      before displaying.

- [ ] Task 9: Update `main_console.py` — typed exception handling + logging init + exit codes
      What: Show typed error messages; exit with non-zero codes on fatal errors
      Where: `main_console.py` → `main()`, `interactive_chat()`, `test_both_providers()`
      How: Call `configure_logging(get_config())` at the start of `main()`. Replace
      each generic `except Exception as e: print(f"Error: {str(e)}")` with typed
      clauses that log at ERROR level and print a user-friendly message. On `ConfigError`
      or `RetrieverError` in `main()`, call `sys.exit(1)`. In `interactive_chat()`,
      `LLMError` continues the loop (non-fatal); `RetrieverError` exits the loop.

- [ ] Task 10: Write `tests/test_exceptions.py`
      What: Unit-test the exception hierarchy
      Where: `tests/test_exceptions.py` (new file)
      How: Test that each class instantiates correctly, that attribute values are stored
      (e.g., `LLMError.provider`), that all three are subclasses of `PathologyAppError`,
      and that `PathologyAppError` is a subclass of `Exception`.

- [ ] Task 11: Update existing tests for the new exception types
      What: Fix tests that currently expect `ValueError` or bare `Exception`
      Where: `tests/test_config.py`, `tests/test_rag_system.py`,
      `tests/test_llm_provider_manager.py`
      How: In `test_config.py`, change `pytest.raises(ValueError)` to
      `pytest.raises(ConfigError)` in the API-key validation tests. In
      `test_rag_system.py`, update mock setup so `ask_question()` raises rather than
      returns an error string, and assert the right exception type is raised. In
      `test_llm_provider_manager.py`, assert `LLMError` (not bare `Exception`) is
      raised on provider load failure.

---

## Files to Create
| File | Purpose |
|------|---------|
| `exceptions.py` | Custom exception hierarchy: `PathologyAppError`, `LLMError`, `RetrieverError`, `ConfigError` |
| `tests/test_exceptions.py` | Unit tests for exception classes and hierarchy |

## Files to Modify
| File | What Changes |
|------|-------------|
| `config.py` | Add `log_level`, `log_file` fields; add `configure_logging()`; `ConfigError` in validator |
| `llm_provider_manager.py` | Module logger; raise `LLMError` instead of bare `Exception` |
| `vector_retriever.py` | Module logger; raise `RetrieverError`; replace `print()` error calls |
| `chat_history_manager.py` | Module logger; replace `print()` error calls with `logger.error()` |
| `rag_system.py` | Module logger; remove catch-and-return-string; let exceptions propagate |
| `streamlit_app.py` | Init logging at startup; typed `except` clauses with friendly messages |
| `main_console.py` | Init logging at startup; typed `except` clauses; `sys.exit(1)` on fatal errors |
| `tests/test_config.py` | `ConfigError` instead of `ValueError` in API-key validation tests |
| `tests/test_rag_system.py` | Assert exceptions propagate; not returned as strings |
| `tests/test_llm_provider_manager.py` | Assert `LLMError` raised on load failure |

## New Dependencies
None. Uses stdlib `logging` and `logging.handlers.RotatingFileHandler` only.

## Breaking Changes
| What Breaks | Impact | Migration |
|------------|--------|-----------|
| `ask_question()` raises on failure instead of returning `"Error: ..."` | Callers that check `if answer.startswith("Error")` will break | Both callers (`streamlit_app.py`, `main_console.py`) already use try/except — updated in Tasks 8 & 9 |
| `config.py` raises `ConfigError` instead of `ValueError` | Tests checking `pytest.raises(ValueError)` will fail | Updated in Task 11 |

## Data Flow
Error path (new):
`ask_question()` → module raises `LLMError` / `RetrieverError` / `ConfigError`
→ `logger.error(...)` in source module
→ exception propagates to caller (Streamlit or CLI)
→ caller catches typed exception, logs at ERROR, shows user-friendly message

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| Exception class hierarchy and attributes | Unit | No mocks needed |
| `configure_logging()` sets up handlers | Unit | Check root logger handlers after call |
| `ConfigError` raised on missing API keys | Unit | `monkeypatch.delenv` both key env vars; `get_config.cache_clear()` |
| `LLMError` raised when ChatOpenAI init fails | Unit | Patch `ChatOpenAI.__init__` to raise; assert `LLMError` |
| `RetrieverError` raised when FAISS db missing | Unit | Patch `os.path.exists` to return False |
| `ask_question()` propagates `LLMError` | Unit | Patch `load_llm` to raise `LLMError`; assert it propagates |
| Streamlit shows typed error message | Unit | Patch `ask_question` to raise; assert `st.error` called with friendly text |

Minimum coverage target: 80% on all new/modified code.
