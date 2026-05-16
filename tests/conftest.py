import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock


def _clear_cache() -> None:
    from config import get_config

    get_config.cache_clear()


@pytest.fixture(autouse=True)
def clear_config_cache():
    _clear_cache()
    yield
    _clear_cache()


@pytest.fixture
def set_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq")
    monkeypatch.setenv("HUGGINGFACEHUB_ACCESS_TOKEN", "hf-test-token")


@pytest.fixture
def history_file(tmp_path) -> Path:
    return tmp_path / "chat_history.json"


@pytest.fixture
def populated_history_file(history_file: Path) -> Path:
    interactions = [
        {
            "timestamp": "2024-01-01T10:00:00",
            "question": "What is cellulitis?",
            "answer": "Cellulitis is a bacterial skin infection.",
            "provider": "OPENAI",
            "performance": {"retrieval_time": 0.5, "llm_time": 1.2, "total_time": 1.7},
            "pages_retrieved": 3,
        },
        {
            "timestamp": "2024-01-01T10:05:00",
            "question": "Describe ameloblastoma.",
            "answer": "Ameloblastoma is a benign odontogenic tumour.",
            "provider": "GROQ",
            "performance": {"retrieval_time": 0.4, "llm_time": 0.9, "total_time": 1.3},
            "pages_retrieved": 5,
        },
    ]
    history_file.write_text(json.dumps(interactions), encoding="utf-8")
    return history_file


@pytest.fixture
def mock_doc() -> MagicMock:
    doc = MagicMock()
    doc.page_content = "Test pathology content about oral disease."
    doc.metadata = {"page_number": 27}
    return doc


@pytest.fixture
def mock_docs(mock_doc) -> list:
    doc2 = MagicMock()
    doc2.page_content = "Additional content about diagnosis."
    doc2.metadata = {"page_number": 30}

    doc3 = MagicMock()
    doc3.page_content = "Further content about treatment options."
    doc3.metadata = {"page_number": 35}

    return [mock_doc, doc2, doc3]


@pytest.fixture
def mock_retriever(mock_docs) -> MagicMock:
    retriever = MagicMock()
    retriever.invoke.return_value = mock_docs
    return retriever
