# Code Review: RAG Evaluation Framework
Date:     2026-05-16
Branch:   feature/rag-evaluation
Reviewer: code-reviewer agent

CODE REVIEW — RAG Evaluation Framework
Branch: feature/rag-evaluation
Spec:   specs/06-rag-evaluation/tech-spec.md
Files:  4 changed (3 new, 1 modified)

VERDICT: APPROVED WITH COMMENTS

---
ISSUES
------

[SHOULD FIX] eval_runner.py:score_answer (line 101)
What: _create_judge_llm() is called on every invocation of score_answer(), instantiating
      a new ChatOpenAI object for every one of the 20 golden questions in a single run.
Why:  Creating 20 ChatOpenAI instances per evaluation run is wasteful. The object is
      stateless between calls — only the prompt changes. More importantly, _create_judge_llm()
      calls get_config() and performs the OPENAI_API_KEY guard check 20 times per run.
      If the key were somehow revoked mid-run the error message would appear on question N
      rather than at startup, which makes diagnosis confusing.
Fix:  Accept an optional `judge_llm` parameter (defaulting to None) and create it once
      in run_full_evaluation() before the loop, then pass it through. Alternatively,
      call _create_judge_llm() once in run_full_evaluation() and pass the instance into
      score_answer() as a parameter. This keeps the function unit-testable and eliminates
      redundant object construction.

[SHOULD FIX] eval_runner.py:run_full_evaluation (line 364)
What: find_previous_results("eval_results_*.json") uses a relative glob pattern.
      The function runs correctly only when the working directory is the project root.
Why:  If this module is ever imported from a test or a sub-directory context where
      monkeypatch.chdir() has not been applied, the glob silently finds no files and
      returns None, so regressions are never detected. The test for find_previous_results
      correctly uses monkeypatch.chdir(tmp_path), but run_full_evaluation() itself has
      no such guard. save_results() and the report write also use bare filenames with
      the same implicit-cwd assumption.
Fix:  Resolve the paths relative to __file__ at module level, or accept an
      output_dir parameter in run_full_evaluation(). A minimal fix is:
        import pathlib
        _PROJECT_ROOT = pathlib.Path(__file__).parent
      then use str(_PROJECT_ROOT / "eval_results_*.json") for the glob and
      _PROJECT_ROOT / filename for writes. The tests already use monkeypatch.chdir()
      so this would not break them.

[SHOULD FIX] eval_runner.py:detect_regressions (line 193)
What: The drop value can be negative (i.e. the score improved) and will still be
      included in the regression dict if critical is True. In the regression table in
      generate_markdown_report (line 255), a negative drop is displayed as-is (e.g.
      "drop: -0.3") with no visual indicator that the score actually improved.
Why:  A question with faithfulness=1.5 but an improved overall score will appear in the
      regressions table with a negative drop, which is confusing for the reader trying
      to triage quality issues. The spec says detect regressions where "drop >0.5 OR
      any dimension <2.0" — the critical flag is correct — but the displayed drop value
      should be clamped to 0 when the overall score did not actually drop.
Fix:  In the appended regression dict, use max(drop, 0.0) for the "drop" field, or add
      a separate "critical" boolean field so the report can render it distinctly (e.g.
      "CRIT" instead of a negative number in the Drop column).

[CONSIDER] eval_runner.py:__main__ block (lines 385-386)
What: The __main__ block imports get_config and configure_logging from config, but
      get_config is already imported at module level (line 10). The re-import inside
      __main__ is redundant.
Why:  Not a bug, but it is confusing — a reader might assume the module-level import
      and the __main__ import serve different purposes. Ruff may flag the duplicate
      import depending on configuration.
Fix:  Remove the duplicate `from config import configure_logging, get_config` line
      inside the __main__ block. configure_logging is the only symbol that actually
      needs adding there.

[CONSIDER] tests/test_eval_runner.py:test_score_answer_raises_when_openai_key_missing (line 214)
What: This test patches get_config at the eval_runner module level but does NOT patch
      _create_judge_llm. The test therefore exercises the real _create_judge_llm()
      code path (which calls get_config() internally) — which is correct. However,
      because conftest.py's clear_config_cache fixture calls get_config.cache_clear()
      before and after every test, patching eval_runner.get_config only works if
      eval_runner imported get_config directly (which it did). This is fine as written,
      but worth noting: if _create_judge_llm is ever refactored to call
      config.get_config() via module reference instead of the local binding, this test
      will silently stop testing the guard.
Fix:  No action required. Documenting for awareness.

[CONSIDER] eval_runner.py:generate_markdown_report (line 220)
What: generate_markdown_report calls get_config() to obtain cfg.openai_model for the
      report header line. This is the only reason a pure-report-builder function needs
      a config dependency, which makes it harder to unit test without mocking get_config.
Why:  The openai_model name is already known at call time — it comes from
      _create_judge_llm(), which is called during scoring. It could instead be passed
      as a parameter (e.g. judge_model: str).
Fix:  Add a judge_model: str parameter and remove the get_config() call. The caller
      (run_full_evaluation) can pass get_config().openai_model once. This makes
      generate_markdown_report a truly pure function.

---
POSITIVES
---------
1. The JUDGE_PROMPT_TEMPLATE correctly uses {{ / }} escaping for literal braces in the
   .format() call (lines 21-42). This is a subtle correctness detail that is easy to
   miss, and it is handled exactly right.

2. score_answer() validates that all 7 required keys are present in the parsed JSON
   (lines 117-131) and raises a typed LLMError with a precise message. This is the
   right level of defensiveness for an LLM-driven pipeline where the judge may silently
   drop fields rather than return invalid JSON.

3. Test coverage is thorough for the pure functions (compute_summary, detect_regressions,
   generate_markdown_report) with boundary-value tests at the exact thresholds stated
   in the spec (3.5 pass/fail, 0.5 regression drop, 2.0 critical failure). The
   find_previous_results tests correctly use monkeypatch.chdir() to isolate file system
   state rather than relying on the actual project directory.

---
SUMMARY
-------
The implementation matches all five tasks in the tech spec: the golden questions file is
complete (20 questions, correct categories and key points), eval_runner.py implements
every specified function with correct type hints and typed exceptions, the eval.md command
was simplified to delegate to the CLI as specified, and the 28 tests cover all public
functions including error paths. The three [SHOULD FIX] issues are quality concerns — a
per-question LLM instantiation cost, an implicit cwd dependency that could cause silent
failures outside the project root, and a misleading negative "drop" value in regression
output — none of which block correctness in the standard execution path. No new
dependencies are introduced and no existing modules were modified.
