# tests/test_docker_config.py
#
# Validates the content and structure of Docker infrastructure files.
# No subprocess calls, no Docker daemon interaction — pure file-content inspection.
import yaml
from pathlib import Path

# Repo root is two levels up from this test file (tests/ -> repo root)
REPO_ROOT = Path(__file__).parent.parent

DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DOCKERFILE = REPO_ROOT / "Dockerfile"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    """Return file contents as a string."""
    return path.read_text(encoding="utf-8")


def _compose() -> dict:
    """Parse docker-compose.yml once and return the mapping."""
    return yaml.safe_load(_read(COMPOSE_FILE))


# ---------------------------------------------------------------------------
# .dockerignore tests
# ---------------------------------------------------------------------------


def test_dockerignore_file_exists():
    """The .dockerignore file is present at the repository root."""
    assert DOCKERIGNORE.exists(), ".dockerignore not found at repo root"


def test_dockerignore_excludes_env():
    """.env appears as a standalone non-comment line so secrets are never baked into the image."""
    non_comment_lines = [
        line.strip()
        for line in _read(DOCKERIGNORE).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert ".env" in non_comment_lines


def test_dockerignore_excludes_vectordb():
    """vectorDB/ is excluded because it is volume-mounted at runtime."""
    content = _read(DOCKERIGNORE)
    assert "vectorDB/" in content


def test_dockerignore_excludes_data():
    """data/ is excluded so the source PDF is not copied into the image."""
    content = _read(DOCKERIGNORE)
    assert "data/" in content


def test_dockerignore_excludes_venv():
    """.venv/ is excluded because dependencies are installed fresh in the builder stage."""
    content = _read(DOCKERIGNORE)
    assert ".venv/" in content


def test_dockerignore_does_not_exclude_pyproject_toml():
    """pyproject.toml must reach the builder stage so uv can install dependencies."""
    lines = _read(DOCKERIGNORE).splitlines()
    # A bare 'pyproject.toml' entry would exclude it — that line must not appear
    assert "pyproject.toml" not in [line.strip() for line in lines]


def test_dockerignore_does_not_exclude_uv_lock():
    """uv.lock must reach the builder stage for reproducible dependency resolution."""
    lines = _read(DOCKERIGNORE).splitlines()
    assert "uv.lock" not in [line.strip() for line in lines]


# ---------------------------------------------------------------------------
# Dockerfile tests
# ---------------------------------------------------------------------------


def test_dockerfile_exists():
    """The Dockerfile is present at the repository root."""
    assert DOCKERFILE.exists(), "Dockerfile not found at repo root"


def test_dockerfile_builder_base_image():
    """Stage 1 uses python:3.13-slim as the builder base image."""
    assert "FROM python:3.13-slim AS builder" in _read(DOCKERFILE)


def test_dockerfile_runtime_base_image():
    """Stage 2 uses python:3.13-slim as the runtime base image."""
    assert "FROM python:3.13-slim AS runtime" in _read(DOCKERFILE)


def test_dockerfile_uses_uv_sync():
    """uv sync is used to install dependencies."""
    assert "uv sync" in _read(DOCKERFILE)


def test_dockerfile_uv_sync_is_frozen():
    """--frozen flag is passed to uv sync for reproducible installs."""
    assert "--frozen" in _read(DOCKERFILE)


def test_dockerfile_uv_sync_is_no_dev():
    """--no-dev flag is passed to uv sync so dev dependencies are not installed."""
    assert "--no-dev" in _read(DOCKERFILE)


def test_dockerfile_creates_useradd():
    """useradd is called to create a non-root user."""
    assert "useradd" in _read(DOCKERFILE)


def test_dockerfile_creates_appuser():
    """The non-root user is named appuser."""
    assert "appuser" in _read(DOCKERFILE)


def test_dockerfile_appuser_has_uid_1000():
    """appuser is created with UID 1000 for predictable volume permissions on Linux hosts."""
    assert "--uid 1000" in _read(DOCKERFILE)


def test_dockerfile_switches_to_appuser():
    """USER appuser instruction drops privileges before the CMD runs."""
    assert "USER appuser" in _read(DOCKERFILE)


def test_dockerfile_sets_hf_home():
    """HF_HOME environment variable is set to control the HuggingFace model cache path."""
    assert "HF_HOME" in _read(DOCKERFILE)


def test_dockerfile_predownloads_sentence_transformer():
    """SentenceTransformer is imported at build time to pre-download the model."""
    assert "SentenceTransformer" in _read(DOCKERFILE)


def test_dockerfile_predownloads_correct_model():
    """The all-MiniLM-L6-v2 model is the one pre-downloaded at build time."""
    assert "all-MiniLM-L6-v2" in _read(DOCKERFILE)


def test_dockerfile_has_healthcheck():
    """A HEALTHCHECK directive is present in the Dockerfile."""
    assert "HEALTHCHECK" in _read(DOCKERFILE)


def test_dockerfile_healthcheck_uses_stcore_endpoint():
    """The health check polls Streamlit's built-in /_stcore/health endpoint."""
    assert "/_stcore/health" in _read(DOCKERFILE)


def test_dockerfile_exposes_8501():
    """Port 8501 is declared via EXPOSE for the Streamlit server."""
    assert "EXPOSE 8501" in _read(DOCKERFILE)


def test_dockerfile_cmd_uses_headless():
    """--server.headless is passed in CMD so Streamlit runs without a browser."""
    assert "--server.headless" in _read(DOCKERFILE)


def test_dockerfile_cmd_binds_all_interfaces():
    """0.0.0.0 is used as the server address so the container is reachable externally."""
    assert "0.0.0.0" in _read(DOCKERFILE)


def test_dockerfile_fixes_cache_ownership():
    """chown -R appuser is run to give appuser ownership of the pre-downloaded model cache."""
    assert "chown -R appuser" in _read(DOCKERFILE)


# ---------------------------------------------------------------------------
# docker-compose.yml tests
# ---------------------------------------------------------------------------


def test_compose_file_exists():
    """docker-compose.yml is present at the repository root."""
    assert COMPOSE_FILE.exists(), "docker-compose.yml not found at repo root"


def test_compose_is_valid_yaml():
    """docker-compose.yml can be parsed as valid YAML without errors."""
    parsed = _compose()
    assert isinstance(parsed, dict)


def test_compose_has_app_service():
    """The `app` service is declared in the compose file."""
    parsed = _compose()
    assert "app" in parsed["services"]


def test_compose_app_port_mapping():
    """The app service maps host port 8501 to container port 8501."""
    ports = _compose()["services"]["app"]["ports"]
    assert "8501:8501" in ports


def test_compose_app_env_file():
    """The app service uses env_file to inject secrets from .env into the container."""
    env_file = _compose()["services"]["app"]["env_file"]
    # env_file may be a string or a list; normalise to list for the assertion
    if isinstance(env_file, str):
        env_file = [env_file]
    assert ".env" in env_file


def test_compose_app_volume_mount():
    """The app service mounts the named vectordb volume at /app/vectorDB."""
    volumes = _compose()["services"]["app"]["volumes"]
    assert "vectordb:/app/vectorDB" in volumes


def test_compose_app_restart_policy():
    """The app service restarts automatically unless explicitly stopped."""
    assert _compose()["services"]["app"]["restart"] == "unless-stopped"


def test_compose_app_has_healthcheck():
    """The app service declares a healthcheck block."""
    assert "healthcheck" in _compose()["services"]["app"]


def test_compose_app_healthcheck_uses_stcore_endpoint():
    """The compose healthcheck polls Streamlit's built-in /_stcore/health endpoint."""
    test_field = str(_compose()["services"]["app"]["healthcheck"]["test"])
    assert "_stcore/health" in test_field


def test_compose_has_vector_builder_service():
    """The vector-builder service is declared in the compose file."""
    assert "vector-builder" in _compose()["services"]


def test_compose_vector_builder_has_build_profile():
    """The vector-builder service is guarded by the `build` profile so it does not start by default."""
    profiles = _compose()["services"]["vector-builder"]["profiles"]
    assert "build" in profiles


def test_compose_vector_builder_command_runs_creator():
    """The vector-builder command invokes vector_store_creator.py."""
    command = _compose()["services"]["vector-builder"]["command"]
    assert "vector_store_creator.py" in command


def test_compose_vector_builder_mounts_data_readonly():
    """The vector-builder mounts ./data as read-only so it cannot modify source files."""
    volumes = _compose()["services"]["vector-builder"]["volumes"]
    assert "./data:/app/data:ro" in volumes


def test_compose_vector_builder_mounts_vectordb():
    """The vector-builder mounts the named vectordb volume to persist the built index."""
    volumes = _compose()["services"]["vector-builder"]["volumes"]
    assert "vectordb:/app/vectorDB" in volumes


def test_compose_top_level_volumes_declares_vectordb():
    """The top-level volumes section declares the vectordb named volume."""
    assert "vectordb" in _compose()["volumes"]
