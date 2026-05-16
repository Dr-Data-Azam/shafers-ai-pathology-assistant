# Technical Design: RAG Evaluation Framework

## Summary
Build `eval_runner.py` — a standalone evaluation module that loads a curated golden question
set (`evals/golden_questions.json`), runs each question through the existing `ask_question()`
API, scores answers via an OpenAI GPT-4o judge (always, regardless of generation provider,
temperature=0 for deterministic scoring), detects regressions against the previous run, and
saves a dated markdown report + JSON results file. The `/eval` command is updated to call
`eval_runner.py` directly via CLI. No changes to any existing RAG module.

## Implementation Tasks

- [ ] Task 1: Create evals/golden_questions.json
      What: JSON file with all 20 golden questions, categories, and expected key points
      Where: `evals/golden_questions.json` (new file, new directory)
      How: Extract each question entry from `.claude/skills/rag-eval.md` (all 20 questions +
      expected key points are defined there). Each entry: `{id, category, question,
      expected_key_points}`. Categories: Definition, Classification, Clinical Features,
      Comparison, Edge Cases.

- [ ] Task 2: Create eval_runner.py — pure helper functions
      What: Module with data loading, context retrieval, LLM judge scoring, summary maths,
      regression detection, and report/results generation
      Where: `eval_runner.py` (new file, project root)
      How: Implement these typed functions:
      - `load_golden_questions(path: str) -> list[dict]` — reads JSON, raises `ConfigError`
        if file missing
      - `get_answer_with_context(question: str, provider: str) -> tuple[str, str]` — calls
        `get_retriever()`, `get_comprehensive_context()`, `process_documents_for_context()`
        for context string, then `ask_question(question, provider, save_history=False)` for
        the answer; returns `(answer, context)`
      - `_create_judge_llm() -> ChatOpenAI` — private helper; always instantiates `ChatOpenAI`
        with `model=get_config().openai_model` and `temperature=0`; does NOT use the cached
        `load_llm()` instance; raises `LLMError("openai", ...)` if `OPENAI_API_KEY` unset
      - `score_answer(question: str, answer: str, context: str,
        expected_key_points: list[str]) -> dict` — formats the judge prompt from rag-eval
        skill, invokes `_create_judge_llm()`, parses JSON response into
        `{faithfulness, relevance, completeness, faithfulness_reason, relevance_reason,
        completeness_reason, overall}`; raises `LLMError` on unparseable response
      - `compute_summary(scored_results: list[dict]) -> dict` — averages per dimension +
        overall, pass_rate (% with overall ≥3.5), fail_count (any dimension <2.0)
      - `find_previous_results(glob_pattern: str) -> dict | None` — finds most-recent
        `eval_results_*.json` by filename sort; returns parsed JSON or None
      - `detect_regressions(current: list[dict], previous: dict | None) -> list[dict]` —
        returns list of `{id, question, prev_overall, curr_overall, drop}` where drop >0.5
        or any dimension <2.0 in current
      - `generate_markdown_report(results: list[dict], summary: dict, regressions: list[dict],
        provider: str, date_str: str) -> str` — builds markdown per rag-eval skill template
        (summary table, failures section, full results table)
      - `save_results(results: list[dict], summary: dict, provider: str,
        date_str: str) -> str` — writes `eval_results_<date>.json`, returns filename

- [ ] Task 3: Add run_full_evaluation() + CLI to eval_runner.py
      What: Top-level orchestration function and argparse CLI entry point
      Where: `eval_runner.py` — append to file created in Task 2
      How: `run_full_evaluation(provider: str = "openai") -> dict` — calls each helper in
      sequence: load questions → loop get_answer_with_context + score_answer for each →
      compute_summary → find_previous_results → detect_regressions → generate_markdown_report →
      save_results → write report to `eval_report_<date>.md` → return summary dict.
      Logs progress at INFO level ("Evaluating question N/20 — <question text>").
      `if __name__ == "__main__":` block with argparse: `--provider` (default "openai"),
      prints the summary table to stdout on completion.

- [ ] Task 4: Update .claude/commands/eval.md
      What: Replace the inline Python eval loop with a call to `eval_runner.run_full_evaluation()`
      Where: `.claude/commands/eval.md`
      How: Keep Steps 1–3 (read skill, determine provider, check API key). Add an explicit
      check that `OPENAI_API_KEY` is set (required for the judge regardless of generation
      provider). Replace Steps 4–8 (the inline Python + scoring loop) with a single Bash
      call: `python eval_runner.py --provider <provider>`. Keep Step 9 (print summary to
      user in the exact format defined in the current eval.md).

- [ ] Task 5: Create tests/test_eval_runner.py
      What: Unit tests for all public functions in eval_runner.py
      Where: `tests/test_eval_runner.py` (new file)
      How: Mock all external calls — no real LLM, no real FAISS. Follow project test patterns:
      import inside test functions after monkeypatching; use `tmp_path` for file I/O;
      use `monkeypatch.setattr` to patch module-level names. Key test groups:
      - `load_golden_questions`: happy path (tmp JSON), missing file raises ConfigError
      - `get_answer_with_context`: mock get_retriever, get_comprehensive_context,
        process_documents_for_context, ask_question; verify (answer, context) tuple returned
      - `score_answer`: mock _create_judge_llm → MagicMock with .invoke() returning valid
        JSON; verify all 7 fields; test invalid JSON raises LLMError; test missing
        OPENAI_API_KEY raises LLMError
      - `compute_summary`: pure function; test pass_rate boundary (3.5=pass, 3.49=fail),
        fail_count when any dimension <2.0
      - `detect_regressions`: pure function; drop >0.5 flagged, drop ≤0.5 not, None
        previous returns empty list
      - `generate_markdown_report`: pure function; verify FAIL marker present, regression
        section present when regressions non-empty
      - `run_full_evaluation`: mock load_golden_questions (2 questions), mock
        get_answer_with_context, mock score_answer; monkeypatch output paths to tmp_path;
        verify JSON + report files written

## Files to Modify
| File | What Changes |
|------|-------------|
| `.claude/commands/eval.md` | Steps 4–8 replaced with `python eval_runner.py --provider <provider>` Bash call; add OPENAI_API_KEY check for judge |

## Files to Create
| File | Purpose |
|------|---------|
| `evals/golden_questions.json` | 20 curated oral-pathology questions with expected key points |
| `eval_runner.py` | Standalone evaluation module + CLI entry point |
| `tests/test_eval_runner.py` | Unit tests for eval_runner.py (80%+ coverage target) |

## New Dependencies
None. `langchain-openai`, `langchain-groq`, and `pydantic-settings` are already in the project.

## Breaking Changes
None. `rag_system.py`, `llm_provider_manager.py`, `config.py`, and all other existing modules
are unchanged.

## Data Flow
```
/eval openai
  → eval.md command
  → python eval_runner.py --provider openai
  → load_golden_questions("evals/golden_questions.json")       # 20 questions
  → for each question:
      get_answer_with_context(q, "openai")
        → get_retriever() + get_comprehensive_context()         # FAISS retrieval
        → ask_question(q, "openai", save_history=False)         # LLM answer
        → returns (answer, context)
      score_answer(q, answer, context, key_points)
        → _create_judge_llm()                                   # always OpenAI GPT-4o, temp=0
        → judge_llm.invoke(judge_prompt)                        # LLM scoring
        → parse JSON → {faithfulness, relevance, completeness, ...}
  → compute_summary(scored_results)
  → find_previous_results("eval_results_*.json")
  → detect_regressions(current, previous)
  → generate_markdown_report(...)
  → save_results(...)  → eval_results_<date>.json
  → write report      → eval_report_<date>.md
  → print summary to stdout
```

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| `load_golden_questions` happy path | Unit | `tmp_path` JSON file |
| `load_golden_questions` missing file | Unit | pass nonexistent path |
| `get_answer_with_context` | Unit | `monkeypatch.setattr` on eval_runner.get_retriever, get_comprehensive_context, process_documents_for_context, ask_question |
| `score_answer` valid JSON | Unit | mock `eval_runner._create_judge_llm`; `.invoke()` returns JSON string |
| `score_answer` invalid JSON | Unit | `.invoke()` returns `"not json"` → assert LLMError |
| `compute_summary` boundaries | Unit | No mocks — pure function |
| `detect_regressions` | Unit | No mocks — pure function |
| `generate_markdown_report` | Unit | No mocks — pure function |
| `run_full_evaluation` | Unit | Mock load_golden_questions, get_answer_with_context, score_answer; monkeypatch output paths to tmp_path |

Minimum coverage target: 80% on `eval_runner.py`.
