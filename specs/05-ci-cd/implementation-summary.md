# Implementation Summary: CI/CD Pipeline with GitHub Actions

## Tasks Completed

- [x] Task 1: Create PR checks workflow (`.github/workflows/pr-checks.yml`)
- [x] Task 2: Create Docker build workflow (`.github/workflows/docker-build.yml`)
- [x] Task 3: Document branch protection setup (`specs/05-ci-cd/branch-protection.md`)

## Files Created and Modified

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/pr-checks.yml` | Created | PR workflow: 3 parallel jobs — lint, test, security |
| `.github/workflows/docker-build.yml` | Created | Push-to-main workflow: Docker image build, no push |
| `specs/05-ci-cd/branch-protection.md` | Created | Manual post-deploy steps for GitHub branch protection |
| `specs/05-ci-cd/non-tech-spec.md` | Created | Non-technical specification |
| `specs/05-ci-cd/tech-spec.md` | Created | Technical design specification |
| `specs/05-ci-cd/implementation-summary.md` | Created | This file |

No application source files (`.py`) were modified.

## Test Results

All pre-existing tests pass. No new Python code was introduced, so no new tests were written.

| Metric | Value |
|--------|-------|
| Tests run | 165 |
| Passed | 165 |
| Failed | 0 |
| Duration | 6.51s |
| Total coverage | 77% |
| Coverage threshold | 75% (passed) |

**Per-module coverage:**

| Module | Coverage |
|--------|----------|
| config.py | 100% |
| exceptions.py | 100% |
| rag_system.py | 100% |
| llm_provider_manager.py | 95% |
| chat_history_manager.py | 82% |
| vector_retriever.py | 76% |
| main_console.py | 51% |

## Key Implementation Decisions

**Three parallel jobs instead of sequential steps**
The PR checks workflow uses three independent jobs (`lint`, `test`, `security`) rather than
sequential steps in one job. This means each check produces its own GitHub status check,
which can be individually required in branch protection rules. A developer pushing a PR
gets simultaneous feedback on all three dimensions rather than discovering failures one at
a time.

**`uvx pip-audit` instead of a project dependency**
pip-audit is invoked via `uvx` (uv's isolated tool runner) rather than being added to
`[dependency-groups] dev` in `pyproject.toml`. pip-audit is a CI infrastructure tool, not
part of the development or runtime environment. Keeping it out of the project venv avoids
polluting the lock file with a tool that has no relevance to local development.

**`uv export --no-dev` for the security audit scope**
The `security` job exports only runtime dependencies (no `--dev` group) before running
pip-audit. Scanning dev tools like Black, Ruff, and pytest for CVEs produces noise
unrelated to production risk and would train developers to dismiss security warnings.

**GHA layer caching on Docker build**
The Docker build workflow uses `cache-from: type=gha` / `cache-to: type=gha,mode=max`.
The Dockerfile downloads a HuggingFace embedding model (`all-MiniLM-L6-v2`) at build time,
which is a multi-hundred-MB download. Without caching, every push to `main` would re-download
it. With GHA caching the model layer is cached after the first run, keeping subsequent build
times practical.

**`python-version` omitted from `setup-uv` blocks**
The `astral-sh/setup-uv` action is invoked without a `python-version` input. uv reads the
`.python-version` file automatically, making it the single source of truth for the Python
version across local development, Docker, and CI.

## Deviations from the Tech Spec

All deviations were introduced during code review (APPROVED WITH COMMENTS).

| Deviation | Reason |
|-----------|--------|
| Added `--no-dev` to `uv export` in the `security` job | Code review: scanning dev tools is noisy and unrelated to production risk |
| Removed `python-version: "3.13"` from all three `setup-uv` blocks | Code review: `.python-version` is the single source of truth; duplicating it creates drift risk |
| Added `timeout-minutes` to all three PR check jobs (10m lint/security, 15m test) | Code review: GitHub's 6-hour default could exhaust runner minutes on a hung job |
| Added job name vs. job id clarification to `branch-protection.md` | Code review: GitHub uses the `name:` field as the status check identifier, not the job id |
