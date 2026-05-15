# Code Review: Config Refactor
Date:     2026-05-15
Branch:   feature/config-refactor
Reviewer: code-reviewer agent

---

```
CODE REVIEW — config-refactor
Branch: feature/config-refactor
Spec:   specs/config-refactor/tech-spec.md
Files:  8 modified, 4 new (untracked)

VERDICT: APPROVED WITH COMMENTS

---
ISSUES
------

[SHOULD FIX] llm_provider_manager.py:40 — load_llm()
What: Missing return type annotation. The function returns either a ChatOpenAI or
      ChatGroq instance (both are BaseLanguageModel subclasses), but the signature
      read `def load_llm(provider: str = "openai"):` with no return hint.
Why:  CLAUDE.md requires "All new/modified functions must have type hints on
      parameters and return values." This function was modified as part of Task 5
      and the obligation applies.
Fix:  Add `-> Union[ChatOpenAI, ChatGroq]` to the signature.
Status: RESOLVED — Union[ChatOpenAI, ChatGroq] added before shipping.

[SHOULD FIX] llm_provider_manager.py:104 — clear_llm_cache()
What: Missing return type annotation on a public function that returns None implicitly.
Why:  Same CLAUDE.md rule.
Fix:  Add `-> None:` to the signature.
Status: RESOLVED — `-> None` added before shipping.

[SHOULD FIX] vector_retriever.py:15 — get_retriever()
What: Missing return type annotation. The function returns a VectorStoreRetriever
      but the signature read `def get_retriever():`.
Why:  This function was modified in Task 4 and carries the same type-hint obligation.
Fix:  Add `-> VectorStoreRetriever` to the signature.
Status: RESOLVED — `-> VectorStoreRetriever` added before shipping.

[CONSIDER] config.py:49 — require_at_least_one_llm_key validator
What: The validator error message names both keys generically rather than saying
      which one is missing given the context.
Why:  Not a bug — both could be missing, and both are named. Observation only.
Status: No action taken (CONSIDER severity).

[CONSIDER] test_llm_provider_manager.py:153-170 — test_load_llm_openai_constructs_correctly
What: The test constructs a second AppConfig(_env_file=None) to read expected values,
      creating implicit coupling — if defaults change both sides change in lockstep.
Why:  A literal-value assertion per test would serve as a regression guard.
Fix:  Consider adding one explicit assertion (e.g., `assert call_kwargs["temperature"] == 0.3`)
      alongside the config-comparison assertion.
Status: No action taken (CONSIDER severity).

---
POSITIVES
---------

1. The lru_cache / cache_clear pattern in test_config.py is exactly right. Using
   autouse fixtures that clear before and after each test means no test can leak
   config state to another. This is the correct and non-obvious way to test a
   cached singleton, and it is applied consistently in both test files.

2. The lazy-initialization refactor of embedding_model in vector_store_creator.py
   is a genuine improvement beyond the spec's minimum requirement. The old code
   eagerly instantiated HuggingFaceEmbeddings at import time. The new
   get_embedding_model() defers it until first use, speeding up tests and CLI startup.

3. All 16 config fields named in the tech spec are present in AppConfig with correct
   types and defaults matching the original hardcoded values. The validator correctly
   enforces the "at least one LLM key" invariant that was previously implicit and
   unenforced. This is the most important correctness property of the feature.

---
SUMMARY
-------
The implementation matches all 8 tasks in the tech spec. Every hardcoded path,
model name, and retrieval parameter has been centralised into AppConfig, and the
two modules specifically called out in the non-tech spec (streamlit_app.py,
main_console.py) were correctly left untouched as they contain no config literals.
All three [SHOULD FIX] items (missing return type annotations) were resolved
immediately after the review, before shipping.
```
