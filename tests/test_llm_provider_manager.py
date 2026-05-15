# tests/test_llm_provider_manager.py
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Autouse fixtures — reset module-level LLM globals and config cache
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_llm_cache():
    """Clear the LLM globals before and after every test in this file."""
    import llm_provider_manager

    llm_provider_manager.clear_llm_cache()
    yield
    llm_provider_manager.clear_llm_cache()


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear the lru_cache on get_config() before and after every test."""
    from config import get_config

    get_config.cache_clear()
    yield
    get_config.cache_clear()


# ---------------------------------------------------------------------------
# get_available_providers()
# ---------------------------------------------------------------------------


def test_get_available_providers_openai_only(monkeypatch):
    """Only OpenAI key set returns a list containing only 'openai'."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import get_available_providers

    providers = get_available_providers()
    assert providers == ["openai"]


def test_get_available_providers_groq_only(monkeypatch):
    """Only Groq key set returns a list containing only 'groq'."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-fake-groq")

    from llm_provider_manager import get_available_providers

    providers = get_available_providers()
    assert providers == ["groq"]


def test_get_available_providers_both(monkeypatch):
    """Both keys set returns a list with both 'openai' and 'groq'."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-fake-groq")

    from llm_provider_manager import get_available_providers

    providers = get_available_providers()
    assert "openai" in providers
    assert "groq" in providers
    assert len(providers) == 2


def test_get_available_providers_none(monkeypatch):
    """No keys set returns an empty list."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import get_available_providers

    providers = get_available_providers()
    assert providers == []


# ---------------------------------------------------------------------------
# validate_provider()
# ---------------------------------------------------------------------------


def test_validate_provider_openai_passes(monkeypatch):
    """validate_provider('openai') returns True when the OpenAI key is set."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-validate-ok")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import validate_provider

    assert validate_provider("openai") is True


def test_validate_provider_groq_passes(monkeypatch):
    """validate_provider('groq') returns True when the Groq key is set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-validate-ok")

    from llm_provider_manager import validate_provider

    assert validate_provider("groq") is True


def test_validate_provider_no_keys_raises(monkeypatch):
    """No keys at all raises Exception with 'No API keys found' message."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import validate_provider

    with pytest.raises(Exception, match="No API keys found"):
        validate_provider("openai")


def test_validate_provider_openai_requested_but_only_groq_set_raises(monkeypatch):
    """Requesting 'openai' when only Groq key is present raises with OPENAI_API_KEY hint."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-only-groq")

    from llm_provider_manager import validate_provider

    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        validate_provider("openai")


def test_validate_provider_groq_requested_but_only_openai_set_raises(monkeypatch):
    """Requesting 'groq' when only OpenAI key is present raises with GROQ_API_KEY hint."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-only-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import validate_provider

    with pytest.raises(Exception, match="GROQ_API_KEY"):
        validate_provider("groq")


def test_validate_provider_case_insensitive_openai(monkeypatch):
    """validate_provider is invoked by load_llm which normalises via provider.lower(),
    but validate_provider itself checks the string as-is against get_available_providers.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-case-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import validate_provider

    # The internal available list uses lowercase keys so uppercase won't match
    with pytest.raises(Exception):
        validate_provider("OPENAI")


# ---------------------------------------------------------------------------
# load_llm() — construction
# ---------------------------------------------------------------------------


@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_openai_constructs_correctly(mock_chat_openai, monkeypatch):
    """load_llm('openai') instantiates ChatOpenAI with values from get_config()."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-construct-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_chat_openai.return_value = MagicMock()

    from llm_provider_manager import load_llm
    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    load_llm("openai")

    mock_chat_openai.assert_called_once()
    call_kwargs = mock_chat_openai.call_args.kwargs
    assert call_kwargs["model"] == cfg.openai_model
    assert call_kwargs["temperature"] == cfg.temperature
    assert call_kwargs["max_tokens"] == cfg.max_tokens
    assert call_kwargs["timeout"] == cfg.llm_timeout


@patch("llm_provider_manager.ChatGroq")
def test_load_llm_groq_constructs_correctly(mock_chat_groq, monkeypatch):
    """load_llm('groq') instantiates ChatGroq with values from get_config()."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-construct-test")
    mock_chat_groq.return_value = MagicMock()

    from llm_provider_manager import load_llm
    from config import AppConfig

    cfg = AppConfig(_env_file=None)
    load_llm("groq")

    mock_chat_groq.assert_called_once()
    call_kwargs = mock_chat_groq.call_args.kwargs
    assert call_kwargs["model"] == cfg.groq_model
    assert call_kwargs["temperature"] == cfg.temperature
    assert call_kwargs["max_tokens"] == cfg.max_tokens
    assert call_kwargs["timeout"] == cfg.llm_timeout


# ---------------------------------------------------------------------------
# load_llm() — caching
# ---------------------------------------------------------------------------


@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_openai_is_cached(mock_chat_openai, monkeypatch):
    """A second call to load_llm('openai') reuses the cached instance."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-cache-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_chat_openai.return_value = MagicMock()

    from llm_provider_manager import load_llm

    result1 = load_llm("openai")
    result2 = load_llm("openai")

    # Constructor called only once
    mock_chat_openai.assert_called_once()
    # Same object returned both times
    assert result1 is result2


@patch("llm_provider_manager.ChatGroq")
def test_load_llm_groq_is_cached(mock_chat_groq, monkeypatch):
    """A second call to load_llm('groq') reuses the cached instance."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-cache-groq")
    mock_chat_groq.return_value = MagicMock()

    from llm_provider_manager import load_llm

    result1 = load_llm("groq")
    result2 = load_llm("groq")

    mock_chat_groq.assert_called_once()
    assert result1 is result2


@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_openai_rebuilds_after_cache_clear(mock_chat_openai, monkeypatch):
    """After clear_llm_cache(), load_llm('openai') constructs a fresh instance."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-rebuild-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_chat_openai.return_value = MagicMock()

    import llm_provider_manager
    from llm_provider_manager import load_llm

    load_llm("openai")
    assert mock_chat_openai.call_count == 1

    llm_provider_manager.clear_llm_cache()

    load_llm("openai")
    assert mock_chat_openai.call_count == 2


@patch("llm_provider_manager.ChatGroq")
def test_load_llm_groq_rebuilds_after_cache_clear(mock_chat_groq, monkeypatch):
    """After clear_llm_cache(), load_llm('groq') constructs a fresh instance."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-rebuild-groq")
    mock_chat_groq.return_value = MagicMock()

    import llm_provider_manager
    from llm_provider_manager import load_llm

    load_llm("groq")
    assert mock_chat_groq.call_count == 1

    llm_provider_manager.clear_llm_cache()

    load_llm("groq")
    assert mock_chat_groq.call_count == 2


# ---------------------------------------------------------------------------
# load_llm() — error paths
# ---------------------------------------------------------------------------


def test_load_llm_invalid_provider_raises_exception(monkeypatch):
    """Passing an unknown provider name raises an Exception.

    validate_provider() checks the provider against the list of keys that are
    actually set ('openai', 'groq'). 'anthropic' is never in that list so it
    raises Exception before the elif chain in load_llm() is reached. The test
    documents this real behaviour rather than the unreachable ValueError branch.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-invalid-prov")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-invalid-prov")

    from llm_provider_manager import load_llm

    with pytest.raises(Exception, match="anthropic"):
        load_llm("anthropic")


@patch(
    "llm_provider_manager.ChatOpenAI", side_effect=RuntimeError("connection refused")
)
def test_load_llm_openai_construction_failure_is_wrapped(mock_chat_openai, monkeypatch):
    """A ChatOpenAI constructor error is caught and re-raised as Exception with context."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fail-openai")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from llm_provider_manager import load_llm

    with pytest.raises(Exception, match="Failed to load OpenAI model"):
        load_llm("openai")


@patch("llm_provider_manager.ChatGroq", side_effect=RuntimeError("groq unreachable"))
def test_load_llm_groq_construction_failure_is_wrapped(mock_chat_groq, monkeypatch):
    """A ChatGroq constructor error is caught and re-raised as Exception with context."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-fail-groq")

    from llm_provider_manager import load_llm

    with pytest.raises(Exception, match="Failed to load Groq model"):
        load_llm("groq")


# ---------------------------------------------------------------------------
# load_llm() — uses config values
# ---------------------------------------------------------------------------


@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_uses_config_temperature(mock_chat_openai, monkeypatch):
    """load_llm reads temperature from get_config(), not a hardcoded value."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-temp-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("TEMPERATURE", "0.3")
    mock_chat_openai.return_value = MagicMock()

    from llm_provider_manager import load_llm

    load_llm("openai")

    call_kwargs = mock_chat_openai.call_args.kwargs
    assert call_kwargs["temperature"] == pytest.approx(0.3)


@patch("llm_provider_manager.ChatOpenAI")
def test_load_llm_openai_provider_case_insensitive(mock_chat_openai, monkeypatch):
    """load_llm('OPENAI') (uppercase) is handled via provider.lower() internally."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-case-open")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_chat_openai.return_value = MagicMock()

    from llm_provider_manager import load_llm

    # validate_provider receives "OPENAI" which won't match lowercase list,
    # so this should raise — documenting the actual behaviour
    with pytest.raises(Exception):
        load_llm("OPENAI")


# ---------------------------------------------------------------------------
# get_provider_info()
# ---------------------------------------------------------------------------


def test_get_provider_info_openai_returns_correct_fields(monkeypatch):
    """get_provider_info('openai') returns a dict with expected metadata keys."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-info-test")

    from llm_provider_manager import get_provider_info

    info = get_provider_info("openai")
    assert isinstance(info, dict)
    assert info.get("name") == "OpenAI GPT-4o"
    assert "speed" in info
    assert "quality" in info
    assert "cost" in info
    assert "description" in info


def test_get_provider_info_groq_returns_correct_fields(monkeypatch):
    """get_provider_info('groq') returns a dict with expected metadata keys."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk-info-test")

    from llm_provider_manager import get_provider_info

    info = get_provider_info("groq")
    assert isinstance(info, dict)
    assert info.get("name") == "Groq Llama 3.1 70B"
    assert "speed" in info
    assert "quality" in info
    assert "cost" in info
    assert "description" in info


def test_get_provider_info_unknown_provider_returns_empty_dict():
    """An unknown provider name returns an empty dict without raising."""
    from llm_provider_manager import get_provider_info

    info = get_provider_info("unknown_provider")
    assert info == {}


def test_get_provider_info_case_insensitive(monkeypatch):
    """get_provider_info uses .lower() so 'OPENAI' resolves to the openai entry."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-case-info")

    from llm_provider_manager import get_provider_info

    info = get_provider_info("OPENAI")
    assert info.get("name") == "OpenAI GPT-4o"


# ---------------------------------------------------------------------------
# clear_llm_cache()
# ---------------------------------------------------------------------------


@patch("llm_provider_manager.ChatOpenAI")
@patch("llm_provider_manager.ChatGroq")
def test_clear_llm_cache_resets_both_globals(mock_groq, mock_openai, monkeypatch):
    """clear_llm_cache() sets both _llm_openai and _llm_groq to None."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-clear-test")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-clear-test")
    mock_openai.return_value = MagicMock()
    mock_groq.return_value = MagicMock()

    import llm_provider_manager

    # Populate the cache
    llm_provider_manager.load_llm("openai")
    llm_provider_manager.load_llm("groq")

    assert llm_provider_manager._llm_openai is not None
    assert llm_provider_manager._llm_groq is not None

    llm_provider_manager.clear_llm_cache()

    assert llm_provider_manager._llm_openai is None
    assert llm_provider_manager._llm_groq is None


def test_clear_llm_cache_is_idempotent():
    """Calling clear_llm_cache() when cache is already empty does not raise."""
    import llm_provider_manager

    # Should not raise when globals are already None
    llm_provider_manager.clear_llm_cache()
    llm_provider_manager.clear_llm_cache()

    assert llm_provider_manager._llm_openai is None
    assert llm_provider_manager._llm_groq is None
