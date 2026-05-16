# Implementation Summary: RAG Evaluation Framework

## Tasks Completed

- [x] Task 1: Create `evals/golden_questions.json` — 20 curated oral-pathology questions across 5 categories with expected key points
- [x] Task 2: Create `eval_runner.py` — pure helper functions (load, retrieve, score, summarise, detect regressions, report, save)
- [x] Task 3: Add `run_full_evaluation()` + argparse CLI to `eval_runner.py`
- [x] Task 4: Update `.claude/commands/eval.md` — replaced inline Python loop with `python eval_runner.py --provider <provider>` call
- [x] Task 5: Create `tests/test_eval_runner.py` — 26 unit tests, all mocked, 92% coverage on `eval_runner.py`

## Files Created and Modified

| File | Status | Purpose |
|------|--------|---------|
| `evals/golden_questions.json` | Created | 20 golden questions with categories and expected key points |
| `eval_runner.py` | Created | Standalone evaluation module + CLI entry point |
| `tests/test_eval_runner.py` | Created | 26 unit tests covering all public functions |
| `.claude/commands/eval.md` | Modified | Replaced 9-step inline eval loop with 5-step delegating command |
| `.gitignore` | Modified | Eval output files intentionally NOT ignored — committed as regression baseline |

## Test Results

```
Tests run:   191
Passed:      191
Failed:      0
Coverage:    81% (total); 92% on eval_runner.py
```

Run time: ~17 seconds.

## Key Implementation Decisions

**Judge always OpenAI GPT-4o (temperature=0), regardless of generation provider.**
Using the same provider as judge and generator creates self-evaluation bias and makes scores incomparable across runs (a weak Llama 8B judging itself vs. GPT-4o). Fixing the judge to one provider ensures regression detection works correctly.

**Judge LLM instantiated once before the scoring loop.**
`run_full_evaluation()` calls `_create_judge_llm()` once and passes it to every `score_answer()` call via the `judge_llm=` parameter. This avoids 20 redundant instantiations and surfaces a missing API key before the loop starts rather than failing mid-run.

**Context retrieved independently from the answer.**
`ask_question()` does not return the retrieved context, so `get_answer_with_context()` calls `get_retriever()` + `get_comprehensive_context()` + `process_documents_for_context()` directly alongside `ask_question()`. Both share the cached retriever, so FAISS loads only once.

**`_PROJECT_ROOT = pathlib.Path(__file__).parent` for all file I/O.**
All default output paths are anchored to the module's directory, not the caller's cwd. This keeps eval output stable regardless of where the script is invoked.

**Eval output files committed (not gitignored).**
`eval_results_*.json` and `eval_report_*.md` are tracked in git. `find_previous_results()` uses `glob.glob()` on the filesystem — on a fresh clone there would be no baseline and regression detection would always return empty. Committing the dated results files keeps the regression baseline intact across clones and lets the git history show the quality trajectory alongside RAG changes.

**Sentinel-based prompt template instead of `str.format()`.**
The judge prompt uses `__QUESTION__`, `__KEY_POINTS__`, `__ANSWER__`, `__CONTEXT__` sentinels replaced via `str.replace()`. This avoids brace-character KeyErrors when retrieved context or generated answers contain `{...}` text (a real risk with medical content), and removes a prompt injection surface where document content mimicking Python format fields could corrupt the prompt.

**`output_dir` parameter on `save_results()` and `run_full_evaluation()`.**
Added to allow tests to redirect file writes to `tmp_path` without `monkeypatch.chdir()`. Avoids cwd-dependent test flakiness.

**Negative drop clamped to 0.0, `critical` boolean added.**
`detect_regressions()` stores `drop=max(drop, 0.0)` so improved scores never show negative drops. A `critical=True` flag is added for dimension-level failures independent of the overall score. The report renders these as "CRIT" in the drop column.

## Deviations from Tech Spec

**`score_answer()` accepts an optional `judge_llm` parameter (not in original spec).**
Added to enable judge reuse across the scoring loop. The original spec called `_create_judge_llm()` inside `score_answer()` on every call; the approved code-reviewer fix moved creation to the caller.

**`run_full_evaluation()` accepts `questions_path` and `output_dir` parameters (not in original spec).**
`output_dir` enables test isolation. `questions_path` lets callers override the default golden questions path for custom evaluation sets.

**Prompt template uses sentinel replacement instead of `str.format()` (post-spec security fix).**
Applied after security review to eliminate brace-character crash risk and reduce prompt injection surface from retrieved context.

**`_create_judge_llm()` passes `api_key=cfg.openai_api_key` explicitly (post-spec security fix).**
Ensures the validated key from config is used directly rather than relying on ambient env var, which could fail in containers where env vars are stripped after config is cached.

**Raw LLM output omitted from `LLMError` message (post-spec security fix).**
The original implementation embedded the first 200 chars of raw judge output in the exception message. Changed to `"Judge returned unparseable JSON (N chars)."` with the full raw value logged at DEBUG level only.
