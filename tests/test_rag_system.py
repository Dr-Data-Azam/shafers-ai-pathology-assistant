import pytest
from unittest.mock import MagicMock, patch


def _make_chain_mock(answer: str = "Test answer") -> tuple:
    """Return (mock_prompt, mock_chain) pre-wired so prompt | llm | parser → chain.invoke() == answer."""
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = answer

    mock_intermediate = MagicMock()
    mock_intermediate.__or__ = MagicMock(return_value=mock_chain)

    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_intermediate)

    return mock_prompt, mock_chain


def _make_config(**kwargs) -> MagicMock:
    cfg = MagicMock()
    cfg.db_path = "vectorDB/my_FAISS_db"
    cfg.retriever_path = "vectorDB/retriever.pkl"
    cfg.chat_history_path = "chat_history.json"
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------------------
# create_prompt
# ---------------------------------------------------------------------------


def test_create_prompt_returns_prompt_template():
    from langchain_core.prompts import PromptTemplate

    import rag_system

    result = rag_system.create_prompt()

    assert isinstance(result, PromptTemplate)
    assert "context" in result.input_variables
    assert "question" in result.input_variables


# ---------------------------------------------------------------------------
# ask_question — happy path
# ---------------------------------------------------------------------------


def test_ask_question_returns_tuple(monkeypatch, mock_docs):
    import rag_system

    mock_prompt, mock_chain = _make_chain_mock("Cellulitis is a skin infection.")
    mock_page_groups = {"Page 5": ["content"]}

    monkeypatch.setattr(rag_system, "validate_provider", MagicMock())
    monkeypatch.setattr(
        rag_system, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(rag_system, "load_llm", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(
        rag_system, "get_comprehensive_context", MagicMock(return_value=mock_docs)
    )
    monkeypatch.setattr(
        rag_system,
        "process_documents_for_context",
        MagicMock(return_value=("context text", mock_page_groups)),
    )
    monkeypatch.setattr(
        rag_system, "create_prompt", MagicMock(return_value=mock_prompt)
    )
    monkeypatch.setattr(rag_system, "StrOutputParser", MagicMock())
    monkeypatch.setattr(rag_system, "save_chat_history", MagicMock())

    answer, stats = rag_system.ask_question("What is cellulitis?", provider="openai")

    assert isinstance(stats, dict)
    assert stats["provider"] == "OPENAI"
    assert stats["success"] is True
    assert "total_time" in stats
    assert "pages_retrieved" in stats
    assert "documents_retrieved" in stats


def test_ask_question_stats_doc_counts(monkeypatch, mock_docs):
    import rag_system

    mock_prompt, _ = _make_chain_mock()
    mock_page_groups = {"Page 5": ["a"], "Page 8": ["b"]}

    monkeypatch.setattr(rag_system, "validate_provider", MagicMock())
    monkeypatch.setattr(
        rag_system, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(rag_system, "load_llm", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(
        rag_system, "get_comprehensive_context", MagicMock(return_value=mock_docs)
    )
    monkeypatch.setattr(
        rag_system,
        "process_documents_for_context",
        MagicMock(return_value=("context", mock_page_groups)),
    )
    monkeypatch.setattr(
        rag_system, "create_prompt", MagicMock(return_value=mock_prompt)
    )
    monkeypatch.setattr(rag_system, "StrOutputParser", MagicMock())
    monkeypatch.setattr(rag_system, "save_chat_history", MagicMock())

    _, stats = rag_system.ask_question("question", provider="groq")

    assert stats["documents_retrieved"] == len(mock_docs)
    assert stats["pages_retrieved"] == len(mock_page_groups)
    assert stats["provider"] == "GROQ"


def test_ask_question_saves_history_when_flag_true(monkeypatch, mock_docs):
    import rag_system

    mock_prompt, _ = _make_chain_mock()
    mock_save = MagicMock()

    monkeypatch.setattr(rag_system, "validate_provider", MagicMock())
    monkeypatch.setattr(
        rag_system, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(rag_system, "load_llm", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(
        rag_system, "get_comprehensive_context", MagicMock(return_value=mock_docs)
    )
    monkeypatch.setattr(
        rag_system,
        "process_documents_for_context",
        MagicMock(return_value=("context", {"Page 5": ["x"]})),
    )
    monkeypatch.setattr(
        rag_system, "create_prompt", MagicMock(return_value=mock_prompt)
    )
    monkeypatch.setattr(rag_system, "StrOutputParser", MagicMock())
    monkeypatch.setattr(rag_system, "save_chat_history", mock_save)

    rag_system.ask_question("question", save_history=True)

    mock_save.assert_called_once()


def test_ask_question_skips_history_when_flag_false(monkeypatch, mock_docs):
    import rag_system

    mock_prompt, _ = _make_chain_mock()
    mock_save = MagicMock()

    monkeypatch.setattr(rag_system, "validate_provider", MagicMock())
    monkeypatch.setattr(
        rag_system, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(rag_system, "load_llm", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(
        rag_system, "get_comprehensive_context", MagicMock(return_value=mock_docs)
    )
    monkeypatch.setattr(
        rag_system,
        "process_documents_for_context",
        MagicMock(return_value=("context", {"Page 5": ["x"]})),
    )
    monkeypatch.setattr(
        rag_system, "create_prompt", MagicMock(return_value=mock_prompt)
    )
    monkeypatch.setattr(rag_system, "StrOutputParser", MagicMock())
    monkeypatch.setattr(rag_system, "save_chat_history", mock_save)

    rag_system.ask_question("question", save_history=False)

    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# ask_question — error path
# ---------------------------------------------------------------------------


def test_ask_question_propagates_retriever_error(monkeypatch):
    import rag_system
    from exceptions import RetrieverError

    monkeypatch.setattr(rag_system, "validate_provider", MagicMock())
    monkeypatch.setattr(
        rag_system,
        "get_retriever",
        MagicMock(side_effect=RetrieverError("DB missing")),
    )

    with pytest.raises(RetrieverError, match="DB missing"):
        rag_system.ask_question("question")


# ---------------------------------------------------------------------------
# get_system_info
# ---------------------------------------------------------------------------


def test_get_system_info_returns_expected_keys(monkeypatch):
    import rag_system

    # get_system_info() imports get_available_providers and get_config locally,
    # so we patch at their source modules.
    monkeypatch.setattr(
        "llm_provider_manager.get_available_providers",
        MagicMock(return_value=["openai"]),
    )
    monkeypatch.setattr("config.get_config", lambda: _make_config())

    with patch("os.path.exists", return_value=True):
        info = rag_system.get_system_info()

    assert "vector_db_exists" in info
    assert "available_providers" in info
    assert "retriever_cached" in info
    assert "chat_history_exists" in info


def test_get_system_info_vector_db_false_when_missing(monkeypatch):
    import rag_system

    monkeypatch.setattr(
        "llm_provider_manager.get_available_providers", MagicMock(return_value=[])
    )
    monkeypatch.setattr("config.get_config", lambda: _make_config())

    with patch("os.path.exists", return_value=False):
        info = rag_system.get_system_info()

    assert info["vector_db_exists"] is False
