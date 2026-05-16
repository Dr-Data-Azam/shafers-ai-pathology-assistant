# Technical Design: Testing Framework

## Summary
Add a complete pytest suite that covers every application module using mocked LLM, FAISS,
and file-system dependencies. Existing test files for `config` and `llm_provider_manager`
are left untouched. The suite is wired to `pyproject.toml` so the `/test` command and plain
`pytest` both produce a coverage report and finish in under 30 seconds.

## Implementation Tasks
Tasks are ordered — complete them in sequence.

- [ ] Task 1: Add pytest and coverage config to pyproject.toml
      What: Enables `pytest` and `/test` to run the full suite with coverage out of the box.
      Where: `pyproject.toml` → `[tool.pytest.ini_options]`, `[tool.coverage.run]`,
             `[tool.coverage.report]`
      How: Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and
           `addopts = "-v --tb=short --cov=. --cov-report=term-missing"`.
           Add `[tool.coverage.run]` with `omit` covering `tests/*`, `vector_store_creator.py`,
           and `conftest.py`. Add `[tool.coverage.report]` with `fail_under = 75` and
           `exclude_lines` for `pragma: no cover`, `if __name__`, `raise NotImplementedError`.

- [ ] Task 2: Create tests/conftest.py with shared fixtures
      What: Provides reusable fixtures consumed by every test module; eliminates repetition.
      Where: `tests/conftest.py`
      How: Define `clear_config_cache` (autouse, function scope) that calls
           `get_config.cache_clear()` in setup and teardown. Define `set_api_keys` that
           monkeypatches `OPENAI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACEHUB_ACCESS_TOKEN`.
           Define `history_file(tmp_path)` returning a `Path` for a temp JSON file.
           Define `populated_history_file` building on `history_file` with 2 saved interactions.
           Define `mock_doc` as a `MagicMock` with `.page_content = "test content"` and
           `.metadata = {"page": 27}`. Define `mock_docs` as a list of 3 `mock_doc` instances.
           Define `mock_retriever` as a `MagicMock` whose `.invoke()` returns `mock_docs`.

- [ ] Task 3: Create tests/test_chat_history_manager.py
      What: Full CRUD coverage for the JSON-backed chat history module.
      Where: `tests/test_chat_history_manager.py`
      How: In each test, import `chat_history_manager` after monkeypatching `get_config` to
           return a config-like object whose `chat_history_path` points at `history_file`.
           Tests: `save_chat_history()` writes a valid JSON list; round-trip `save → load`
           preserves all fields; `load_chat_history()` returns `[]` when file absent;
           `clear_chat_history()` empties the file; `get_recent_history(limit=1)` returns one
           entry; `get_history_stats()` returns correct `total_questions` and `avg_response_time`
           on empty and populated history; saving 101 entries retains only the most recent 100.

- [ ] Task 4: Create tests/test_vector_store_creator.py
      What: Tests the one-time PDF→FAISS build pipeline with all external calls mocked.
      Where: `tests/test_vector_store_creator.py`
      How: Patch at module level: `vector_store_creator.HuggingFaceEmbeddings`,
           `vector_store_creator.DirectoryLoader`, `vector_store_creator.RecursiveCharacterTextSplitter`,
           `vector_store_creator.FAISS`. Reset `_embedding_model` global to `None` via
           `monkeypatch.setattr` before each test. Tests: `get_embedding_model()` constructs
           the mock once and caches it (second call returns same object without re-constructing);
           `load_pdf_files()` instantiates `DirectoryLoader` with the configured `data_path` and
           calls `.load()`; `create_chunks()` calls `split_documents()` on the mock splitter;
           `build_vector_store()` calls `FAISS.from_documents()` and `.save_local()`.

- [ ] Task 5: Create tests/test_vector_retriever.py
      What: Tests term expansion (pure logic), document processing, and retriever loading paths.
      Where: `tests/test_vector_retriever.py`
      How: `generate_related_terms(query)` — no mocks; assert it returns a non-empty list of
           strings for a real query like "cellulitis". `process_documents_for_context(mock_docs)`
           — assert the returned tuple is `(str, dict)` and that the page number in the sources
           dict equals `mock_doc.metadata["page"] + 1` (i.e., 28). `get_retriever()` — two
           paths: (a) when `os.path.exists` returns True for the pkl path, mock `pickle.load`
           and assert the cached retriever is returned; (b) when pkl absent, mock `FAISS.load_local`
           and `get_embedding_model` and assert a new retriever is built. Reset `_retriever`
           global to `None` via monkeypatch before each test.

- [ ] Task 6: Create tests/test_rag_system.py
      What: End-to-end tests for `ask_question()` and `get_system_info()` with all I/O mocked.
      Where: `tests/test_rag_system.py`
      How: Patch inside each test: `rag_system.load_llm`, `rag_system.get_retriever`,
           `rag_system.get_comprehensive_context`, `rag_system.save_chat_history`. For the LCEL
           chain (`llm | parser`), configure the mock LLM so that `mock_llm.__or__(mock_parser)`
           returns a mock chain whose `.invoke()` returns `"mock answer"`. Alternatively, patch
           `rag_system.StrOutputParser` and `rag_system.create_prompt`. Tests: `ask_question()`
           returns a `(str, dict)` tuple; stats dict contains keys `total_time`, `provider`,
           `pages_retrieved`, `docs_retrieved`; `save_chat_history` is called when
           `save_history=True` and not called when `save_history=False`; an exception inside
           `load_llm` propagates to the caller; `get_system_info()` returns a dict with
           `vector_db_exists` (bool) and `available_providers` (list).

- [ ] Task 7: Create tests/test_streamlit_app.py
      What: Tests non-rendering logic in streamlit_app.py with the Streamlit module mocked.
      Where: `tests/test_streamlit_app.py`
      How: Before importing `streamlit_app`, insert a `MagicMock()` for the `streamlit` module
           into `sys.modules["streamlit"]`. Back `st.session_state` with a plain dict accessed
           via `__getitem__`/`__setitem__`/`__contains__`. Import `streamlit_app` inside each
           test function. Tests: `initialize_session_state()` populates `chat_history`,
           `current_provider`, and `system_initialized` when session_state is empty;
           `check_system_status()` returns `True` when `get_system_info` returns
           `{"vector_db_exists": True, "available_providers": ["openai"]}`; returns `False`
           when `vector_db_exists` is `False`; `render_sidebar()` calls `get_history_stats()`
           exactly once.

- [ ] Task 8: Create tests/test_main_console.py
      What: Tests CLI functions with external dependencies and user input mocked.
      Where: `tests/test_main_console.py`
      How: Patch inside each test: `main_console.get_system_info`, `main_console.ask_question`,
           `main_console.get_available_providers`, `main_console.load_chat_history`. For
           `select_provider()` with a single provider in the list, assert it returns that
           provider without calling `input()`. For multiple providers, monkeypatch
           `builtins.input` to return `"1"` and assert the first provider is returned.
           `print_system_status()` returns `True` when `get_system_info` reports
           `{"vector_db_exists": True, "available_providers": ["openai"]}` and `False` when
           db is missing. `test_both_providers()` calls `ask_question` once per provider
           returned by `get_available_providers`.

## Files to Modify
| File | What Changes |
|------|-------------|
| `pyproject.toml` | Add `[tool.pytest.ini_options]`, `[tool.coverage.run]`, `[tool.coverage.report]` sections |

## Files to Create
| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared autouse and named fixtures for all test modules |
| `tests/test_chat_history_manager.py` | CRUD + cap tests for the JSON history module |
| `tests/test_vector_store_creator.py` | PDF→FAISS pipeline tests with all externals mocked |
| `tests/test_vector_retriever.py` | Term expansion, doc processing, and retriever load paths |
| `tests/test_rag_system.py` | `ask_question()` and `get_system_info()` end-to-end |
| `tests/test_streamlit_app.py` | Non-rendering Streamlit functions with mocked `st` |
| `tests/test_main_console.py` | CLI entry points with mocked `input()` and external calls |

## New Dependencies
None.

## Breaking Changes
None.

## Data Flow
Not applicable — this feature adds tests only and does not change application data flow.

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| `save_chat_history()` / `load_chat_history()` | Unit | monkeypatch `get_config` → `tmp_path` |
| `get_history_stats()` on empty/populated | Unit | monkeypatch `get_config` → `tmp_path` |
| 100-entry cap enforcement | Unit | monkeypatch `get_config` → `tmp_path` |
| `get_embedding_model()` caching | Unit | patch `HuggingFaceEmbeddings` constructor |
| `build_vector_store()` orchestration | Unit | patch FAISS, DirectoryLoader, splitter |
| `generate_related_terms()` | Unit | No mocks (pure function) |
| `process_documents_for_context()` | Unit | `mock_docs` fixture |
| `get_retriever()` — cache hit path | Unit | patch `pickle.load`, `os.path.exists` |
| `get_retriever()` — cache miss path | Unit | patch `FAISS.load_local`, `get_embedding_model` |
| `ask_question()` — happy path | Unit | patch `load_llm`, `get_retriever`, LCEL chain |
| `ask_question()` — save_history flag | Unit | assert `save_chat_history` call/no-call |
| `get_system_info()` | Unit | patch `os.path.exists`, `get_available_providers` |
| `initialize_session_state()` | Unit | mock `sys.modules["streamlit"]` |
| `check_system_status()` | Unit | mock `get_system_info` return value |
| `print_system_status()` | Unit | mock `get_system_info` return value |
| `test_both_providers()` | Unit | mock `ask_question`, `get_available_providers` |

Minimum coverage target: 75% on all new/modified code.
