import pytest
from unittest.mock import MagicMock, patch


def _make_config(**kwargs) -> MagicMock:
    cfg = MagicMock()
    cfg.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    cfg.chunk_size = 500
    cfg.chunk_overlap = 50
    cfg.db_path = "vectorDB/my_FAISS_db"
    cfg.data_path = "data/"
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


@pytest.fixture(autouse=True)
def reset_embedding_model(monkeypatch):
    import vector_store_creator

    monkeypatch.setattr(vector_store_creator, "_embedding_model", None)
    yield
    monkeypatch.setattr(vector_store_creator, "_embedding_model", None)


# ---------------------------------------------------------------------------
# get_embedding_model
# ---------------------------------------------------------------------------


def test_get_embedding_model_constructs_once(monkeypatch):
    import vector_store_creator

    mock_embeddings_cls = MagicMock()
    mock_instance = MagicMock()
    mock_embeddings_cls.return_value = mock_instance

    monkeypatch.setattr(
        vector_store_creator, "HuggingFaceEmbeddings", mock_embeddings_cls
    )
    monkeypatch.setattr(vector_store_creator, "get_config", lambda: _make_config())

    result1 = vector_store_creator.get_embedding_model()
    result2 = vector_store_creator.get_embedding_model()

    assert result1 is mock_instance
    assert result2 is mock_instance
    mock_embeddings_cls.assert_called_once_with(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def test_get_embedding_model_uses_config_model_name(monkeypatch):
    import vector_store_creator

    mock_embeddings_cls = MagicMock()
    monkeypatch.setattr(
        vector_store_creator, "HuggingFaceEmbeddings", mock_embeddings_cls
    )
    monkeypatch.setattr(
        vector_store_creator,
        "get_config",
        lambda: _make_config(embedding_model="custom/model"),
    )

    vector_store_creator.get_embedding_model()

    mock_embeddings_cls.assert_called_once()
    call_kwargs = mock_embeddings_cls.call_args[1]
    assert call_kwargs["model_name"] == "custom/model"


# ---------------------------------------------------------------------------
# load_pdf_files
# ---------------------------------------------------------------------------


def test_load_pdf_files_calls_directory_loader(monkeypatch):
    import vector_store_creator

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_loader_cls = MagicMock(return_value=mock_loader_instance)

    monkeypatch.setattr(vector_store_creator, "DirectoryLoader", mock_loader_cls)

    result = vector_store_creator.load_pdf_files("data/")

    mock_loader_cls.assert_called_once()
    mock_loader_instance.load.assert_called_once()
    assert len(result) == 1


def test_load_pdf_files_sets_page_number_metadata(monkeypatch):
    import vector_store_creator

    docs = [MagicMock(), MagicMock()]
    for doc in docs:
        doc.metadata = {}

    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = docs
    monkeypatch.setattr(
        vector_store_creator,
        "DirectoryLoader",
        MagicMock(return_value=mock_loader_instance),
    )

    result = vector_store_creator.load_pdf_files("data/")

    assert result[0].metadata["page_number"] == 1
    assert result[1].metadata["page_number"] == 2
    assert result[0].metadata["source"] == "Shafer"


# ---------------------------------------------------------------------------
# create_chunks
# ---------------------------------------------------------------------------


def test_create_chunks_calls_split_documents(monkeypatch, mock_docs):
    import vector_store_creator

    mock_chunks = [MagicMock(), MagicMock()]
    mock_splitter = MagicMock()
    mock_splitter.split_documents.return_value = mock_chunks
    mock_splitter_cls = MagicMock(return_value=mock_splitter)

    monkeypatch.setattr(
        vector_store_creator, "RecursiveCharacterTextSplitter", mock_splitter_cls
    )
    monkeypatch.setattr(vector_store_creator, "get_config", lambda: _make_config())

    result = vector_store_creator.create_chunks(mock_docs)

    mock_splitter.split_documents.assert_called_once_with(mock_docs)
    assert result == mock_chunks


def test_create_chunks_uses_config_sizes(monkeypatch, mock_docs):
    import vector_store_creator

    mock_splitter_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        vector_store_creator, "RecursiveCharacterTextSplitter", mock_splitter_cls
    )
    monkeypatch.setattr(
        vector_store_creator,
        "get_config",
        lambda: _make_config(chunk_size=300, chunk_overlap=30),
    )

    vector_store_creator.create_chunks(mock_docs)

    call_kwargs = mock_splitter_cls.call_args[1]
    assert call_kwargs["chunk_size"] == 300
    assert call_kwargs["chunk_overlap"] == 30


# ---------------------------------------------------------------------------
# build_vector_store
# ---------------------------------------------------------------------------


def test_build_skips_when_db_already_exists(monkeypatch):
    import vector_store_creator

    monkeypatch.setattr(vector_store_creator, "get_config", lambda: _make_config())
    mock_faiss = MagicMock()
    monkeypatch.setattr(vector_store_creator, "FAISS", mock_faiss)

    with patch("vector_store_creator.os.path.exists", return_value=True):
        vector_store_creator.build_vector_store()

    mock_faiss.from_documents.assert_not_called()


def test_build_orchestrates_full_pipeline(monkeypatch):
    import vector_store_creator

    monkeypatch.setattr(vector_store_creator, "get_config", lambda: _make_config())

    mock_docs = [MagicMock()]
    mock_chunks = [MagicMock()]
    mock_embedding = MagicMock()
    mock_db = MagicMock()

    monkeypatch.setattr(vector_store_creator, "load_pdf_files", lambda path: mock_docs)
    monkeypatch.setattr(vector_store_creator, "create_chunks", lambda docs: mock_chunks)
    monkeypatch.setattr(
        vector_store_creator, "get_embedding_model", lambda: mock_embedding
    )

    mock_faiss_cls = MagicMock()
    mock_faiss_cls.from_documents.return_value = mock_db
    monkeypatch.setattr(vector_store_creator, "FAISS", mock_faiss_cls)

    with patch("vector_store_creator.os.path.exists", return_value=False):
        vector_store_creator.build_vector_store()

    mock_faiss_cls.from_documents.assert_called_once_with(
        documents=mock_chunks, embedding=mock_embedding
    )
    mock_db.save_local.assert_called_once_with("vectorDB/my_FAISS_db")
