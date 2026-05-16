import pytest


def test_pathology_app_error_is_exception():
    from exceptions import PathologyAppError

    assert issubclass(PathologyAppError, Exception)
    e = PathologyAppError("something went wrong")
    assert str(e) == "something went wrong"


def test_llm_error_is_pathology_app_error():
    from exceptions import LLMError, PathologyAppError

    assert issubclass(LLMError, PathologyAppError)


def test_retriever_error_is_pathology_app_error():
    from exceptions import PathologyAppError, RetrieverError

    assert issubclass(RetrieverError, PathologyAppError)


def test_config_error_is_pathology_app_error():
    from exceptions import ConfigError, PathologyAppError

    assert issubclass(ConfigError, PathologyAppError)


def test_llm_error_stores_provider_and_message():
    from exceptions import LLMError

    e = LLMError(provider="openai", message="rate limit exceeded")
    assert e.provider == "openai"
    assert e.message == "rate limit exceeded"


def test_llm_error_str_includes_provider_and_message():
    from exceptions import LLMError

    e = LLMError(provider="groq", message="timeout")
    assert "[groq]" in str(e)
    assert "timeout" in str(e)


def test_retriever_error_stores_message():
    from exceptions import RetrieverError

    e = RetrieverError("DB not found")
    assert e.message == "DB not found"
    assert str(e) == "DB not found"


def test_config_error_stores_message():
    from exceptions import ConfigError

    e = ConfigError("missing API key")
    assert e.message == "missing API key"
    assert str(e) == "missing API key"


def test_llm_error_is_catchable_as_exception():
    from exceptions import LLMError

    with pytest.raises(Exception):
        raise LLMError(provider="openai", message="boom")


def test_retriever_error_is_catchable_as_exception():
    from exceptions import RetrieverError

    with pytest.raises(Exception):
        raise RetrieverError("index missing")


def test_config_error_is_catchable_as_exception():
    from exceptions import ConfigError

    with pytest.raises(Exception):
        raise ConfigError("bad config")
