# Feature: RAG Evaluation Framework

## Problem Statement
There is currently no systematic way to assess the quality of answers produced by the RAG
pipeline. Developers cannot tell whether answers are faithful to the source textbook,
relevant to the question asked, or complete in covering key points. Without a baseline
quality signal, regressions from model changes, chunking adjustments, or prompt tweaks
go undetected until a user notices a bad answer.

## User Story
As a developer, I want to run a single command that evaluates the RAG system against a
fixed set of oral pathology questions so that I can detect quality regressions and
understand how well the system is performing across three quality dimensions.

## What It Should Do (Acceptance Criteria)
- When `/eval` is run, the system poses each question in the golden question set to the
  RAG pipeline and collects the answer and the retrieved source chunks
- When an answer is collected, an LLM judge scores it on three dimensions:
  - **Faithfulness** (1–5): does the answer accurately reflect the retrieved source chunks
    without adding unsupported claims?
  - **Relevance** (1–5): does the answer directly address what the question asked?
  - **Completeness** (1–5): does the answer cover the key points expected for that question?
- Each score is accompanied by a one-sentence justification written by the LLM judge
- When all questions are evaluated, the system generates a markdown report that includes:
  per-question scores with justifications, per-dimension averages, and an overall
  pass/fail summary based on a configurable threshold
- The report is saved to `eval_report.md` in the project root and its summary
  (averages + pass/fail) is printed to the terminal
- When run as `/eval openai` or `/eval groq`, the specified provider is used for both
  answer generation and LLM judging; when no provider is given, the default provider
  from config is used
- When any question scores below the threshold on any dimension, it is flagged in the
  report with a "FAIL" marker so regressions are immediately visible

## What It Should NOT Do (Constraints)
- Must not modify `rag_system.py`'s `ask_question()` function or any existing RAG
  answer generation behavior — the evaluator is read-only with respect to the pipeline
- Must not call real LLM APIs or FAISS during automated tests — all external calls
  must be mocked
- Must not be imported or executed at app startup — evaluation is a standalone,
  on-demand operation only
- Must not write results to `chat_history.json` — that file is reserved for
  user-facing interactions only
- Must not change temperature settings in the main RAG pipeline — the evaluator
  may use its own temperature for the judge LLM calls

## Files Likely Affected
- `eval_runner.py` — new module: orchestrates the evaluation loop, LLM judge scoring,
  and markdown report generation
- `evals/golden_questions.json` — new: curated question set with expected key points
  for each question (used by the judge to assess completeness)
- `.claude/skills/rag-eval.md` — skill file already referenced in CLAUDE.md; defines
  golden questions, scoring rubric, and report format (to be authored as part of this feature)
- `.claude/commands/eval.md` — command stub already referenced in CLAUDE.md;
  needs full implementation
- `rag_system.py` — called (not modified) to generate answers for each golden question
- `tests/test_eval_runner.py` — new test file covering the evaluation module

## Open Questions
- Should the LLM judge always use the same provider that generated the answer, or should
  it be fixed to a specific model (e.g., always GPT-4o) for consistent scoring across runs?
- How many questions should the initial golden set contain? (10? 20? 50?)
- Should each golden question include a full reference answer, or only a list of
  key points the answer must cover?
- Should evaluation results be appended to a history file across runs to enable
  regression trend tracking, or is a single overwritten report sufficient for v1?
- What is the passing threshold per dimension — e.g., average score ≥ 3.0 out of 5.0?
