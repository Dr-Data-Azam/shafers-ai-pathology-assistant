---
name: write-test
description: >
  Use this skill whenever you need to write pytest tests for the Shafer's AI Pathology
  Assistant project. Covers what to mock and exactly how, fixture patterns, file naming,
  conftest.py structure, coverage targets, and module-specific testing strategies.
  Trigger when the test-writer agent is invoked, when the coder says "write tests",
  "add tests for X", or "create test_<module>.py". Always read this skill before writing
  any test file. Never hit real APIs, real FAISS, or real disk paths in tests.
---

# Skill: Write Tests for Shafer's AI Pathology Assistant

This skill is used by the test-writer sub-agent and when writing tests directly.
It defines every convention, mock pattern, and fixture needed to write correct,
isolated, fast pytest tests for this project.

Rule #1: Never make real API calls. Never load real FAISS. Never write to real disk paths.
Every external dependency must be mocked or isolated with tmp_path.

---

## Project Test Layout

```
tests/
├── conftest.py                  <- shared fixtures (always check here first)
├── test_config.py               <- config loading, validation, defaults
├── test_llm_provider.py         <- provider loading, validation, caching
├── test_chat_history.py         <- save/load/clear/stats with tmp_path
├── test_vector_retriever.py     <- term expansion, doc processing (mock FAISS)
├── test_rag_system.py           <- ask_question() end-to-end (mock chain)
└── integration/
    └── test_rag_integration.py  <- skipped in CI, requires real vector DB
```

File naming: test_<module_name>.py mirrors the source file it tests.

---

## Running Tests

```bash
# Full suite with coverage
pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

# Single file
pytest tests/test_chat_history.py -v

# Skip integration tests (default in CI)
pytest tests/ -v --ignore=tests/integration/

# Fail fast on first failure
pytest tests/ -x
```

---

## conftest.py — Shared Fixtures

Always check tests/conftest.py before creating new fixtures.
Add shared fixtures here rather than duplicating across test files.

```python
# tests/conftest.py
import pytest
import json
from unittest.mock import MagicMock


@pytest.fixture
def history_file(tmp_path):
    """A real temp file acting as chat_history.json."""
    return tmp_path / "chat_history.json"


@pytest.fixture
def populated_history_file(history_file):
    """history_file pre-loaded with two sample interactions."""
    records = [
        {
            "timestamp": "2026-01-01T10:00:00",
            "question": "What is a cyst?",
            "answer": "A cyst is a pathological cavity.",
            "provider": "OPENAI",
            "performance": {"retrieval_time": 0.5, "llm_time": 1.2, "total_time": 1.7},
            "pages_retrieved": 3,
        },
        {
            "timestamp": "2026-01-01T11:00:00",
            "question": "Define leukoplakia.",
            "answer": "Leukoplakia is a white patch.",
            "provider": "GROQ",
            "performance": {"retrieval_time": 0.3, "llm_time": 0.8, "total_time": 1.1},
            "pages_retrieved": 2,
        },
    ]
    history_file.write_text(json.dumps(records, indent=2))
    return history_file


@pytest.fixture
def mock_doc():
    """A single fake LangChain Document."""
    doc = MagicMock()
    doc.page_content = "Oral pathology deals with diseases of the mouth."
    doc.metadata = {"page_number": 27, "source": "shafers.pdf"}
    return doc


@pytest.fixture
def mock_docs(mock_doc):
    """A list of three fake Documents."""
    doc2 = MagicMock()
    doc2.page_content = "Cysts are fluid-filled cavities lined by epithelium."
    doc2.metadata = {"page_number": 45, "source": "shafers.pdf"}

    doc3 = MagicMock()
    doc3.page_content = "Leukoplakia presents as a white patch on the mucosa."
    doc3.metadata = {"page_number": 112, "source": "shafers.pdf"}

    return [mock_doc, doc2, doc3]


@pytest.fixture
def mock_retriever(mock_docs):
    """A FAISS retriever mock whose .invoke() returns mock_docs."""
    retriever = MagicMock()
    retriever.invoke.return_value = mock_docs
    return retriever


@pytest.fixture
def set_api_keys(monkeypatch):
    """Set fake API keys so provider validation passes."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-openai-key")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake-groq-key")
    monkeypatch.setenv("HUGGINGFACEHUB_ACCESS_TOKEN", "hf_faketoken")
```

---

## Module-by-Module Testing Strategies

### test_config.py

Tests the Pydantic Settings class and get_config() singleton (after config-refactor).

Key patterns:
- Use monkeypatch.setenv() to set required keys
- Use monkeypatch.delenv() to test missing-key behavior
- Import get_config inside test functions, after env is patched

```python
def test_config_loads_with_all_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake")
    monkeypatch.setenv("HUGGINGFACEHUB_ACCESS_TOKEN", "hf_fake")
    from config import get_config
    cfg = get_config()
    assert cfg.OPENAI_API_KEY == "sk-fake"

def test_config_uses_defaults(set_api_keys):
    from config import get_config
    cfg = get_config()
    assert cfg.TEMPERATURE == 0.3
    assert cfg.MAX_TOKENS == 1500
    assert cfg.RETRIEVAL_K == 12

def test_missing_required_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        from config import get_config
        get_config()

def test_get_config_is_singleton(set_api_keys):
    from config import get_config
    assert get_config() is get_config()
```

---

### test_llm_provider.py

Tests validate_provider(), load_llm(), and clear_llm_cache().

Key patterns:
- Mock ChatOpenAI and ChatGroq constructors so no real network call is made
- Always call clear_llm_cache() before tests that check caching — the module-level
  _llm_openai and _llm_groq globals persist between tests if not reset

```python
from unittest.mock import patch, MagicMock

def test_validate_passes_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    from llm_provider_manager import validate_provider
    assert validate_provider("openai") is True

def test_validate_raises_when_no_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from llm_provider_manager import validate_provider
    with pytest.raises(Exception, match="No API keys found"):
        validate_provider("openai")

@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_openai_is_cached(mock_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    import llm_provider_manager
    llm_provider_manager.clear_llm_cache()
    mock_cls.return_value = MagicMock()
    llm_provider_manager.load_llm("openai")
    llm_provider_manager.load_llm("openai")
    mock_cls.assert_called_once()  # cached — constructor called only once
```

---

### test_chat_history.py

Tests save_chat_history(), load_chat_history(), clear_chat_history(), get_history_stats().

Key pattern: monkeypatch CHAT_HISTORY_PATH to a tmp_path file. Never write to real disk.

```python
def test_save_and_load_round_trip(tmp_path, monkeypatch):
    path = str(tmp_path / "chat_history.json")
    monkeypatch.setattr("chat_history_manager.CHAT_HISTORY_PATH", path)
    from chat_history_manager import save_chat_history, load_chat_history
    save_chat_history("What is a cyst?", "A cyst is...", "openai", 0.5, 1.2, 1.7, 3)
    loaded = load_chat_history()
    assert len(loaded) == 1
    assert loaded[0]["question"] == "What is a cyst?"

def test_history_capped_at_100(tmp_path, monkeypatch):
    path = str(tmp_path / "chat_history.json")
    monkeypatch.setattr("chat_history_manager.CHAT_HISTORY_PATH", path)
    from chat_history_manager import save_chat_history, load_chat_history
    for i in range(105):
        save_chat_history(f"Q{i}", f"A{i}", "openai", 0.1, 0.2, 0.3, 1)
    assert len(load_chat_history()) == 100

def test_clear_empties_history(tmp_path, monkeypatch):
    path = str(tmp_path / "chat_history.json")
    monkeypatch.setattr("chat_history_manager.CHAT_HISTORY_PATH", path)
    from chat_history_manager import save_chat_history, clear_chat_history, load_chat_history
    save_chat_history("Q", "A", "openai", 0.1, 0.2, 0.3, 1)
    clear_chat_history()
    assert load_chat_history() == []

def test_stats_empty_history(tmp_path, monkeypatch):
    monkeypatch.setattr("chat_history_manager.CHAT_HISTORY_PATH",
                        str(tmp_path / "empty.json"))
    from chat_history_manager import get_history_stats
    stats = get_history_stats()
    assert stats["total_interactions"] == 0
```

---

### test_vector_retriever.py

Tests generate_related_terms() (pure logic — no mocks needed) and
process_documents_for_context() (use mock_docs fixture).

Key patterns:
- generate_related_terms() is pure Python — test directly with no mocking
- process_documents_for_context() uses mock_docs from conftest.py
- Page number offset: page_number=27 in metadata -> "Page 5" in output (27-22=5)
- When mocking os.path.exists() which is called multiple times in get_retriever(),
  use side_effect list to control each call: side_effect=[False, False]

```python
from unittest.mock import MagicMock, patch

def test_generate_related_terms_expands_anomalies():
    from vector_retriever import generate_related_terms
    terms = generate_related_terms("What are tooth anomalies?")
    assert any(t in terms for t in ["abnormalities", "malformations", "developmental disorders"])

def test_generate_related_terms_max_5():
    from vector_retriever import generate_related_terms
    result = generate_related_terms("anomalies development pathology diagnosis treatment etiology")
    assert len(result) <= 5

def test_page_number_offset_correction(mock_doc):
    from vector_retriever import process_documents_for_context
    mock_doc.metadata = {"page_number": 27}
    context, page_groups = process_documents_for_context([mock_doc])
    assert "Page 5" in page_groups  # 27 - 22 = 5

def test_missing_page_number_becomes_front_matter():
    from vector_retriever import process_documents_for_context
    doc = MagicMock()
    doc.page_content = "Text."
    doc.metadata = {}
    context, groups = process_documents_for_context([doc])
    assert "Front Matter" in groups

@patch("vector_retriever.os.path.exists", side_effect=[False, False])
def test_get_retriever_raises_when_db_missing(mock_exists):
    import vector_retriever
    vector_retriever._retriever = None
    from vector_retriever import get_retriever
    with pytest.raises(FileNotFoundError, match="Vector DB not found"):
        get_retriever()
```

---

### test_rag_system.py

Tests ask_question() end-to-end.

Critical: Add this autouse fixture at the top of test_rag_system.py to prevent
LLM global state from bleeding between tests:

```python
import llm_provider_manager

@pytest.fixture(autouse=True)
def reset_llm_cache():
    llm_provider_manager.clear_llm_cache()
    yield
    llm_provider_manager.clear_llm_cache()
```

Mock all four: load_llm, get_retriever, get_comprehensive_context, save_chat_history.

For the LCEL chain (prompt | llm | parser), mock at the chain level:

```python
from unittest.mock import patch, MagicMock

def _make_mock_chain(answer="Mocked answer."):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = answer
    mock_llm = MagicMock()
    intermediate = MagicMock()
    intermediate.__or__ = MagicMock(return_value=mock_chain)
    mock_llm.__ror__ = MagicMock(return_value=intermediate)
    return mock_llm

@patch("rag_system.save_chat_history")
@patch("rag_system.get_comprehensive_context")
@patch("rag_system.get_retriever")
@patch("rag_system.load_llm")
def test_ask_question_success(mock_load_llm, mock_get_retriever,
                               mock_get_context, mock_save, mock_docs, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    mock_load_llm.return_value = _make_mock_chain()
    mock_get_retriever.return_value = MagicMock()
    mock_get_context.return_value = mock_docs
    from rag_system import ask_question
    answer, stats = ask_question("What is a cyst?", provider="openai")
    assert stats["success"] is True
    assert stats["provider"] == "OPENAI"

@patch("rag_system.get_retriever")
@patch("rag_system.load_llm")
def test_ask_question_exception_returns_error(mock_load_llm, mock_get_retriever, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    mock_load_llm.side_effect = Exception("API failed")
    mock_get_retriever.return_value = MagicMock()
    from rag_system import ask_question
    answer, stats = ask_question("Q", provider="openai")
    assert answer.startswith("Error:")
    assert stats["success"] is False
```

---

## Coverage Targets

| Module | Target | Notes |
|--------|--------|-------|
| config.py | 90%+ | Test all validation paths |
| chat_history_manager.py | 85%+ | All CRUD paths + edge cases |
| llm_provider_manager.py | 80%+ | Both providers, caching, errors |
| vector_retriever.py | 75%+ | Pure logic easy; skip real FAISS I/O |
| rag_system.py | 75%+ | Mock the chain; test success and error |
| Any new feature code | 80%+ | Always meet this for new additions |

---

## Integration Tests (Skipped in CI)

```python
# tests/integration/test_rag_integration.py
import pytest, os

@pytest.mark.skipif(
    not os.path.exists("vectorDB/my_FAISS_db"),
    reason="Requires real vector DB — run locally only"
)
def test_real_ask_question():
    from rag_system import ask_question
    answer, stats = ask_question("What is leukoplakia?")
    assert stats["success"] is True
    assert len(answer) > 50
```

---

## Anti-Patterns — Never Do These

| Anti-Pattern | Why | Fix |
|-------------|-----|-----|
| load_llm("openai") without mocking | Real API call — fails in CI | @patch("module.load_llm") |
| open("chat_history.json") directly | Pollutes real disk | Use tmp_path + monkeypatch.setattr |
| get_retriever() without mocking | Requires real FAISS on disk | @patch("rag_system.get_retriever") |
| Asserting on exact LLM answer text | Brittle — mocked answers vary | Assert on stats["success"] or structure |
| Tests that depend on run order | State bleeds between tests | Use clear_llm_cache() and tmp_path |
| Import at module level in test file | Skips monkeypatching window | Import inside test function after patching |
