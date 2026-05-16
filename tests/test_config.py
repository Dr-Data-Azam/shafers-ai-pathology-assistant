# tests/test_config.py
import pytest


def _clear_cache() -> None:
    from config import get_config

    get_config.cache_clear()


@pytest.fixture(autouse=True)
def clear_config_cache():
    _clear_cache()
    yield
    _clear_cache()


# ---------------------------------------------------------------------------
# Original tests (preserved)
# ---------------------------------------------------------------------------


def test_defaults_applied_with_both_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq")

    from config import AppConfig

    # _env_file=None prevents reading the real .env so only monkeypatched vars are used
    cfg = AppConfig(_env_file=None)

    assert cfg.temperature == 0.3
    assert cfg.max_tokens == 1500
    assert cfg.llm_timeout == 60
    assert cfg.retriever_k == 12
    assert cfg.retriever_fetch_k == 25
    assert cfg.retriever_lambda_mult == 0.7
    assert cfg.max_context_docs == 20
    assert cfg.chunk_size == 500
    assert cfg.chunk_overlap == 50
    assert cfg.db_path == "vectorDB/my_FAISS_db"
    assert cfg.retriever_path == "vectorDB/retriever.pkl"
    assert cfg.data_path == "data/"
    assert cfg.chat_history_path == "chat_history.json"
    assert cfg.openai_model == "gpt-4o"
    assert cfg.groq_model == "llama-3.1-8b-instant"
    assert cfg.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"


def test_missing_both_llm_keys_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from config import AppConfig
    from exceptions import ConfigError

    with pytest.raises(ConfigError):
        AppConfig(_env_file=None)


def test_only_openai_key_is_sufficient(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-only-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.openai_api_key == "sk-test-only-openai"
    assert cfg.groq_api_key is None


def test_only_groq_key_is_sufficient(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-only-groq")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.groq_api_key == "gsk-test-only-groq"
    assert cfg.openai_api_key is None


def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-override")
    monkeypatch.setenv("RETRIEVER_K", "8")
    monkeypatch.setenv("TEMPERATURE", "0.1")
    monkeypatch.setenv("CHAT_HISTORY_PATH", "/tmp/custom_history.json")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.retriever_k == 8
    assert cfg.temperature == 0.1
    assert cfg.chat_history_path == "/tmp/custom_history.json"


# ---------------------------------------------------------------------------
# Extended tests — API keys
# ---------------------------------------------------------------------------


def test_both_keys_stored_correctly(monkeypatch):
    """Both API keys are stored on the config object when both are provided."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-both-openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-both-groq")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.openai_api_key == "sk-both-openai"
    assert cfg.groq_api_key == "gsk-both-groq"


def test_huggingface_token_is_optional(monkeypatch):
    """HuggingFace token is not required — config loads fine without it."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-hf-test")
    monkeypatch.delenv("HUGGINGFACEHUB_ACCESS_TOKEN", raising=False)

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.huggingfacehub_access_token is None


def test_huggingface_token_stored_when_set(monkeypatch):
    """HuggingFace token is stored when it is provided."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-hf-test2")
    monkeypatch.setenv("HUGGINGFACEHUB_ACCESS_TOKEN", "hf_faketoken123")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.huggingfacehub_access_token == "hf_faketoken123"


def test_config_error_message_mentions_at_least_one_key(monkeypatch):
    """The ConfigError message references the missing LLM key requirement."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from config import AppConfig
    from exceptions import ConfigError

    with pytest.raises(ConfigError) as exc_info:
        AppConfig(_env_file=None)

    assert "At least one" in exc_info.value.message


# ---------------------------------------------------------------------------
# Extended tests — path overrides
# ---------------------------------------------------------------------------


def test_db_path_override(monkeypatch):
    """DB_PATH env var overrides the default vector DB path."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-path-test")
    monkeypatch.setenv("DB_PATH", "custom/db_path")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.db_path == "custom/db_path"


def test_retriever_path_override(monkeypatch):
    """RETRIEVER_PATH env var overrides the default retriever pickle path."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ret-path")
    monkeypatch.setenv("RETRIEVER_PATH", "custom/retriever.pkl")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.retriever_path == "custom/retriever.pkl"


def test_data_path_override(monkeypatch):
    """DATA_PATH env var overrides the default data directory."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-data-path")
    monkeypatch.setenv("DATA_PATH", "my_data/")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.data_path == "my_data/"


# ---------------------------------------------------------------------------
# Extended tests — model overrides
# ---------------------------------------------------------------------------


def test_openai_model_override(monkeypatch):
    """OPENAI_MODEL env var overrides the default model name."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-model-override")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.openai_model == "gpt-4-turbo"


def test_groq_model_override(monkeypatch):
    """GROQ_MODEL env var overrides the default Groq model name."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk-model-override")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.groq_model == "llama-3.1-70b-versatile"


def test_embedding_model_override(monkeypatch):
    """EMBEDDING_MODEL env var overrides the default embedding model."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-embed-override")
    monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.embedding_model == "sentence-transformers/all-mpnet-base-v2"


# ---------------------------------------------------------------------------
# Extended tests — numeric config overrides
# ---------------------------------------------------------------------------


def test_max_tokens_override(monkeypatch):
    """MAX_TOKENS env var is parsed as integer and overrides the default."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-tok-override")
    monkeypatch.setenv("MAX_TOKENS", "2000")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.max_tokens == 2000


def test_llm_timeout_override(monkeypatch):
    """LLM_TIMEOUT env var is parsed as integer and overrides the default."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-timeout-override")
    monkeypatch.setenv("LLM_TIMEOUT", "120")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.llm_timeout == 120


def test_retriever_fetch_k_override(monkeypatch):
    """RETRIEVER_FETCH_K env var overrides the default fetch_k value."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fetch-k-override")
    monkeypatch.setenv("RETRIEVER_FETCH_K", "50")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.retriever_fetch_k == 50


def test_retriever_lambda_mult_override(monkeypatch):
    """RETRIEVER_LAMBDA_MULT env var is parsed as float and overrides the default."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-lambda-override")
    monkeypatch.setenv("RETRIEVER_LAMBDA_MULT", "0.5")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.retriever_lambda_mult == pytest.approx(0.5)


def test_max_context_docs_override(monkeypatch):
    """MAX_CONTEXT_DOCS env var overrides the default max context docs."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ctx-override")
    monkeypatch.setenv("MAX_CONTEXT_DOCS", "10")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.max_context_docs == 10


def test_chunk_size_override(monkeypatch):
    """CHUNK_SIZE env var overrides the default chunk size."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-chunk-override")
    monkeypatch.setenv("CHUNK_SIZE", "256")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.chunk_size == 256


def test_chunk_overlap_override(monkeypatch):
    """CHUNK_OVERLAP env var overrides the default chunk overlap."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-overlap-override")
    monkeypatch.setenv("CHUNK_OVERLAP", "25")

    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    assert cfg.chunk_overlap == 25


# ---------------------------------------------------------------------------
# Extended tests — get_config() singleton behaviour
# ---------------------------------------------------------------------------


def test_get_config_is_singleton(monkeypatch):
    """get_config() returns the exact same object on repeated calls."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-singleton-test")

    from config import get_config

    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_get_config_cache_clear_returns_fresh_instance(monkeypatch):
    """After cache_clear(), get_config() builds a new AppConfig instance."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fresh-1")

    from config import get_config

    cfg1 = get_config()
    get_config.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fresh-2")
    cfg2 = get_config()

    # Different objects after cache clear
    assert cfg1 is not cfg2


def test_get_config_reads_updated_env_after_cache_clear(monkeypatch):
    """Fresh get_config() call picks up env changes made after the last cache_clear()."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-step1")
    monkeypatch.setenv("MAX_TOKENS", "1000")

    from config import get_config

    cfg1 = get_config()
    assert cfg1.max_tokens == 1000

    get_config.cache_clear()
    monkeypatch.setenv("MAX_TOKENS", "3000")

    cfg2 = get_config()
    assert cfg2.max_tokens == 3000


# ---------------------------------------------------------------------------
# configure_logging()
# ---------------------------------------------------------------------------


def test_configure_logging_attaches_rotating_file_and_stderr_handlers(
    monkeypatch, tmp_path
):
    """configure_logging() adds a RotatingFileHandler and a StreamHandler to root."""
    import logging
    import logging.handlers

    monkeypatch.setenv("OPENAI_API_KEY", "sk-log-test")

    from config import AppConfig, configure_logging

    cfg = AppConfig(
        _env_file=None, log_file=str(tmp_path / "test.log"), log_level="DEBUG"
    )

    root = logging.getLogger()
    original_handlers = root.handlers[:]
    root.handlers.clear()

    try:
        configure_logging(cfg)

        handler_types = [type(h) for h in root.handlers]
        assert logging.handlers.RotatingFileHandler in handler_types
        assert logging.StreamHandler in handler_types
        assert root.level == logging.DEBUG
    finally:
        for h in root.handlers[:]:
            h.close()
            root.removeHandler(h)
        root.handlers.extend(original_handlers)


def test_configure_logging_is_idempotent(monkeypatch, tmp_path):
    """Calling configure_logging() twice does not add duplicate handlers."""
    import logging

    monkeypatch.setenv("OPENAI_API_KEY", "sk-idempotent-test")

    from config import AppConfig, configure_logging

    cfg = AppConfig(_env_file=None, log_file=str(tmp_path / "test2.log"))

    root = logging.getLogger()
    original_handlers = root.handlers[:]
    root.handlers.clear()

    try:
        configure_logging(cfg)
        count_after_first = len(root.handlers)
        configure_logging(cfg)
        count_after_second = len(root.handlers)

        assert count_after_second == count_after_first
    finally:
        for h in root.handlers[:]:
            h.close()
            root.removeHandler(h)
        root.handlers.extend(original_handlers)
