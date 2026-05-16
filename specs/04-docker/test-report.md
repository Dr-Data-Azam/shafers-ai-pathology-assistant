# Test Report: Docker Containerization
Date:       2026-05-15
Branch:     feature/docker
Written by: test-writer agent

## Test Files
- `tests/test_docker_config.py` — 41 tests (39 original + 2 added after code review)

## Results
41 written | 41 passed | 0 failed

## Test List
| Test | Verifies |
|------|----------|
| test_dockerignore_file_exists | .dockerignore is present at the repository root |
| test_dockerignore_excludes_env | .env appears as a standalone non-comment line (secrets never baked in) |
| test_dockerignore_excludes_vectordb | vectorDB/ is excluded because it is volume-mounted at runtime |
| test_dockerignore_excludes_data | data/ is excluded so the source PDF is not copied into the image |
| test_dockerignore_excludes_venv | .venv/ is excluded because deps are installed fresh in the builder stage |
| test_dockerignore_does_not_exclude_pyproject_toml | pyproject.toml must reach the builder stage so uv can install deps |
| test_dockerignore_does_not_exclude_uv_lock | uv.lock must reach the builder stage for reproducible resolution |
| test_dockerfile_exists | Dockerfile is present at the repository root |
| test_dockerfile_builder_base_image | Stage 1 uses FROM python:3.13-slim AS builder |
| test_dockerfile_runtime_base_image | Stage 2 uses FROM python:3.13-slim AS runtime |
| test_dockerfile_uses_uv_sync | uv sync is used to install dependencies |
| test_dockerfile_uv_sync_is_frozen | --frozen flag ensures reproducible installs |
| test_dockerfile_uv_sync_is_no_dev | --no-dev flag keeps dev dependencies out of the image |
| test_dockerfile_creates_useradd | useradd is called to create a non-root user |
| test_dockerfile_creates_appuser | The non-root user is named appuser |
| test_dockerfile_appuser_has_uid_1000 | appuser is created with UID 1000 for predictable volume permissions |
| test_dockerfile_switches_to_appuser | USER appuser drops privileges before the CMD runs |
| test_dockerfile_sets_hf_home | HF_HOME env var controls the HuggingFace model cache path |
| test_dockerfile_predownloads_sentence_transformer | SentenceTransformer is imported at build time |
| test_dockerfile_predownloads_correct_model | all-MiniLM-L6-v2 is the model pre-downloaded at build time |
| test_dockerfile_has_healthcheck | A HEALTHCHECK directive is present |
| test_dockerfile_healthcheck_uses_stcore_endpoint | Health check polls /_stcore/health |
| test_dockerfile_exposes_8501 | EXPOSE 8501 declares the Streamlit port |
| test_dockerfile_cmd_uses_headless | --server.headless is passed in CMD |
| test_dockerfile_cmd_binds_all_interfaces | 0.0.0.0 is used so the container is reachable externally |
| test_dockerfile_fixes_cache_ownership | chown -R appuser gives the non-root user model cache ownership |
| test_compose_file_exists | docker-compose.yml is present at the repository root |
| test_compose_is_valid_yaml | docker-compose.yml parses as valid YAML |
| test_compose_has_app_service | The app service is declared |
| test_compose_app_port_mapping | Port 8501:8501 is mapped on the app service |
| test_compose_app_env_file | env_file references .env for secret injection |
| test_compose_app_volume_mount | vectordb:/app/vectorDB volume is mounted on the app service |
| test_compose_app_restart_policy | restart: unless-stopped is set on the app service |
| test_compose_app_has_healthcheck | A healthcheck block is declared on the app service |
| test_compose_app_healthcheck_uses_stcore_endpoint | The compose healthcheck polls /_stcore/health |
| test_compose_has_vector_builder_service | The vector-builder service is declared |
| test_compose_vector_builder_has_build_profile | vector-builder is guarded by the build profile |
| test_compose_vector_builder_command_runs_creator | The command invokes vector_store_creator.py |
| test_compose_vector_builder_mounts_data_readonly | ./data:/app/data:ro mount is present |
| test_compose_vector_builder_mounts_vectordb | vectordb:/app/vectorDB mount is present on the builder |
| test_compose_top_level_volumes_declares_vectordb | The vectordb named volume is declared at the top level |

## Coverage Notes
test_docker_config.py exercises no application Python lines — it validates infrastructure
file content only. Excluded from coverage measurement in pyproject.toml omit list.
Full suite coverage: 77% (gate: 75%).
