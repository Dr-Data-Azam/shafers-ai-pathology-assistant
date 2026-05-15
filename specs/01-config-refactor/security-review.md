# Security Review: Config Refactor
Date:     2026-05-15
Branch:   feature/config-refactor
Reviewer: security-reviewer agent

```
SECURITY REVIEW — config-refactor
Branch: feature/config-refactor

VERDICT: REVIEW NOTES

---
FINDINGS
--------

[MEDIUM] Unsafe Deserialization: vector_retriever.py:31 — get_retriever()
Risk:   pickle.load() on vectorDB/retriever.pkl executes arbitrary Python bytecode.
        An attacker who can write to the vectorDB/ directory achieves RCE on the
        next call to get_retriever().
Vector: In a shared or cloud-hosted deployment (Streamlit Cloud, shared VM, mounted
        volume), a co-tenant or misconfigured permission on vectorDB/ allows writing a
        malicious pickle. The app deserializes it on the next cold start or cache miss.
        No HMAC, hash, or signature check guards the file before loading.
Fix:    Replace pickle with a safe alternative: serialize the retriever's config
        parameters (path, k, fetch_k, lambda_mult) and reconstruct the object on load
        rather than pickling the object itself. If pickle is required, sign the file
        with hmac.new(secret_key, file_bytes, sha256) and verify before loading.
Confidence: 8/10

[MEDIUM] Credential Exposure via Exception Propagation: llm_provider_manager.py:62,78 / rag_system.py:134
Risk:   raise Exception(f"Failed to load OpenAI model: {str(e)}") and
        raise Exception(f"Failed to load Groq model: {str(e)}") propagate raw SDK
        exception strings. The OpenAI SDK 1.x constructs APIError messages by
        interpolating the full API response body, which on 401 errors contains
        the partial API key: "Incorrect API key provided: sk-proj-***...XXXX".
        This string reaches the Streamlit UI via st.error() and is also returned
        in the answer string from rag_system.get_answer(), exposing it to any user
        of the app.
Vector: A user enters a question → the LLM call fails with 401 → the exception string
        containing the partial key is rendered in the Streamlit browser UI and/or
        returned as the answer string. Any user of the app can trigger this with a
        network error or if the API key expires.
Fix:    Strip exception details from user-facing messages:
          raise Exception("Failed to load OpenAI model: authentication error")
          raise Exception("Failed to load Groq model: authentication error")
        Log the full str(e) to stderr only (not to the UI). In streamlit_app.py,
        catch exceptions and show a generic "LLM error — check your API keys" message.
Confidence: 8/10

---
DEPENDENCY SCAN
---------------
pip-audit result: 19 vulnerabilities found

Notable CVEs in this diff's dependency set:
  streamlit    1.45.1  CVE-2026-33682  (fix: 1.54.0)
  transformers 4.52.4  CVE-2025-5197   (fix: 4.53.0) — 4 CVEs total
  tornado      6.5.1   CVE-2026-31958  (fix: 6.5.5)  — 3 CVEs total
  starlette    0.46.2  CVE-2025-54121  (fix: 0.47.2)  — 2 CVEs total
  requests     2.32.4  CVE-2026-25645  (fix: 2.33.0)
  urllib3      2.5.0   CVE-2025-66418  (fix: 2.6.0)  — 3 CVEs total
  torch        2.7.1   CVE-2025-3730   (fix: 2.8.0)
  uv           0.9.7   GHSA-pjjw-68hj-v9mw (fix: 0.11.6)

These are pre-existing dependency issues, not introduced by this diff.
Recommend a separate chore branch to bump affected packages.

---
SUMMARY
-------
The config-refactor change itself introduces no new attack surface — it centralises
config into Pydantic Settings and removes hardcoded values. The two medium findings
are pre-existing patterns in vector_retriever.py and llm_provider_manager.py that
this diff did not introduce or worsen. No CRITICAL or HIGH findings. Safe to proceed
with /ship-feature, but both MEDIUM items should be tracked as follow-up work before
any public or multi-user deployment.
```
