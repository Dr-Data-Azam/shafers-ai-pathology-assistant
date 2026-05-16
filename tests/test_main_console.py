from unittest.mock import MagicMock


def _ready_system_info(providers=None):
    return {
        "vector_db_exists": True,
        "available_providers": providers or ["openai"],
        "retriever_cached": True,
        "chat_history_exists": False,
    }


# ---------------------------------------------------------------------------
# print_system_status
# ---------------------------------------------------------------------------


def test_print_system_status_returns_true_when_ready(monkeypatch):
    import main_console

    monkeypatch.setattr(
        main_console, "get_system_info", MagicMock(return_value=_ready_system_info())
    )

    result = main_console.print_system_status()

    assert result is True


def test_print_system_status_returns_false_when_db_missing(monkeypatch):
    import main_console

    monkeypatch.setattr(
        main_console,
        "get_system_info",
        MagicMock(
            return_value={
                "vector_db_exists": False,
                "available_providers": [],
                "retriever_cached": False,
                "chat_history_exists": False,
            }
        ),
    )

    result = main_console.print_system_status()

    assert result is False


def test_print_system_status_returns_false_when_no_providers(monkeypatch):
    import main_console

    monkeypatch.setattr(
        main_console,
        "get_system_info",
        MagicMock(
            return_value={
                "vector_db_exists": True,
                "available_providers": [],
                "retriever_cached": False,
                "chat_history_exists": False,
            }
        ),
    )

    result = main_console.print_system_status()

    assert result is False


# ---------------------------------------------------------------------------
# select_provider
# ---------------------------------------------------------------------------


def test_select_provider_auto_selects_single_provider(monkeypatch):
    import main_console

    mock_input = MagicMock()
    monkeypatch.setattr("builtins.input", mock_input)

    result = main_console.select_provider(["openai"])

    assert result == "openai"
    mock_input.assert_not_called()


def test_select_provider_prompts_when_multiple(monkeypatch):
    import main_console

    monkeypatch.setattr("builtins.input", MagicMock(return_value="1"))
    monkeypatch.setattr(
        "llm_provider_manager.get_provider_info",
        MagicMock(
            return_value={"description": "Fast", "speed": "High", "quality": "Good"}
        ),
    )

    result = main_console.select_provider(["openai", "groq"])

    assert result == "openai"


def test_select_provider_selects_second_option(monkeypatch):
    import main_console

    monkeypatch.setattr("builtins.input", MagicMock(return_value="2"))
    monkeypatch.setattr(
        "llm_provider_manager.get_provider_info",
        MagicMock(
            return_value={"description": "Fast", "speed": "High", "quality": "Good"}
        ),
    )

    result = main_console.select_provider(["openai", "groq"])

    assert result == "groq"


# ---------------------------------------------------------------------------
# show_chat_history
# ---------------------------------------------------------------------------


def test_show_chat_history_prints_nothing_when_empty(monkeypatch, capsys):
    import main_console

    monkeypatch.setattr(main_console, "load_chat_history", MagicMock(return_value=[]))

    main_console.show_chat_history()

    captured = capsys.readouterr()
    assert "No chat history found" in captured.out


def test_show_chat_history_prints_interactions(
    monkeypatch, capsys, populated_history_file
):
    import json
    import main_console

    history = json.loads(populated_history_file.read_text())
    monkeypatch.setattr(
        main_console, "load_chat_history", MagicMock(return_value=history)
    )

    main_console.show_chat_history()

    captured = capsys.readouterr()
    assert "cellulitis" in captured.out.lower()


# ---------------------------------------------------------------------------
# test_both_providers
# ---------------------------------------------------------------------------


def test_both_providers_calls_ask_question_per_provider(monkeypatch):
    import main_console

    mock_ask = MagicMock(
        return_value=(
            "Test answer about cellulitis in great detail here...",
            {
                "documents_retrieved": 3,
                "pages_retrieved": 2,
                "total_time": 1.5,
            },
        )
    )
    monkeypatch.setattr(
        main_console,
        "get_system_info",
        MagicMock(return_value=_ready_system_info(["openai", "groq"])),
    )
    monkeypatch.setattr(
        main_console,
        "get_available_providers",
        MagicMock(return_value=["openai", "groq"]),
    )
    monkeypatch.setattr(main_console, "ask_question", mock_ask)

    main_console.test_both_providers()

    assert mock_ask.call_count == 2
    call_providers = [c.args[1] for c in mock_ask.call_args_list]
    assert "openai" in call_providers
    assert "groq" in call_providers


def test_both_providers_skips_when_system_not_ready(monkeypatch):
    import main_console

    monkeypatch.setattr(
        main_console,
        "get_system_info",
        MagicMock(
            return_value={
                "vector_db_exists": False,
                "available_providers": [],
                "retriever_cached": False,
                "chat_history_exists": False,
            }
        ),
    )
    mock_ask = MagicMock()
    monkeypatch.setattr(main_console, "ask_question", mock_ask)

    main_console.test_both_providers()

    mock_ask.assert_not_called()
