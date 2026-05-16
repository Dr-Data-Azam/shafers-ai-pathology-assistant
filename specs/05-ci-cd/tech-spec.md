# Technical Design: CI/CD Pipeline with GitHub Actions

## Summary
Two GitHub Actions workflows are added to the existing `.github/workflows/` directory.
The first runs on every pull request targeting `main` and executes three parallel jobs —
lint (Black + Ruff), test (pytest with coverage), and security (pip-audit) — each
producing an independent status check that can block merging. The second runs on every
push to `main` and builds the Docker image without pushing it to any registry.

## Implementation Tasks
Tasks are ordered — complete them in sequence.

- [ ] Task 1: Create PR checks workflow
      What: Validates every PR with three parallel, independently-blocking quality checks.
      Where: `.github/workflows/pr-checks.yml` (new file)
      How: Define a `pull_request` workflow targeting `main` with three jobs — `lint`,
      `test`, and `security`. Each job independently checks out the code, installs uv,
      runs `uv sync --frozen`, then executes its check. `lint` runs `uv run black --check .`
      then `uv run ruff check .`. `test` runs `uv run pytest` (pyproject.toml config is
      picked up automatically). `security` exports locked deps via
      `uv export --frozen --format requirements-txt -o /tmp/requirements-audit.txt` then
      runs `uvx pip-audit -r /tmp/requirements-audit.txt`. No secrets or env vars are
      needed — tests mock all external calls.

- [ ] Task 2: Create Docker build workflow
      What: Verifies the Docker image builds successfully on every merge to main.
      Where: `.github/workflows/docker-build.yml` (new file)
      How: Define a `push` workflow scoped to the `main` branch with one job —
      `docker-build`. Steps: `actions/checkout@v4`, `docker/setup-buildx-action@v3`,
      then `docker/build-push-action@v6` with `push: false`, tagged as
      `shafers-ai-pathology-assistant:latest`, and GHA layer caching enabled
      (`cache-from: type=gha` / `cache-to: type=gha,mode=max`). No secrets needed —
      the embedded HuggingFace model is public.

- [ ] Task 3: Document branch protection setup
      What: Records the manual GitHub Settings steps required to enforce PR blocking.
      Where: `specs/05-ci-cd/branch-protection.md` (new file)
      How: Write a short Markdown document listing the exact GitHub UI steps:
      Settings → Branches → Add rule for `main` → enable "Require status checks to
      pass before merging" → add required checks `lint`, `test`, `security` → enable
      "Require branches to be up to date before merging". Note that this step cannot
      be automated without a repository admin token, so it is a post-deployment manual
      action.

## Files to Modify
None.

## Files to Create
| File | Purpose |
|------|---------|
| `.github/workflows/pr-checks.yml` | PR workflow: 3 parallel jobs (lint, test, security) |
| `.github/workflows/docker-build.yml` | Push-to-main workflow: Docker image build, no push |
| `specs/05-ci-cd/branch-protection.md` | Manual post-deploy steps for GitHub branch protection |

## New Dependencies
None. `pip-audit` is invoked via `uvx` (uv's isolated tool runner) and is not added to
`pyproject.toml`.

## Breaking Changes
None.

## Data Flow
Not applicable — this feature adds CI infrastructure, not application data paths.

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| `lint` job catches bad formatting | Manual / integration | Push a PR with an unformatted file; verify job fails |
| `test` job catches failing tests | Manual / integration | Push a PR with a broken test; verify job fails |
| `security` job runs pip-audit | Manual / integration | Inspect job logs for pip-audit output after push |
| `docker-build` job completes | Manual / integration | Merge to main; verify job passes in Actions tab |

Minimum coverage target: N/A — no new Python code is introduced.

## Branch Protection (Post-Deploy Manual Step)
After the workflows are merged to `main`, configure branch protection in GitHub:
1. Settings → Branches → Branch protection rules → Add rule
2. Branch name pattern: `main`
3. Enable: **Require status checks to pass before merging**
4. Add required checks: `lint`, `test`, `security`
5. Enable: **Require branches to be up to date before merging**
