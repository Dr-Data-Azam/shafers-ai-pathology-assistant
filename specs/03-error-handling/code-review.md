# Code Review: Error Handling and Structured Logging
Date:     2026-05-15
Branch:   feature/error-handling
Reviewer: code-reviewer agent

CODE REVIEW — Error Handling and Structured Logging
Branch: feature/error-handling
Spec:   specs/03-error-handling/tech-spec.md
Files:  13 changed (2 created, 11 modified)

VERDICT: APPROVED WITH COMMENTS

---
ISSUES
------

[SHOULD FIX] config.py:71 — configure_logging()
What: Every call to configure_logging() unconditionally adds two new handlers to
the root logger (a RotatingFileHandler and a StreamHandler). There is no guard
against duplicate handlers. The implementation summary acknowledges this and
labels it "acceptable in the current architecture", but the Streamlit runner
re-imports the module on hot-reload cycles, meaning the root logger accumulates
duplicate handlers over the lifetime of a long-running Streamlit session. This
produces duplicate log lines and inflated log files.
Why: In production this causes every log statement to be emitted N times (once
per app restart/hot-reload), filling app.log faster and making the audit trail
misleading — a concern for a healthcare-adjacent application.
Fix: Add a short guard before attaching handlers:

    root = logging.getLogger()
    if root.handlers:
        return  # already configured; skip to avoid duplicates
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)

[SHOULD FIX] rag_system.py:9-17 — import ordering violates PEP 8 / Ruff E402
What: logger = logging.getLogger(__name__) appears on line 9, between the stdlib
imports and the first-party imports. The three local imports (llm_provider_manager,
vector_retriever, chat_history_manager) appear after the logger assignment, which
means they land below the module-level logger. While this works at runtime, Ruff
will flag E402 (module-level import not at top of file) for any import that
follows a non-import statement.
Why: The project mandates Ruff clean before every commit. If Ruff reports E402
for those lines, the /ship-feature pipeline will fail or require a --no-fix
workaround.
Fix: Move the logger assignment after all imports:

    import logging
    import time
    from typing import Any, Dict, Tuple

    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate

    from llm_provider_manager import load_llm, validate_provider
    from vector_retriever import (
        get_comprehensive_context,
        get_retriever,
        process_documents_for_context,
    )
    from chat_history_manager import save_chat_history

    logger = logging.getLogger(__name__)

[SHOULD FIX] tests/ — no test for configure_logging()
What: The tech spec explicitly lists "configure_logging() sets up handlers" as a
required test scenario (testing strategy table, row 2). No such test exists in
any test file. The function is called in production entry points but its
behaviour — that it actually attaches the expected handlers with the expected
format string — is never verified.
Why: Without a test, a future refactor that silently drops one of the handlers
(e.g., the RotatingFileHandler) would go undetected. For a healthcare application
where auditability matters, the logging setup is critical infrastructure.
Fix: Add a test in tests/test_config.py (or a new tests/test_configure_logging.py)
that calls configure_logging() with a controlled AppConfig, then asserts that
logging.getLogger() has at least one RotatingFileHandler and one StreamHandler
attached, and that the root level matches the configured log_level.

[CONSIDER] tests/test_llm_provider_manager.py:282-296 — stale docstring on
test_load_llm_invalid_provider_raises_exception
What: The docstring says "raises Exception before the elif chain in load_llm()
is reached" and refers to the "unreachable ValueError branch". Both of these
descriptions are now outdated: the ValueError branch was replaced with
LLMError in this feature. The test itself still passes (LLMError IS-A Exception,
and the match="anthropic" string is present in the formatted LLMError message),
but the docstring is misleading for the next developer.
Why: Misleading documentation is a maintenance liability — someone reading this
test will think the validation happens in validate_provider and that the old
ValueError branch exists, neither of which is the full picture.
Fix: Update the docstring to: "Passing an unknown provider name raises LLMError.
With both keys set, validate_provider() finds 'anthropic' not in ['openai',
'groq'] and raises LLMError before the elif chain is reached."

[CONSIDER] config.py — log_level is not validated
What: configure_logging() uses getattr(logging, cfg.log_level.upper(), logging.INFO)
as a fallback when the level string is unrecognised. This silently falls back to
INFO with no warning. A typo in LOG_LEVEL (e.g. "INFOO") would go unnoticed.
Why: Operational visibility issue — the user sets LOG_LEVEL=DEBUG and never sees
debug output, with no indication why.
Fix: Either add a Pydantic validator on log_level that rejects values not in
{"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}, or emit a warning log before
falling back: logger.warning("Unrecognised LOG_LEVEL '%s'; defaulting to INFO").

---
POSITIVES
---------

1. Exception hierarchy design is clean and complete. PathologyAppError as a
catchable base, typed subclasses with stored attributes (provider, message), and
super().__init__() wired correctly so str(e) and isinstance() both work as
expected. The LLMError format string "[{provider}] {message}" gives instant
context in log output without any extra formatting code at the call site.

2. The rag_system.py refactor is exactly right. Removing the broad try/except
that silently returned error strings is the most impactful correctness change in
the entire diff. The function is now simpler (15 fewer lines), its return type
contract is honoured (always a real answer or an exception, never a fake string),
and both callers were updated in the same commit. No new exception-swallowing was
introduced.

3. Caller-side error handling is well-differentiated. Both streamlit_app.py and
main_console.py show distinct handling per exception type: LLMError is non-fatal
and prompts a retry message, RetrieverError is fatal and exits the loop,
ConfigError exits the process with sys.exit(1) in main_console.py. The messages
are user-friendly and do not expose internal exception detail to the UI — a
correct approach for a production health application.

---
SUMMARY
-------
The implementation matches all 11 tasks in the tech spec and the deviations are
well-reasoned and documented in the implementation summary. The exception hierarchy
is sound, all named modules have module-level loggers, print()-based error output
has been eliminated, and both callers handle typed exceptions correctly. Two
should-fix items (the duplicate-handler accumulation in configure_logging and the
import ordering in rag_system.py) need attention before shipping; neither is a
correctness bug in isolation but both will surface as problems in the running app
or in the CI pipeline. The missing configure_logging test is a gap against the
tech spec's own testing strategy table.
