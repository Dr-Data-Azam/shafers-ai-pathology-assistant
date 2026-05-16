# Code Review: Testing Framework
Date:     2026-05-15
Branch:   feature/testing-framework
Reviewer: code-reviewer agent

CODE REVIEW — Testing Framework
Branch: feature/testing-framework
Spec:   specs/02-testing-framework/tech-spec.md
Files:  8 changed (pyproject.toml modified; 7 test files created)

VERDICT: APPROVED WITH COMMENTS

---
ISSUES
------

[SHOULD FIX] tests/test_vector_retriever.py, tests/test_chat_history_manager.py,
             tests/test_rag_system.py, tests/test_streamlit_app.py,
             tests/test_main_console.py, tests/test_vector_store_creator.py
What: Six files fail `black --check --target-version py313`. The specific violations
      are long `patch(...)` call chains that exceed the 88-character line limit (most
      visibly the `side_effect=lambda` lines in test_vector_retriever.py). Black would
      wrap these into the multi-line form.
Why:  CLAUDE.md requires Black + Ruff to pass before every commit. The `/ship-feature`
      command runs lint as a gate; these files will block the ship step.
Fix:  Run `/fix` (or `python -m black --target-version py313 tests/`) to auto-format
      all six files in one step.

[SHOULD FIX] tests/test_vector_retriever.py:1, tests/test_vector_store_creator.py:2,
             tests/test_chat_history_manager.py:2, tests/test_rag_system.py:1,
             tests/test_main_console.py:1-2
What: Ruff reports 6 unused-import (F401) violations:
      - `import pickle` in test_vector_retriever.py (pickle is patched as a string, not
        used as an object)
      - `import call` from unittest.mock in test_vector_store_creator.py
      - `import pytest` in test_chat_history_manager.py, test_rag_system.py,
        test_main_console.py (none of these files use pytest directly — no
        pytest.raises, pytest.mark, etc.)
      - `from unittest.mock import ... patch` in test_main_console.py (patch is unused;
        all mocking is done via monkeypatch)
Why:  Ruff is a required lint gate per CLAUDE.md. All 6 are auto-fixable with
      `ruff check --fix`.
Fix:  Run `/fix` to clean all six automatically.

[SHOULD FIX] pyproject.toml:[tool.coverage.run] omit list
What: The spec (Task 1) says to omit `conftest.py`. The implementation omits
      `conftest.py` (the root-level file) instead of `tests/conftest.py`. There is no
      root-level conftest.py in this project — the conftest lives at `tests/conftest.py`
      — so the omit rule currently matches nothing useful. Additionally, `streamlit_app.py`
      is omitted from coverage even though `test_streamlit_app.py` tests it and achieves
      meaningful coverage of its non-rendering functions. Omitting it hides real coverage
      from the report and could mask regressions.
Why:  The coverage omit list should reflect actual file paths. An incorrect path means
      the omit rule silently does nothing. Hiding covered code inflates the miss count
      and makes the 75% threshold meaningless for that module.
Fix:  Change `conftest.py` to `tests/conftest.py` in the omit list. Remove
      `streamlit_app.py` from the omit list so its coverage is tracked (or add an
      explicit comment explaining why it is excluded if exclusion is intentional).

[CONSIDER] tests/test_vector_store_creator.py: build_vector_store batching path
What: `build_vector_store()` has a batching branch (lines 71-76 of vector_store_creator.py)
      that runs when `len(chunks) > 1000`, calling `FAISS.merge_from()` repeatedly. The
      test `test_build_orchestrates_full_pipeline` only exercises the simple single-batch
      path (1 mock chunk). The batching branch (the majority of the function's complexity)
      is untested.
Why:  The batching logic has its own loop and a separate `FAISS.from_documents` call.
      A regression there would go undetected.
Fix:  Add a test that passes more than 1000 mock chunks to `build_vector_store()` and
      asserts that `mock_db.merge_from` is called at least once.

[CONSIDER] tests/conftest.py: mock_doc metadata key discrepancy with the spec
What: The spec (Task 2) specifies `mock_doc.metadata = {"page": 27}`. The implementation
      uses `{"page_number": 27}`. This is not a bug — the implementation correctly
      matches the actual key used in `vector_retriever.py` (`doc.metadata.get
      ("page_number", "N/A")`) — but it deviates from the spec's fixture definition.
Why:  Not a correctness issue (the implementation is right and the spec was wrong about
      the key name). Calling it out so the spec can be updated if desired for accuracy.
Fix:  No code change required. Optionally update the spec's Task 2 fixture description
      from `{"page": 27}` to `{"page_number": 27}` to reflect the actual implementation.

[CONSIDER] tests/test_rag_system.py: _make_chain_mock wiring
What: `_make_chain_mock` returns `(mock_prompt, mock_chain)` but only `mock_prompt` is
      needed by the caller (the chain is what prompt | llm | parser produces, and the
      mock wires it so `mock_prompt.__or__` returns a mock whose `__or__` returns
      `mock_chain`). However the actual `rag_system.ask_question` builds `chain = prompt
      | llm | parser` — two `|` operations. The helper wires only one level of `__or__`
      on `mock_prompt` and one on `mock_intermediate`, which matches the two `|`
      operations exactly. This is correct but fragile: if the LCEL chain in rag_system
      is ever extended with an extra operator, these tests will silently start returning
      a MagicMock as the answer rather than raising, masking the breakage.
Why:  Silent false-pass risk in the most critical test file.
Fix:  Consider adding `assert isinstance(answer, str)` to every `ask_question` happy-
      path test so that a mock misconfiguration raises rather than passes silently.

---
POSITIVES
---------

1. Fixture design in conftest.py is clean and well-structured. The autouse
   `clear_config_cache` fixture correctly clears the lru_cache both before and after
   each test, preventing inter-test pollution from the singleton config. The layered
   `history_file` / `populated_history_file` fixtures avoid duplication and are
   immediately readable.

2. The streamlit isolation pattern in test_streamlit_app.py is excellent. The
   `MockSessionState` class faithfully replicates Streamlit's dual attribute/`in`-
   operator access contract, and the `isolate_streamlit_app` autouse fixture ensures
   every test gets a clean module import. This is exactly the right approach for testing
   Streamlit apps without a running server.

3. The `test_process_documents_page_number_arithmetic` test in test_vector_retriever.py
   is precise and valuable. It pins the exact off-by-22 page correction formula
   (`page_number - 22`) to a concrete expected value ("Page 5"), making it a
   regression-proof canary for that business logic.

---
SUMMARY
-------

The implementation delivers all 8 tasks from the tech spec: pyproject.toml is correctly
configured, all 7 test files are present, 111 tests pass in ~5 seconds, and the 77%
total coverage clears the 75% threshold. The two [SHOULD FIX] items (Black and Ruff
failures) are the only blockers for /ship-feature — both are fully auto-fixable in a
single `/fix` run. The coverage omit-list issue is a housekeeping correction that should
also be addressed before shipping. No correctness or safety problems were found in the
test logic itself.
