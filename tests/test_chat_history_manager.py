import json
from pathlib import Path
from unittest.mock import MagicMock


def _make_config(path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.chat_history_path = str(path)
    return cfg


# ---------------------------------------------------------------------------
# save_chat_history
# ---------------------------------------------------------------------------


def test_save_creates_json_file(monkeypatch, history_file, set_api_keys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(history_file)
    )

    result = chat_history_manager.save_chat_history(
        question="What is cellulitis?",
        answer="A bacterial infection.",
        provider="openai",
        retrieval_time=0.5,
        llm_time=1.2,
        total_time=1.7,
        pages_retrieved=3,
    )

    assert result is True
    assert history_file.exists()
    data = json.loads(history_file.read_text())
    assert len(data) == 1
    assert data[0]["question"] == "What is cellulitis?"
    assert data[0]["provider"] == "OPENAI"
    assert data[0]["pages_retrieved"] == 3
    assert "performance" in data[0]


def test_save_appends_to_existing(monkeypatch, populated_history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(populated_history_file)
    )

    chat_history_manager.save_chat_history(
        question="New question?",
        answer="New answer.",
        provider="groq",
        retrieval_time=0.3,
        llm_time=0.8,
        total_time=1.1,
        pages_retrieved=2,
    )

    data = json.loads(populated_history_file.read_text())
    assert len(data) == 3
    assert data[-1]["question"] == "New question?"


def test_save_roundtrip_preserves_fields(monkeypatch, history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(history_file)
    )

    chat_history_manager.save_chat_history(
        question="Round trip?",
        answer="Yes.",
        provider="openai",
        retrieval_time=1.0,
        llm_time=2.0,
        total_time=3.0,
        pages_retrieved=7,
    )

    loaded = chat_history_manager.load_chat_history()
    assert loaded[0]["performance"]["retrieval_time"] == 1.0
    assert loaded[0]["performance"]["llm_time"] == 2.0
    assert loaded[0]["performance"]["total_time"] == 3.0


# ---------------------------------------------------------------------------
# load_chat_history
# ---------------------------------------------------------------------------


def test_load_returns_empty_list_when_file_absent(monkeypatch, tmp_path):
    import chat_history_manager

    missing = tmp_path / "nonexistent.json"
    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(missing)
    )

    result = chat_history_manager.load_chat_history()
    assert result == []


def test_load_returns_list_from_file(monkeypatch, populated_history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(populated_history_file)
    )

    result = chat_history_manager.load_chat_history()
    assert len(result) == 2
    assert result[0]["question"] == "What is cellulitis?"


# ---------------------------------------------------------------------------
# clear_chat_history
# ---------------------------------------------------------------------------


def test_clear_removes_file(monkeypatch, populated_history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(populated_history_file)
    )

    result = chat_history_manager.clear_chat_history()

    assert result is True
    assert not populated_history_file.exists()


def test_clear_is_idempotent_when_no_file(monkeypatch, tmp_path):
    import chat_history_manager

    missing = tmp_path / "nonexistent.json"
    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(missing)
    )

    result = chat_history_manager.clear_chat_history()
    assert result is True


# ---------------------------------------------------------------------------
# get_recent_history
# ---------------------------------------------------------------------------


def test_get_recent_history_respects_limit(monkeypatch, populated_history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(populated_history_file)
    )

    result = chat_history_manager.get_recent_history(limit=1)
    assert len(result) == 1
    assert result[0]["question"] == "Describe ameloblastoma."


def test_get_recent_history_empty(monkeypatch, history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(history_file)
    )

    result = chat_history_manager.get_recent_history(limit=5)
    assert result == []


# ---------------------------------------------------------------------------
# get_history_stats
# ---------------------------------------------------------------------------


def test_stats_on_empty_history(monkeypatch, history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(history_file)
    )

    stats = chat_history_manager.get_history_stats()
    assert stats["total_interactions"] == 0
    assert stats["avg_response_time"] == 0
    assert stats["providers_used"] == []
    assert stats["most_recent"] is None


def test_stats_on_populated_history(monkeypatch, populated_history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(populated_history_file)
    )

    stats = chat_history_manager.get_history_stats()
    assert stats["total_interactions"] == 2
    assert stats["avg_response_time"] == round((1.7 + 1.3) / 2, 2)
    assert set(stats["providers_used"]) == {"OPENAI", "GROQ"}
    assert stats["most_recent"] is not None


# ---------------------------------------------------------------------------
# 100-entry cap
# ---------------------------------------------------------------------------


def test_cap_truncates_to_100_entries(monkeypatch, history_file):
    import chat_history_manager

    monkeypatch.setattr(
        chat_history_manager, "get_config", lambda: _make_config(history_file)
    )

    for i in range(101):
        chat_history_manager.save_chat_history(
            question=f"Question {i}",
            answer=f"Answer {i}",
            provider="openai",
            retrieval_time=0.1,
            llm_time=0.1,
            total_time=0.2,
            pages_retrieved=1,
        )

    data = json.loads(history_file.read_text())
    assert len(data) == 100
    assert data[-1]["question"] == "Question 100"
    assert data[0]["question"] == "Question 1"
