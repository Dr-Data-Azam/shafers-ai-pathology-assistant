# Implementation Summary: Docker Containerization

## Tasks Completed

- [x] Task 1: Create `.dockerignore` — excludes secrets, large data files, and dev artifacts from the build context
- [x] Task 2: Create `Dockerfile` — multi-stage build with non-root user, pre-downloaded embedding model, and Streamlit health check
- [x] Task 3: Create `docker-compose.yml` — single-command dev setup with named volume and profile-gated vector-builder service

---

## Files Created and Modified

| File | Type | What Changed |
|------|------|--------------|
| `.dockerignore` | Created | Excludes `.env*`, `vectorDB/`, `data/`, `.venv/`, `__pycache__/`, `*.pkl`, `*.log`, `tests/`, `specs/`, `infrastructure/`, dev caches |
| `Dockerfile` | Created | Multi-stage build: builder (uv + deps), runtime (non-root `appuser` UID 1000, pre-downloaded `all-MiniLM-L6-v2`, HEALTHCHECK via `/_stcore/health`) |
| `docker-compose.yml` | Created | `app` service (port 8501, `env_file`, named volume, healthcheck, restart policy) + `vector-builder` service (profile: build) |
| `tests/test_docker_config.py` | Created | 41 pytest tests validating content and structure of all three infrastructure files |
| `pyproject.toml` | Modified | Added `tests/test_docker_config.py` to `[tool.coverage.run] omit` list to prevent infrastructure tests from diluting coverage below the 75% gate |
| `specs/04-docker/non-tech-spec.md` | Created | Approved non-technical requirements |
| `specs/04-docker/tech-spec.md` | Created | Approved technical design |
| `specs/04-docker/code-review.md` | Created | Code review verdict (CHANGES REQUESTED → fixes applied) |
| `specs/04-docker/test-report.md` | Created | Test-writer agent output (41 tests, all passing) |

---

## Test Results

```
Tests run:   165
Passed:      165
Failed:      0
Duration:    10.52s
Coverage:    77% (gate: 75%)
```

| Module | Coverage |
|--------|----------|
| `config.py` | 100% |
| `exceptions.py` | 100% |
| `rag_system.py` | 100% |
| `llm_provider_manager.py` | 95% |
| `chat_history_manager.py` | 82% |
| `vector_retriever.py` | 76% |
| `main_console.py` | 51% |

`tests/test_docker_config.py` is excluded from coverage measurement (infrastructure tests exercise no application Python lines).

---

## Key Implementation Decisions

**Pre-downloading the embedding model at build time**
The `sentence-transformers/all-MiniLM-L6-v2` model (~91 MB) is downloaded during `docker build` via a `RUN python -c "SentenceTransformer(...)"` instruction in the runtime stage. This makes the image larger but means the container starts instantly with no network calls needed. The alternative (downloading at first startup) would cause a silent 1–3 minute delay that is hard to distinguish from a crash.

**`HF_HOME` pinned to `/app/.cache/huggingface`**
By default HuggingFace caches models under `~/.cache` (i.e., `/root/.cache` during the build). Since we switch to a non-root user at runtime, that path is inaccessible. Setting `HF_HOME=/app/.cache/huggingface` before the model download, then running `chown -R appuser:appuser /app/.cache`, ensures the cache is readable and writable by `appuser` at runtime.

**Model download before `COPY . .`**
The `SentenceTransformer` download layer appears before `COPY --chown=appuser:appuser . .` in the Dockerfile. This means a code-only edit does not invalidate the model download cache layer — Docker reuses the cached layer and skips the ~3 minute download on every rebuild.

**Streamlit built-in health check — no app code changes**
`/_stcore/health` is a built-in endpoint available since Streamlit 1.x. Using it required zero changes to application Python files, which satisfied the core constraint ("infrastructure only"). The health check uses `python -c "import urllib.request; ..."` rather than `curl` because `python:3.13-slim` does not include `curl` by default, avoiding an extra `apt-get install` layer.

**`vector-builder` under `--profile build`**
Docker Compose profiles allow the vector-builder service to be declared in the same file without starting automatically on `docker compose up`. The workflow is: run `docker compose --profile build run --rm vector-builder` once (with the PDF in `./data/`), then `docker compose up` for all subsequent starts. Both services share the same `vectordb` named volume.

---

## Deviations from the Tech Spec

**Two additional tests added post-review**
The code-reviewer identified two missing assertions: `test_dockerfile_appuser_has_uid_1000` (UID 1000 is a spec requirement with volume permission implications) and `test_compose_app_healthcheck_uses_stcore_endpoint` (the Dockerfile test had this check but the compose equivalent did not). Both were added, bringing the total from 39 to 41 tests.

**`tests/test_docker_config.py` added to coverage omit list**
The tech spec noted "no unit tests — infrastructure files only" but did not anticipate that adding 41 coverage-blind tests to the suite would dilute measured coverage from 77% to 10%, triggering the `fail_under = 75` gate in `pyproject.toml`. Adding the file to the omit list was the correct fix — it mirrors how `tests/conftest.py` is already handled.

**`test_dockerignore_excludes_env` assertion hardened**
The original test used `assert ".env" in content`, which passed trivially because `.env` appears in both a comment and the wildcard `.env.*` pattern. The code-reviewer flagged this as a security risk (the most critical entry in `.dockerignore` deserves a real assertion). The fix checks for `.env` as a standalone non-comment line.
