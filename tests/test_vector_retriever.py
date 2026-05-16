import pytest
from unittest.mock import MagicMock, patch, mock_open


def _make_config(**kwargs) -> MagicMock:
    cfg = MagicMock()
    cfg.db_path = "vectorDB/my_FAISS_db"
    cfg.retriever_path = "vectorDB/retriever.pkl"
    cfg.retriever_k = 12
    cfg.retriever_fetch_k = 25
    cfg.retriever_lambda_mult = 0.7
    cfg.max_context_docs = 20
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


@pytest.fixture(autouse=True)
def reset_retriever(monkeypatch):
    import vector_retriever

    monkeypatch.setattr(vector_retriever, "_retriever", None)
    yield
    monkeypatch.setattr(vector_retriever, "_retriever", None)


# ---------------------------------------------------------------------------
# generate_related_terms  (pure logic — no mocks needed)
# ---------------------------------------------------------------------------


def test_generate_related_terms_returns_list_of_strings():
    import vector_retriever

    result = vector_retriever.generate_related_terms("tooth pathology")

    assert isinstance(result, list)
    assert all(isinstance(t, str) for t in result)


def test_generate_related_terms_expands_known_keywords():
    import vector_retriever

    result = vector_retriever.generate_related_terms("diagnosis and treatment")

    # "diagnosis" and "treatment" are known expansion keys
    known_expansions = {
        "clinical features",
        "symptoms",
        "signs",
        "management",
        "therapy",
        "intervention",
    }
    assert any(term in known_expansions for term in result)


def test_generate_related_terms_max_five():
    import vector_retriever

    result = vector_retriever.generate_related_terms(
        "anomalies development tooth pathology diagnosis treatment etiology classification"
    )

    assert len(result) <= 5


def test_generate_related_terms_empty_query():
    import vector_retriever

    result = vector_retriever.generate_related_terms("")

    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# process_documents_for_context
# ---------------------------------------------------------------------------


def test_process_documents_returns_tuple(mock_docs):
    import vector_retriever

    context, sources = vector_retriever.process_documents_for_context(mock_docs)

    assert isinstance(context, str)
    assert isinstance(sources, dict)


def test_process_documents_page_number_arithmetic():
    import vector_retriever

    doc = MagicMock()
    doc.page_content = "Sample content."
    doc.metadata = {"page_number": 27}

    context, sources = vector_retriever.process_documents_for_context([doc])

    # 27 - 22 = 5 → "Page 5"
    assert "Page 5" in sources
    assert "Sample content." in context


def test_process_documents_front_matter_for_low_page_numbers():
    import vector_retriever

    doc = MagicMock()
    doc.page_content = "Front matter content."
    doc.metadata = {"page_number": 5}

    context, sources = vector_retriever.process_documents_for_context([doc])

    # 5 - 22 = -17, corrected_page <= 0 → "Front Matter"
    assert "Front Matter" in sources


def test_process_documents_front_matter_when_no_page_number():
    import vector_retriever

    doc = MagicMock()
    doc.page_content = "Content without page."
    doc.metadata = {}

    context, sources = vector_retriever.process_documents_for_context([doc])

    assert "Front Matter" in sources


def test_process_documents_groups_same_page(mock_doc):
    import vector_retriever

    doc2 = MagicMock()
    doc2.page_content = "Second chunk on same page."
    doc2.metadata = {"page_number": 27}

    context, sources = vector_retriever.process_documents_for_context([mock_doc, doc2])

    assert len(sources) == 1
    page_key = list(sources.keys())[0]
    assert len(sources[page_key]) == 2


# ---------------------------------------------------------------------------
# get_retriever — cache hit path (retriever.pkl exists)
# ---------------------------------------------------------------------------


def test_get_retriever_loads_from_pickle_cache(monkeypatch):
    import vector_retriever

    mock_cached_retriever = MagicMock()
    monkeypatch.setattr(vector_retriever, "get_config", lambda: _make_config())

    exists_responses = {
        "vectorDB/my_FAISS_db": True,
        "vectorDB/retriever.pkl": True,
    }

    with patch(
        "vector_retriever.os.path.exists",
        side_effect=lambda p: exists_responses.get(p, False),
    ):
        with patch("builtins.open", mock_open()):
            with patch(
                "vector_retriever.pickle.load", return_value=mock_cached_retriever
            ):
                result = vector_retriever.get_retriever()

    assert result is mock_cached_retriever


def test_get_retriever_returns_cached_global(monkeypatch):
    import vector_retriever

    mock_existing = MagicMock()
    monkeypatch.setattr(vector_retriever, "_retriever", mock_existing)

    result = vector_retriever.get_retriever()

    assert result is mock_existing


# ---------------------------------------------------------------------------
# get_retriever — cache miss path (no retriever.pkl, load from FAISS)
# ---------------------------------------------------------------------------


def test_get_retriever_builds_from_faiss_when_no_pkl(monkeypatch):
    import vector_retriever

    mock_retriever_instance = MagicMock()
    mock_db = MagicMock()
    mock_db.as_retriever.return_value = mock_retriever_instance

    mock_embedding = MagicMock()
    monkeypatch.setattr(vector_retriever, "get_config", lambda: _make_config())
    monkeypatch.setattr(vector_retriever, "get_embedding_model", lambda: mock_embedding)

    exists_responses = {
        "vectorDB/my_FAISS_db": True,
        "vectorDB/retriever.pkl": False,
    }

    with patch(
        "vector_retriever.os.path.exists",
        side_effect=lambda p: exists_responses.get(p, False),
    ):
        with patch("vector_retriever.FAISS.load_local", return_value=mock_db):
            with patch("builtins.open", mock_open()):
                with patch("vector_retriever.pickle.dump"):
                    result = vector_retriever.get_retriever()

    assert result is mock_retriever_instance
    mock_db.as_retriever.assert_called_once()


def test_get_retriever_raises_when_db_missing(monkeypatch):
    import vector_retriever

    monkeypatch.setattr(vector_retriever, "get_config", lambda: _make_config())

    from exceptions import RetrieverError

    with patch("vector_retriever.os.path.exists", return_value=False):
        with pytest.raises(RetrieverError):
            vector_retriever.get_retriever()
