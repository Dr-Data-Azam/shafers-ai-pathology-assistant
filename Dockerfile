# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Install runtime dependencies using uv so the final image stays minimal.
FROM python:3.13-slim AS builder

# Bring in the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only the dependency manifests first — this layer is cached as long as
# pyproject.toml and uv.lock don't change, skipping a full reinstall on code edits.
COPY pyproject.toml uv.lock ./

# Install runtime deps into an in-tree .venv; skip dev extras and project install
# (the project is an app, not a library, so there is nothing to install as a package).
RUN uv sync --frozen --no-dev --no-install-project


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Non-root user — a compromised process cannot gain elevated host access
RUN groupadd -r appuser \
 && useradd -r -g appuser --uid 1000 --create-home appuser

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Activate the venv for all subsequent RUN / CMD instructions
ENV PATH="/app/.venv/bin:$PATH"

# Point HuggingFace libraries at a path we control so the model lands somewhere
# we can chown before switching to the non-root user
ENV HF_HOME=/app/.cache/huggingface

# Pre-download the embedding model at build time so the container starts instantly.
# Runs as root here; ownership is fixed below after the app code is copied.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application source with correct ownership in a single layer
COPY --chown=appuser:appuser . .

# Fix ownership of the model cache downloaded above
RUN chown -R appuser:appuser /app/.cache

# Drop privileges for all runtime activity
USER appuser

EXPOSE 8501

# Docker (and orchestrators) poll this to decide whether the container is healthy.
# Uses the built-in Streamlit health endpoint — no custom route needed.
# start-period gives the app time to initialise before health checks begin.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "\
import urllib.request; \
urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true"]
