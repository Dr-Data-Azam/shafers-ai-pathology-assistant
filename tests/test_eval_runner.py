"""Unit tests for eval_runner.py — all external calls are mocked."""

import json

import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scores(**kwargs) -> dict:
    """Return a valid judge score dict with sensible defaults."""
    base = {
        "faithfulness": 4,
        "relevance": 5,
        "completeness": 4,
        "faithfulness_reason": "Claims are supported by the context.",
        "relevance_reason": "Directly answers the question asked.",
        "completeness_reason": "All expected key points are present.",
        "overall": 4.33,
    }
    base.update(kwargs)
    return base


def _make_result(
    id: int = 1,
    question: str = "What is leukoplakia?",
    category: str = "Definition",
    **score_kwargs,
) -> dict:
    """Return a scored result dict as produced by run_full_evaluation's loop."""
    result = {"id": id, "question": question, "category": category}
    result.update(_make_scores(**score_kwargs))
    return result


def _make_mock_config(**kwargs):
    cfg = MagicMock()
    cfg.openai_model = "gpt-4o"
    cfg.openai_api_key = "sk-test-openai"
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------------------
# load_golden_questions
# ---------------------------------------------------------------------------


def test_load_golden_questions_returns_list(tmp_path):
    import eval_runner

    questions = [
        {
            "id": 1,
            "question": "What is leukoplakia?",
            "expected_key_points": ["white patch"],
        }
    ]
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(questions), encoding="utf-8")

    result = eval_runner.load_golden_questions(str(path))

    assert result == questions


def test_load_golden_questions_raises_config_error_when_missing(tmp_path):
    import eval_runner
    from exceptions import ConfigError

    with pytest.raises(ConfigError, match="not found"):
        eval_runner.load_golden_questions(str(tmp_path / "nonexistent.json"))


# ---------------------------------------------------------------------------
# get_answer_with_context
# ---------------------------------------------------------------------------


def test_get_answer_with_context_returns_answer_and_context(monkeypatch):
    import eval_runner

    monkeypatch.setattr(
        eval_runner, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        eval_runner, "get_comprehensive_context", MagicMock(return_value=[MagicMock()])
    )
    monkeypatch.setattr(
        eval_runner,
        "process_documents_for_context",
        MagicMock(return_value=("retrieved context", {"Page 5": ["x"]})),
    )
    monkeypatch.setattr(
        eval_runner,
        "ask_question",
        MagicMock(return_value=("The answer text", {"provider": "OPENAI"})),
    )

    answer, context = eval_runner.get_answer_with_context(
        "What is leukoplakia?", "openai"
    )

    assert answer == "The answer text"
    assert context == "retrieved context"


def test_get_answer_with_context_passes_save_history_false(monkeypatch):
    import eval_runner

    mock_ask = MagicMock(return_value=("answer", {}))
    monkeypatch.setattr(
        eval_runner, "get_retriever", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        eval_runner, "get_comprehensive_context", MagicMock(return_value=[])
    )
    monkeypatch.setattr(
        eval_runner,
        "process_documents_for_context",
        MagicMock(return_value=("ctx", {})),
    )
    monkeypatch.setattr(eval_runner, "ask_question", mock_ask)

    eval_runner.get_answer_with_context("question", "groq")

    mock_ask.assert_called_once_with("question", provider="groq", save_history=False)


# ---------------------------------------------------------------------------
# score_answer
# ---------------------------------------------------------------------------


def _make_mock_llm(content: str) -> MagicMock:
    """Return a mock LLM whose .invoke() returns a response with the given content."""
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    return mock_llm


def test_score_answer_returns_all_required_fields():
    import eval_runner

    result = eval_runner.score_answer(
        "q?",
        "answer",
        "context",
        ["key point"],
        judge_llm=_make_mock_llm(json.dumps(_make_scores())),
    )

    required = {
        "faithfulness",
        "relevance",
        "completeness",
        "faithfulness_reason",
        "relevance_reason",
        "completeness_reason",
        "overall",
    }
    assert required == required & result.keys()


def test_score_answer_strips_markdown_fences():
    import eval_runner

    fenced = "```json\n" + json.dumps(_make_scores()) + "\n```"

    result = eval_runner.score_answer(
        "q?",
        "answer",
        "context",
        ["key point"],
        judge_llm=_make_mock_llm(fenced),
    )

    assert result["faithfulness"] == 4


def test_score_answer_raises_llm_error_on_invalid_json():
    import eval_runner
    from exceptions import LLMError

    with pytest.raises(LLMError, match="unparseable"):
        eval_runner.score_answer(
            "q?",
            "answer",
            "context",
            ["key"],
            judge_llm=_make_mock_llm("not valid json at all"),
        )


def test_score_answer_raises_llm_error_on_missing_fields():
    import eval_runner
    from exceptions import LLMError

    with pytest.raises(LLMError, match="missing required fields"):
        eval_runner.score_answer(
            "q?",
            "answer",
            "context",
            ["key"],
            judge_llm=_make_mock_llm(json.dumps({"faithfulness": 4})),
        )


def test_score_answer_raises_when_openai_key_missing(monkeypatch):
    import eval_runner
    from exceptions import LLMError

    monkeypatch.setattr(
        eval_runner,
        "get_config",
        MagicMock(return_value=_make_mock_config(openai_api_key=None)),
    )

    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        eval_runner.score_answer("q?", "answer", "context", ["key"])


# ---------------------------------------------------------------------------
# compute_summary
# ---------------------------------------------------------------------------


def test_compute_summary_pass_rate_boundary_at_3_5():
    import eval_runner

    results = [
        _make_result(overall=3.5),  # PASS (>= 3.5)
        _make_result(id=2, overall=3.49),  # FAIL (< 3.5)
    ]

    summary = eval_runner.compute_summary(results)

    assert summary["questions_evaluated"] == 2
    assert summary["pass_rate"] == 50.0


def test_compute_summary_all_pass_when_all_above_threshold():
    import eval_runner

    results = [_make_result(id=i, overall=4.0) for i in range(1, 5)]

    summary = eval_runner.compute_summary(results)

    assert summary["pass_rate"] == 100.0


def test_compute_summary_fail_count_when_dimension_below_2():
    import eval_runner

    results = [
        _make_result(faithfulness=1.5, overall=3.2),  # critical failure
        _make_result(id=2, overall=4.0),  # no critical failure
    ]

    summary = eval_runner.compute_summary(results)

    assert summary["fail_count"] == 1


def test_compute_summary_empty_returns_zeros():
    import eval_runner

    summary = eval_runner.compute_summary([])

    assert summary["questions_evaluated"] == 0
    assert summary["overall_avg"] == 0.0
    assert summary["pass_rate"] == 0.0
    assert summary["fail_count"] == 0


# ---------------------------------------------------------------------------
# find_previous_results
# ---------------------------------------------------------------------------


def test_find_previous_results_returns_most_recent(tmp_path, monkeypatch):
    import eval_runner

    monkeypatch.chdir(tmp_path)
    old = {"date": "2026-05-01", "provider": "openai", "questions": []}
    new = {"date": "2026-05-15", "provider": "openai", "questions": []}
    (tmp_path / "eval_results_2026-05-01.json").write_text(json.dumps(old))
    (tmp_path / "eval_results_2026-05-15.json").write_text(json.dumps(new))

    result = eval_runner.find_previous_results("eval_results_*.json")

    assert result["date"] == "2026-05-15"


def test_find_previous_results_returns_none_when_no_files(tmp_path, monkeypatch):
    import eval_runner

    monkeypatch.chdir(tmp_path)

    result = eval_runner.find_previous_results("eval_results_*.json")

    assert result is None


# ---------------------------------------------------------------------------
# detect_regressions
# ---------------------------------------------------------------------------


def test_detect_regressions_flags_drop_above_threshold():
    import eval_runner

    current = [_make_result(overall=3.0)]
    previous = {"questions": [{"id": 1, "overall": 4.0}]}

    regressions = eval_runner.detect_regressions(current, previous)

    assert len(regressions) == 1
    assert regressions[0]["drop"] == 1.0


def test_detect_regressions_ignores_small_drop():
    import eval_runner

    current = [_make_result(overall=3.8)]
    previous = {"questions": [{"id": 1, "overall": 4.0}]}

    regressions = eval_runner.detect_regressions(current, previous)

    assert regressions == []


def test_detect_regressions_returns_empty_when_previous_is_none():
    import eval_runner

    current = [_make_result(overall=4.0)]

    regressions = eval_runner.detect_regressions(current, None)

    assert regressions == []


def test_detect_regressions_flags_critical_dimension():
    import eval_runner

    # No score drop, but faithfulness fell below 2.0
    current = [_make_result(faithfulness=1.5, overall=3.5)]
    previous = {"questions": [{"id": 1, "overall": 3.5}]}

    regressions = eval_runner.detect_regressions(current, previous)

    assert len(regressions) == 1
    assert regressions[0]["critical"] is True
    assert regressions[0]["drop"] == 0.0  # clamped — no negative values


# ---------------------------------------------------------------------------
# generate_markdown_report
# ---------------------------------------------------------------------------


def test_generate_markdown_report_shows_fail_verdict_below_threshold(monkeypatch):
    import eval_runner

    monkeypatch.setattr(
        eval_runner, "get_config", MagicMock(return_value=_make_mock_config())
    )
    results = [_make_result(id=i, overall=2.5) for i in range(1, 6)]
    summary = eval_runner.compute_summary(results)

    report = eval_runner.generate_markdown_report(
        results, summary, [], "openai", "2026-05-16"
    )

    assert "Verdict: FAIL" in report


def test_generate_markdown_report_shows_pass_verdict_above_threshold(monkeypatch):
    import eval_runner

    monkeypatch.setattr(
        eval_runner, "get_config", MagicMock(return_value=_make_mock_config())
    )
    results = [_make_result(id=i, overall=4.5) for i in range(1, 11)]
    summary = eval_runner.compute_summary(results)

    report = eval_runner.generate_markdown_report(
        results, summary, [], "openai", "2026-05-16"
    )

    assert "Verdict: PASS" in report


def test_generate_markdown_report_includes_regression_table(monkeypatch):
    import eval_runner

    monkeypatch.setattr(
        eval_runner, "get_config", MagicMock(return_value=_make_mock_config())
    )
    results = [_make_result(overall=4.0)]
    summary = eval_runner.compute_summary(results)
    regressions = [
        {
            "id": 1,
            "question": "What is leukoplakia?",
            "prev_overall": 5.0,
            "curr_overall": 4.0,
            "drop": 1.0,
        }
    ]

    report = eval_runner.generate_markdown_report(
        results, summary, regressions, "openai", "2026-05-16"
    )

    assert "Regressions vs Last Run" in report
    assert "What is leukoplakia?" in report


def test_generate_markdown_report_no_regressions_message(monkeypatch):
    import eval_runner

    monkeypatch.setattr(
        eval_runner, "get_config", MagicMock(return_value=_make_mock_config())
    )
    results = [_make_result(overall=4.0)]
    summary = eval_runner.compute_summary(results)

    report = eval_runner.generate_markdown_report(
        results, summary, [], "openai", "2026-05-16"
    )

    assert "No regressions detected" in report


# ---------------------------------------------------------------------------
# save_results
# ---------------------------------------------------------------------------


def test_save_results_writes_json_with_correct_structure(tmp_path):
    import eval_runner

    results = [_make_result()]
    summary = {"questions_evaluated": 1, "overall_avg": 4.33}

    filename = eval_runner.save_results(
        results, summary, "openai", "2026-05-16", output_dir=tmp_path
    )

    saved = tmp_path / filename
    assert saved.exists()
    payload = json.loads(saved.read_text(encoding="utf-8"))
    assert payload["provider"] == "openai"
    assert payload["date"] == "2026-05-16"
    assert len(payload["questions"]) == 1
    assert "summary" in payload


# ---------------------------------------------------------------------------
# run_full_evaluation
# ---------------------------------------------------------------------------


def test_run_full_evaluation_returns_summary_and_writes_files(
    tmp_path, monkeypatch, set_api_keys
):
    import eval_runner

    questions = [
        {
            "id": 1,
            "category": "Definition",
            "question": "What is leukoplakia?",
            "expected_key_points": ["white patch"],
        },
        {
            "id": 2,
            "category": "Definition",
            "question": "Define ameloblastoma.",
            "expected_key_points": ["benign"],
        },
    ]
    monkeypatch.setattr(
        eval_runner, "load_golden_questions", MagicMock(return_value=questions)
    )
    monkeypatch.setattr(
        eval_runner,
        "get_answer_with_context",
        MagicMock(return_value=("Answer text.", "Context text.")),
    )
    monkeypatch.setattr(
        eval_runner, "score_answer", MagicMock(return_value=_make_scores())
    )
    monkeypatch.setattr(
        eval_runner, "_create_judge_llm", MagicMock(return_value=MagicMock())
    )

    result = eval_runner.run_full_evaluation(provider="openai", output_dir=tmp_path)

    assert result["questions_evaluated"] == 2
    assert result["pass_rate"] == 100.0
    assert result["regressions"] == 0
    assert len(list(tmp_path.glob("eval_results_*.json"))) == 1
    assert len(list(tmp_path.glob("eval_report_*.md"))) == 1


def test_run_full_evaluation_passes_provider_to_get_answer(
    tmp_path, monkeypatch, set_api_keys
):
    import eval_runner

    questions = [
        {
            "id": 1,
            "category": "Definition",
            "question": "What is leukoplakia?",
            "expected_key_points": ["white patch"],
        }
    ]
    mock_get_answer = MagicMock(return_value=("answer", "context"))
    monkeypatch.setattr(
        eval_runner, "load_golden_questions", MagicMock(return_value=questions)
    )
    monkeypatch.setattr(eval_runner, "get_answer_with_context", mock_get_answer)
    monkeypatch.setattr(
        eval_runner, "score_answer", MagicMock(return_value=_make_scores())
    )
    monkeypatch.setattr(
        eval_runner, "_create_judge_llm", MagicMock(return_value=MagicMock())
    )

    eval_runner.run_full_evaluation(provider="groq", output_dir=tmp_path)

    mock_get_answer.assert_called_once_with("What is leukoplakia?", "groq")
