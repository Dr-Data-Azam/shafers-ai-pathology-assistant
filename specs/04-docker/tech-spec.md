# Technical Design: Docker Containerization

## Summary
Add a multi-stage Dockerfile, docker-compose.yml, and .dockerignore to containerize the
Shafer's AI Pathology Assistant. The image runs as a non-root user, pre-downloads the
embedding model at build time, and uses Streamlit's built-in health endpoint. A named
Docker volume persists the FAISS vector database across container restarts. No application
Python logic is modified.

---

## Implementation Tasks

- [ ] Task 1: Create `.dockerignore`
      What: Prevents secrets, large data files, and dev artifacts from being sent to the build context
      Where: `.dockerignore` (new file at repo root)
      How: Exclude `.env*`, `.venv/`, `__pycache__/`, `*.pyc`, `vectorDB/`, `data/`,
           `chat_history.json`, `*.log`, `.git/`, `.github/`, `tests/`, `specs/`,
           `infrastructure/`, `.coverage`, `htmlcov/`, `.pytest_cache/`, `.ruff_cache/`,
           `.python-version`, `*.pkl`. Keep `pyproject.toml`, `uv.lock`, and all `.py` files.

- [ ] Task 2: Create `Dockerfile` (multi-stage)
      What: Builds the containerized app image with a non-root user, pre-downloaded embedding model, and health check
      Where: `Dockerfile` (new file at repo root)
      How: Two stages —
           Stage 1 (builder): `python:3.13-slim` base, copy uv binary from
           `ghcr.io/astral-sh/uv:latest`, copy `pyproject.toml` + `uv.lock`, run
           `uv sync --frozen --no-dev --no-install-project` to install runtime deps into `.venv`.
           Stage 2 (runtime): `python:3.13-slim` base, create non-root group+user `appuser`
           (UID 1000), copy `.venv` from builder, set `PATH` to use the venv, set
           `HF_HOME=/app/.cache/huggingface`, run `python -c "from sentence_transformers
           import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"` as root
           to pre-download the model, copy all app source files with `--chown=appuser:appuser`,
           chown `/app/.cache` to appuser, switch to `USER appuser`, `EXPOSE 8501`,
           `HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3` using
           `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"`,
           `CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0",
           "--server.port", "8501", "--server.headless", "true"]`.

- [ ] Task 3: Create `docker-compose.yml`
      What: Enables single-command local development and provides an explicit vector-builder service
      Where: `docker-compose.yml` (new file at repo root)
      How: Two services —
           `app`: builds from Dockerfile, maps port `8501:8501`, loads secrets via
           `env_file: .env`, mounts named volume `vectordb:/app/vectorDB`, health check
           mirrors Dockerfile, `restart: unless-stopped`.
           `vector-builder`: same build, same env_file, mounts `vectordb:/app/vectorDB` +
           `./data:/app/data:ro`, command `python vector_store_creator.py`,
           `profiles: [build]` so it never starts during normal `docker compose up`.
           Named volume `vectordb` declared at the bottom.

---

## Files to Create
| File | Purpose |
|------|---------|
| `.dockerignore` | Exclude secrets, large data, and dev artifacts from build context |
| `Dockerfile` | Multi-stage build: builder installs deps; runtime runs app as non-root with pre-downloaded model |
| `docker-compose.yml` | Single-command dev setup; named volume for vectorDB; separate build-profile service |

## Files to Modify
None. No application logic changes.

## New Dependencies
None.

## Breaking Changes
None.

---

## Key Decisions
| Decision | Choice | Reason |
|---|---|---|
| Health check | Streamlit built-in `/_stcore/health` | No app code changes; built into Streamlit 1.47+ |
| Embedding model | Pre-downloaded at build time | Instant container startup; no extra volume to manage |
| HF cache path | `/app/.cache/huggingface` via `HF_HOME` | Writable by appuser after chown |
| Vector DB | Named volume `vectordb:/app/vectorDB` | Survives restarts; decoupled from image |
| Vector builder | `--profile build` service | Not part of normal `up`; invoked explicitly |

---

## Testing Strategy
No unit tests — these are infrastructure files with no Python logic.
Verification is manual/integration:

| Check | Command |
|---|---|
| Compose YAML is valid | `docker compose config` |
| Image builds successfully | `docker build .` |
| App starts and is healthy | `docker compose up` then `curl http://localhost:8501/_stcore/health` |
| Non-root user confirmed | `docker compose exec app whoami` → `appuser` |
| Vector DB persists on restart | Stop + restart container; volume contents remain |
| Vector builder runs standalone | `docker compose --profile build run vector-builder` |
