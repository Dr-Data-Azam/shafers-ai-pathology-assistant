# Code Review: Docker Containerization
Date:     2026-05-15
Branch:   feature/docker
Reviewer: code-reviewer agent

CODE REVIEW — Docker Containerization
Branch: feature/docker
Spec:   specs/04-docker/tech-spec.md
Files:  4 changed (3 infrastructure, 1 test file — all untracked, not yet committed)

VERDICT: CHANGES REQUESTED

---
ISSUES
------

[MUST FIX] tests/test_docker_config.py (all 39 tests)
What: Adding test_docker_config.py to the suite causes the project-wide coverage to drop
      from 77% to 10%, triggering the existing fail_under=75 threshold in pyproject.toml
      and making `pytest` exit with an error. This means `/ship-feature` and the CI gate
      will fail even though all 39 individual tests pass.
Why:  test_docker_config.py exercises zero application Python lines (it only reads files
      from disk). Coverage is measured across the whole repo, so 39 tests that touch no
      Python code dilute the denominator enough to fall below the 75% floor.
Fix:  Add a pytest mark and exclude this test file from coverage collection, OR add a
      `# pragma: no cover` escape — but the cleanest fix matches the pattern already used
      for integration tests: mark the file with a custom marker and add a coverage
      `omit` entry in pyproject.toml for `tests/test_docker_config.py`, or move the file
      to `tests/integration/` which is already excluded from the default run via the
      existing skip pattern. Alternatively, update `[tool.coverage.run] omit` in
      pyproject.toml to include `tests/test_docker_config.py`.

[MUST FIX] Dockerfile:45
What: `COPY --chown=appuser:appuser . .` runs after the model is pre-downloaded but
      without any `.dockerignore` protection against a present `.env` file at build time.
      The `.dockerignore` does list `.env` and `.env.*`, so the file is excluded from the
      build context on a clean machine. However, the test `test_dockerignore_excludes_env`
      only asserts `".env" in content` — this passes because the word ".env" appears in
      a comment line (`# Secrets — never bake into the image`) and in `.env.*`, meaning
      the test would pass even if the bare `.env` entry were deleted. The assertion is
      insufficiently precise.
Why:  A test whose assertion is satisfied by a comment string provides false confidence
      about a security-critical exclusion. If someone removes the `.env` line and the
      comment remains, the test still passes while secrets become bakeable into the image.
Fix:  Tighten the assertion to check that `.env` appears as a standalone non-comment
      line. For example:
        non_comment_lines = [l.strip() for l in content.splitlines()
                             if l.strip() and not l.strip().startswith("#")]
        assert ".env" in non_comment_lines

[SHOULD FIX] tests/test_docker_config.py (no test for UID 1000)
What: The tech spec explicitly requires `--uid 1000` for the non-root user. There is no
      test asserting this UID is present in the Dockerfile. The existing
      `test_dockerfile_creates_appuser` only checks that the string "appuser" appears
      somewhere in the file.
Why:  UID 1000 is a deliberate requirement in the spec (it ensures predictable host-
      container UID mapping for volume permissions on Linux hosts). Without a test, this
      can be silently changed or dropped.
Fix:  Add:
        def test_dockerfile_appuser_has_uid_1000():
            assert "--uid 1000" in _read(DOCKERFILE)

[SHOULD FIX] tests/test_docker_config.py (no test that compose healthcheck polls /_stcore/health)
What: The compose file's healthcheck is tested only for existence
      (`test_compose_app_has_healthcheck`), not for the correctness of the endpoint it
      polls. The Dockerfile healthcheck endpoint is verified, but the compose one is not.
Why:  Both healthchecks are spec requirements. A copy-paste error that changed the
      compose healthcheck to a different URL would go undetected.
Fix:  Add:
        def test_compose_app_healthcheck_uses_stcore_endpoint():
            test_str = str(_compose()["services"]["app"]["healthcheck"]["test"])
            assert "_stcore/health" in test_str

[SHOULD FIX] Dockerfile (no WORKDIR set before builder-stage COPY)
What: In Stage 1, `WORKDIR /app` is set on line 8 and the COPY follows on line 12 —
      this is correct. However, in Stage 2, `WORKDIR /app` is set on line 26 but the
      `.venv` copy from builder on line 29 uses an absolute destination `/app/.venv`.
      This is technically fine but inconsistent: the WORKDIR declaration is redundant
      for that COPY because the absolute path is used explicitly. Minor — but can
      confuse readers who expect WORKDIR to govern the COPY destination.
Why:  Clarity and consistency in Dockerfiles reduces the risk of path bugs during future
      edits.
Fix:  Change `COPY --from=builder /app/.venv /app/.venv` to use the relative form
      `.venv .venv/` so it relies on WORKDIR as the other COPY does, or add a brief
      comment explaining the absolute path is intentional.

[CONSIDER] .dockerignore — missing `CLAUDE.md` exclusion
What: `CLAUDE.md` is not excluded from the build context and will be copied into the
      image by `COPY --chown=appuser:appuser . .`. It contains no secrets, but it is a
      dev-only document that has no function inside the running container.
Why:  Adds unnecessary bytes to the image; fine for now but worth noting.
Fix:  Add `CLAUDE.md` and `*.md` (or just `CLAUDE.md`) to `.dockerignore`. Do not
      exclude `README.md` if one exists, unless it too has no runtime role.

[CONSIDER] docker-compose.yml — no explicit `depends_on` or startup order documentation
What: The `vector-builder` service is behind a `--profile build` flag, so it will not
      start automatically with the `app` service. However, there is no guard in the
      compose file that warns if someone runs `docker compose up` before the vectorDB
      volume is populated.
Why:  On a first deploy, the `app` container will start, fail to find a FAISS index,
      and log an error. This is acceptable but undocumented.
Fix:  Add a comment block in `docker-compose.yml` noting the first-run workflow:
      build the vector store with `--profile build` before running `docker compose up`.
      This is partly done in the existing comment block but could be more prominent.

---
POSITIVES
---------
1. Layer-caching discipline in the Dockerfile is excellent: pyproject.toml and uv.lock
   are copied in their own layer before any application source, so a code-only edit
   does not re-run the full dependency install. This is the correct pattern and is
   clearly commented.

2. The model pre-download strategy is well-executed: HF_HOME is pinned to a controlled
   path, the download runs as root before the USER switch, and ownership is corrected
   with a single chown -R before privileges are dropped. The container starts with zero
   network calls needed for the embedding model.

3. The test suite is well-structured for infrastructure-file testing: no Docker daemon
   calls, no subprocess spawning, pure file-content and YAML-parse assertions. The
   _compose() helper that parses YAML once is clean and the normalization of env_file
   (string vs list) in test_compose_app_env_file is a good defensive touch.

---
SUMMARY
-------
The three infrastructure files (.dockerignore, Dockerfile, docker-compose.yml) match
the tech spec closely — all spec tasks are implemented, the non-root user, named volume,
profile-gated vector-builder, and health check are all present and correct. The blocking
issue is purely operational: adding 39 coverage-blind tests to the suite drops total
coverage below the project's 75% threshold and breaks the full test run. Fix the
coverage omit for this test file, tighten the `.env` exclusion assertion to avoid
false confidence on a security-critical line, and add the two missing targeted tests
before shipping.
