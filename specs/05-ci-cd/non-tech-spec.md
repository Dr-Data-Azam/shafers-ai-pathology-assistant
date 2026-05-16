# Feature: CI/CD Pipeline with GitHub Actions

## Problem Statement
There is no automated pipeline to validate pull requests or build the Docker image on
merge. Developers must run linting, tests, and security scans manually — and there is
nothing stopping a failing PR from being merged. This creates risk of regressions,
unformatted code, and vulnerable dependencies reaching the main branch.

## User Story
As a developer on this project, I want every pull request automatically checked for
code quality, test coverage, and security issues so that broken or unsafe code cannot
be merged into main.

## What It Should Do (Acceptance Criteria)
- When a pull request is opened or updated, the pipeline runs Black + Ruff and reports
  any formatting or linting failures as a failed check on the PR.
- When a pull request is opened or updated, the pipeline runs the full pytest suite with
  coverage and reports any test failures as a failed check on the PR.
- When a pull request is opened or updated, the pipeline runs pip-audit against the
  project's dependencies and reports any known vulnerabilities as a failed check on the PR.
- When any of the three PR checks (lint, test, security) fails, GitHub blocks the PR
  from being merged until the failure is resolved.
- When all three PR checks pass, the PR is allowed to merge normally.
- When a commit is merged into main, the pipeline builds the Docker image using the
  project's existing Dockerfile.
- When the Docker build on main fails, the pipeline reports a failed workflow run on
  the main branch.

## What It Should NOT Do (Constraints)
- Must not push the built Docker image to any registry (no publish/deploy step).
- Must not modify any application source files (`.py` files, config, `.env`).
- Must not change or override the existing Black, Ruff, or pytest configuration.
- Must not run the Docker build on pull requests — only on merge to main.
- Must not require secrets beyond what GitHub Actions provides by default for a public
  repository (no external registry credentials needed since there is no push step).

## Files Likely Affected
- `.github/workflows/pr-checks.yml` — new workflow: lint + test + security scan on PRs
- `.github/workflows/docker-build.yml` — new workflow: Docker image build on merge to main

## Open Questions
- None.
