# Security Review: RAG Evaluation Framework
Date:     2026-05-16
Branch:   feature/rag-evaluation
Reviewer: security-reviewer agent

SECURITY REVIEW — RAG Evaluation Framework
Branch: feature/rag-evaluation

VERDICT: REVIEW NOTES

---
FINDINGS
--------

[MEDIUM] Prompt Injection: eval_runner.py:score_answer() (lines 103-108)
Risk:   The FAISS-retrieved context and the RAG-generated answer are embedded
        verbatim into the judge prompt via str.format(). A document in the
        textbook index that contains text mimicking the judge prompt's
        JSON schema (e.g., '{"faithfulness": 5, ...}') could cause the judge
        to output a forged score instead of a genuine evaluation. Because the
        judge prompt uses Python str.format() with named placeholders, any
        brace characters { or } in the context or answer will raise a
        KeyError or be silently misinterpreted as format-spec tokens.
Vector: A poisoned chunk in vectorDB/ (or a crafted answer from the RAG
        pipeline) that contains literal { or } characters, or that includes
        text designed to override the judge's JSON-only instruction, could
        corrupt scores or produce a KeyError at runtime.
Fix:    Use a LangChain PromptTemplate (or at minimum escape brace
        characters in the substituted values) rather than raw str.format().
        Also add a length guard — the context is already capped at 3000 chars
        via _JUDGE_CONTEXT_LIMIT, but answer and question have no cap.
        Consider capping answer at ~2000 chars and question at 500 chars
        before substitution.

[MEDIUM] LLM Judge Response Reflected in LLMError: eval_runner.py:score_answer() (line 122)
Risk:   When the judge returns unparseable output, the first 200 characters
        of the raw LLM response are embedded in the LLMError message:
        f"Judge returned unparseable JSON: {raw[:200]}"
        If the judge response happens to echo back injected content from the
        retrieved context (e.g., a path, internal identifier, or sensitive
        string), that content surfaces in the exception message. Depending on
        how the caller surfaces LLMError (e.g., a future Streamlit integration
        or CI log), this could leak unexpected content into visible output.
Vector: Adversarially crafted content in the FAISS index that causes the
        judge to emit non-JSON output. The raw content is then logged and
        raised as an exception message.
Fix:    Replace the raw substring with a generic token count or a sanitised
        placeholder: f"Judge returned unparseable output ({len(raw)} chars)."
        Log the full raw value at DEBUG level only, gated on a developer-mode
        flag, rather than embedding it in the exception message.

[LOW] eval_results_*.json Not Protected by .gitignore: project root
Risk:   The dated JSON results files written by save_results() to the project
        root include the full system answer for every golden question and the
        per-question judge reasoning. While this is evaluation metadata, not
        API credentials, accidentally committing these files could expose
        details about retrieval quality or internal reasoning that would be
        better kept off the repo history.
Vector: A developer runs /eval, forgets to clean up, then does git add . and
        commits. The results files are not blocked by .gitignore.
Fix:    Add the following pattern to .gitignore:
          eval_results_*.json
          eval_report_*.md
        Alternatively, default output_dir to a dedicated evals/results/
        subdirectory that is git-ignored as a whole.

[LOW] API Key Absence Check Relies on Truthiness of Config Field: eval_runner.py:_create_judge_llm() (line 77)
Risk:   The guard `if not cfg.openai_api_key` treats an empty string ""
        the same as None. Pydantic-settings will load OPENAI_API_KEY=""
        from .env without error; the guard will correctly raise LLMError.
        However, ChatOpenAI is then never instantiated with the key
        explicitly — it relies on the OPENAI_API_KEY environment variable
        being present in the process environment. If pydantic-settings loads
        the key into the config object but the environment variable is
        stripped (e.g., in a subprocess or Docker ENV override), the
        ChatOpenAI call will silently fail at API call time rather than at
        LLM instantiation, producing a confusing error message.
Vector: Misconfigured Docker environment where cfg.openai_api_key is
        non-empty from a cached config but the env var is absent.
Fix:    Pass the key explicitly to ChatOpenAI:
          return ChatOpenAI(model=cfg.openai_model, temperature=0,
                            api_key=cfg.openai_api_key)
        This matches the pattern used in llm_provider_manager.py and ensures
        the key in config is actually used rather than the ambient env var.

[INFO] eval_runner.py Writes Output to Project Root by Default: lines 325, 396-398
Risk:   No immediate security threat. The default output_dir is _PROJECT_ROOT
        (the directory containing eval_runner.py). On a developer workstation
        this is the repo root. Files are named with a date suffix so no
        overwrite of existing critical files is possible.
Vector: N/A — filenames are fixed-format date strings with no user input.
Fix:    No action required. Optional improvement: default to evals/results/
        to keep the project root tidy.

[INFO] No New Dependencies Introduced
Risk:   None. langchain-openai was already a runtime dependency. No new
        packages were added to pyproject.toml.
Vector: N/A
Fix:    N/A

---
DEPENDENCY SCAN
---------------
pip-audit result: The global Python environment (used by the pip-audit
invocation) showed 137 vulnerabilities across 33 packages. These are NOT
in the project venv. The project virtual environment contains:

  langchain-openai         1.2.1   (CVE-2026-41488 fixed at 1.1.14 — PATCHED)
  langchain-core           1.4.0   (CVE-2025-65106 fixed at 0.3.80 — PATCHED;
                                    CVE-2025-68664 fixed at 0.3.81 — PATCHED;
                                    CVE-2026-26013 fixed at 1.2.11 — PATCHED;
                                    CVE-2026-40087 fixed at 0.3.84 — PATCHED;
                                    CVE-2026-44843 fixed at 0.3.85 — PATCHED)
  langchain-community      0.4.1   (CVE-2025-6984 fixed at 0.3.27 — PATCHED)
  langchain-text-splitters 1.1.2   (CVE-2025-6985 fixed at 0.3.9 — PATCHED;
                                    CVE-2026-41481 fixed at 1.1.2 — PATCHED)

All langchain-family CVEs that appeared in the global audit are patched in
the project venv per pyproject.toml version constraints.

No new packages were added by this feature.

---
SUMMARY
-------
The RAG evaluation framework is well-structured and follows the project's
conventions for configuration, error handling, and logging. The two medium
findings are realistic attack paths in an internal tool context: a str.format()
call that embeds unsanitised FAISS-retrieved content into the judge prompt
creates both a prompt injection risk and a potential KeyError on documents
containing literal brace characters, and reflecting raw LLM output in exception
messages is a leakage vector worth closing before any broader deployment.
The low findings (eval output files not git-ignored, and passing the API key
explicitly to ChatOpenAI) are best-practice gaps with no immediate threat.
The dependency surface is clean — no new packages, and all venv langchain
packages are patched past known CVEs.
