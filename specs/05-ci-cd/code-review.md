# Code Review: CI/CD Pipeline with GitHub Actions
Date:     2026-05-16
Branch:   feature/ci-cd
Reviewer: code-reviewer agent

CODE REVIEW — CI/CD Pipeline with GitHub Actions
Branch: feature/ci-cd
Spec:   specs/05-ci-cd/tech-spec.md
Files:  2 changed

VERDICT: APPROVED WITH COMMENTS

---
ISSUES
------

[SHOULD FIX] .github/workflows/pr-checks.yml:14 (all three jobs)
What: `astral-sh/setup-uv@v5` is used with a `python-version` key, but the
      `setup-uv` action does not accept `python-version` as a direct input — that is
      a parameter of `actions/setup-python`. The `setup-uv` action accepts
      `python-version` only as a hint to select the uv-managed Python; it does not
      guarantee the same pinning semantics as `actions/setup-python`. The project
      already has a `.python-version` file containing `3.13`, which uv reads
      automatically when `uv sync` is called. In practice the jobs will likely
      resolve to 3.13 anyway, but the intent is unclear and the mechanism is fragile
      if the action's behaviour changes across minor versions.
Why:  The `.python-version` file is the single source of truth for the Python version
      (used by uv locally and by the Dockerfile). Adding a redundant `python-version`
      input to setup-uv creates a second source of truth that can drift. In a
      healthcare-adjacent application where reproducibility of the test environment
      matters, the CI environment should be unambiguously pinned to the same Python
      as local development.
Fix:  Remove the `python-version: "3.13"` input from `astral-sh/setup-uv@v5` in all
      three jobs. The action will pick up `.python-version` automatically via uv.
      Alternatively, if you want an explicit pin, add a prior `actions/setup-python@v5`
      step with `python-version: "3.13"` and let setup-uv use that interpreter.

[SHOULD FIX] .github/workflows/pr-checks.yml:64 (security job, uv sync step)
What: The `security` job runs `uv sync --frozen` before exporting requirements for
      pip-audit. This installs the full dependency tree (including dev tools like
      Black, Ruff, and the entire pytest stack) into the runner environment, and
      then `uv export` produces a flat requirements file from that same lock. As a
      result, pip-audit scans dev dependencies (Black, Ruff, pytest, pytest-cov,
      pytest-mock) in addition to production dependencies. Dev dependencies have a
      much higher churn rate and are more likely to trigger noise from pip-audit.
Why:  pip-audit should scan what ships — not the dev toolchain. A CVE in a dev-only
      dependency is not a production risk in this application. Scanning it will either
      produce false positive blocks on PRs or cause developers to suppress the warning,
      degrading trust in the security gate over time.
Fix:  Pass `--no-dev` to the export step:
      `uv export --frozen --no-dev --format requirements-txt -o /tmp/requirements-audit.txt`
      The preceding `uv sync --frozen` step can remain as-is (it's needed to install
      pytest for the test job), but for the security job specifically, if you want to
      be strict you can also change the sync to `uv sync --frozen --no-dev`.

[SHOULD FIX] .github/workflows/pr-checks.yml:64 (security job) — spec deviation
What: The `branch-protection.md` file lists the required status check names as
      `Lint (Black + Ruff)`, `Test (pytest + coverage)`, and `Security (pip-audit)`.
      These match the `name:` field values of the three jobs in the workflow exactly.
      However, in the tech spec (Task 3) the checks are listed by their job *ids*:
      `lint`, `test`, `security`. GitHub uses the `name` field for display and the
      status check identifier; it is the full job `name:` value that appears in the
      required-checks search box after the workflow runs.
Why:  This is not a defect in the workflow itself, but branch-protection.md gives
      the full display names while the tech spec says to use the short ids. The
      mismatch between tech spec task 3 and the actual document could confuse a future
      admin configuring branch protection. The document as written is actually *more*
      correct than the spec, but the discrepancy should be noted.
Fix:  No code change required. Add a one-line note in branch-protection.md clarifying
      that GitHub uses the full job `name:` value (e.g. `Lint (Black + Ruff)`) as the
      required-check identifier, not the job id (`lint`). This prevents a future admin
      from searching for the wrong string.

[CONSIDER] .github/workflows/docker-build.yml (build step, uv binary in image)
What: The Dockerfile copies the uv binary at build time with
      `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`. The `docker-build`
      workflow uses GHA layer caching (`type=gha`). If `ghcr.io/astral-sh/uv:latest`
      is updated between CI runs, the builder stage cache will be invalidated and the
      build will re-download uv. This is correct behaviour, but it also means the
      Docker build is not fully reproducible — the same commit can produce a different
      image if uv releases a new version between two builds of the same SHA.
Why:  For a healthcare-adjacent application, build reproducibility is worth tracking.
      This is a latent risk rather than an immediate defect — the current spec does
      not require image signing or SBOM, so there is no blocking issue.
Fix:  In a follow-up, pin the uv image to a digest or specific version tag
      (e.g. `ghcr.io/astral-sh/uv:0.5.x`) in the Dockerfile. This is out of scope
      for the current CI/CD feature but should appear in a future chore ticket.

[CONSIDER] .github/workflows/pr-checks.yml (all jobs) — no timeout set
What: None of the three PR check jobs have a `timeout-minutes` value. The default
      GitHub Actions job timeout is 6 hours, which means a hung job (e.g. a test
      waiting on a mocked network call that leaks) would consume runner minutes for
      hours before being killed.
Why:  For a project where tests run in ~5 seconds locally (per MEMORY.md: 5s run
      time), a 6-hour timeout is 4320x the expected ceiling. A runaway job could
      exhaust free GitHub Actions minutes for the month.
Fix:  Add `timeout-minutes: 10` to the `lint` and `security` jobs and
      `timeout-minutes: 15` to the `test` job. This is generous overhead over a 5s
      test suite.

---
POSITIVES
---------

1. The uv toolchain usage is textbook-correct throughout. `uv sync --frozen` (not
   bare `uv sync`) is used everywhere, ensuring CI resolves from the committed lock
   file rather than re-resolving. `uvx pip-audit` invokes pip-audit in an isolated
   ephemeral environment — exactly the right pattern since pip-audit is not a project
   dependency. The `uv export --frozen` two-step (export then audit the flat file) is
   the correct approach for pip-audit v0.4+ compatibility.

2. The Docker build workflow is a clean, minimal implementation of the spec. GHA
   layer caching (`cache-from: type=gha` / `cache-to: type=gha,mode=max`) is enabled,
   which will dramatically reduce build time on repeat runs by caching the HuggingFace
   model download layer. The `push: false` constraint is correctly enforced, matching
   both the spec requirement and the non-tech-spec constraint of no registry publishing.

3. The three PR check jobs are correctly structured as independent parallel jobs rather
   than sequential steps in a single job. This means a failing lint check does not
   prevent the test or security jobs from running — all three produce their own status
   checks simultaneously, which gives the developer complete feedback in a single CI
   run rather than one failure at a time.

---
SUMMARY
-------
The implementation correctly matches all five acceptance criteria in the tech spec.
All three required workflow files are present, the uv commands are well-formed, and
no application source files were touched. The two [SHOULD FIX] items are not
correctness blockers — the pipeline will function as written — but the missing
`--no-dev` flag on `uv export` and the redundant `python-version` input in setup-uv
are worth correcting before this becomes a template for future features. The
[CONSIDER] items (job timeouts, uv image pinning) are hygiene improvements that
should be addressed in a follow-up chore ticket.
