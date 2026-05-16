import sys
import pytest
from unittest.mock import MagicMock


class MockSessionState:
    """Dict-backed session state that supports both attribute and 'in' access."""

    def __init__(self):
        self._data = {}

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getattr__(self, key: str):
        if key.startswith("_"):
            return object.__getattribute__(self, key)
        return self._data.get(key)

    def __setattr__(self, key: str, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value


def _build_mock_st() -> MagicMock:
    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    return mock_st


@pytest.fixture
def mock_st():
    return _build_mock_st()


@pytest.fixture(autouse=True)
def isolate_streamlit_app():
    """Remove streamlit_app from sys.modules so each test gets a fresh import."""
    sys.modules.pop("streamlit_app", None)
    yield
    sys.modules.pop("streamlit_app", None)


# ---------------------------------------------------------------------------
# initialize_session_state
# ---------------------------------------------------------------------------


def test_initialize_session_state_sets_chat_history(mock_st, monkeypatch):
    mock_st.session_state = MockSessionState()
    sys.modules["streamlit"] = mock_st

    mock_providers = MagicMock(return_value=["openai"])
    monkeypatch.setattr("llm_provider_manager.get_available_providers", mock_providers)

    import streamlit_app

    streamlit_app.initialize_session_state()

    assert "chat_history" in mock_st.session_state._data
    assert mock_st.session_state.chat_history == []


def test_initialize_session_state_sets_provider_from_available(mock_st, monkeypatch):
    mock_st.session_state = MockSessionState()
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "llm_provider_manager.get_available_providers", MagicMock(return_value=["groq"])
    )

    import streamlit_app

    streamlit_app.initialize_session_state()

    assert mock_st.session_state.current_provider == "groq"


def test_initialize_session_state_provider_none_when_no_providers(mock_st, monkeypatch):
    mock_st.session_state = MockSessionState()
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "llm_provider_manager.get_available_providers", MagicMock(return_value=[])
    )

    import streamlit_app

    streamlit_app.initialize_session_state()

    assert mock_st.session_state.current_provider is None


def test_initialize_session_state_does_not_overwrite_existing(mock_st, monkeypatch):
    state = MockSessionState()
    state.chat_history = [{"question": "existing"}]
    state.current_provider = "openai"
    state.system_initialized = True
    mock_st.session_state = state
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "llm_provider_manager.get_available_providers", MagicMock(return_value=["groq"])
    )

    import streamlit_app

    streamlit_app.initialize_session_state()

    assert mock_st.session_state.chat_history == [{"question": "existing"}]
    assert mock_st.session_state.current_provider == "openai"


# ---------------------------------------------------------------------------
# check_system_status
# ---------------------------------------------------------------------------


def test_check_system_status_returns_true_when_ready(mock_st, monkeypatch):
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "rag_system.get_system_info",
        MagicMock(
            return_value={"vector_db_exists": True, "available_providers": ["openai"]}
        ),
    )

    import streamlit_app

    result = streamlit_app.check_system_status()

    assert result is True


def test_check_system_status_returns_false_when_db_missing(mock_st, monkeypatch):
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "rag_system.get_system_info",
        MagicMock(
            return_value={"vector_db_exists": False, "available_providers": ["openai"]}
        ),
    )

    import streamlit_app

    result = streamlit_app.check_system_status()

    assert result is False
    mock_st.error.assert_called_once()


def test_check_system_status_returns_false_when_no_providers(mock_st, monkeypatch):
    sys.modules["streamlit"] = mock_st

    monkeypatch.setattr(
        "rag_system.get_system_info",
        MagicMock(return_value={"vector_db_exists": True, "available_providers": []}),
    )

    import streamlit_app

    result = streamlit_app.check_system_status()

    assert result is False
    mock_st.error.assert_called_once()


# ---------------------------------------------------------------------------
# render_sidebar
# ---------------------------------------------------------------------------


def test_render_sidebar_calls_get_history_stats(mock_st, monkeypatch):
    sys.modules["streamlit"] = mock_st
    mock_st.sidebar.__enter__ = MagicMock(return_value=mock_st.sidebar)
    mock_st.sidebar.__exit__ = MagicMock(return_value=False)

    mock_stats = MagicMock(
        return_value={"total_interactions": 5, "avg_response_time": 1.2}
    )
    monkeypatch.setattr("chat_history_manager.get_history_stats", mock_stats)

    import streamlit_app

    streamlit_app.render_sidebar()

    mock_stats.assert_called_once()
