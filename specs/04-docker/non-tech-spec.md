# Feature: Docker Containerization

## Problem Statement
The app currently has no containerization, so it runs differently depending on who is running it and on which machine. Developers and end-users must manually install Python, dependencies, and environment variables in exactly the right way. A single missing step or version mismatch breaks the entire setup. Containerizing the app eliminates this fragility and guarantees identical behavior everywhere.

## User Story
As a developer or end-user, I want to run the Shafer's AI Pathology Assistant with a single command so that I do not need to install Python, manage virtual environments, or configure dependencies manually on my machine.

## What It Should Do (Acceptance Criteria)
- When a user runs `docker compose up`, the app starts and is accessible in a browser without any additional setup steps beyond providing a `.env` file.
- When the container is built, it uses a multi-stage Docker build so that the final image contains only what is needed to run the app (no build tools or intermediate artifacts).
- When the container runs, it executes as a non-root user so that a compromised process cannot gain elevated access to the host machine.
- When a health check is performed (e.g., by Docker or an orchestrator), the app exposes a health check endpoint that returns a success response when the app is running correctly.
- When the container restarts or is recreated, the FAISS vector database is preserved because `vectorDB/` is mounted as a named Docker volume — no data is lost.
- When the container starts with a pre-existing `vectorDB/` volume, the app loads the existing index without rebuilding it.
- When environment variables (API keys) are missing from `.env`, the container exits with a clear error message rather than starting in a broken state.
- When the image is built, the `.env` file and `data/` directory are not baked into the image — they are injected at runtime via volume mounts or env files.

## What It Should NOT Do (Constraints)
- Must not change any existing application logic in `streamlit_app.py`, `rag_system.py`, or any other Python module — this feature is infrastructure only.
- Must not bake API keys or secrets into the Docker image at any stage.
- Must not require the user to run `vector_store_creator.py` inside the container as part of the normal `docker compose up` flow — the vector store build step remains a separate, explicit command.
- Must not change the temperature, retrieval parameters, or any RAG behavior.
- Must not run the container process as root.

## Files Likely Affected
- `Dockerfile` — new file; defines the multi-stage build, non-root user, and health check
- `docker-compose.yml` — new file; defines the service, volume mount for `vectorDB/`, env file wiring, and port mapping
- `.dockerignore` — new file; excludes `data/`, `vectorDB/`, `.env`, `__pycache__`, and other non-essential files from the build context
- `streamlit_app.py` — may need a minimal health check route or confirmation that Streamlit's built-in health endpoint (`/_stcore/health`) is sufficient

## Open Questions
- Should the health check use Streamlit's built-in `/_stcore/health` endpoint, or do we add a custom one?
- Should `docker-compose.yml` include a separate one-off service (e.g., `vector-builder`) for running `vector_store_creator.py`, or is that left as a manual `docker exec` step?
- Which port should the app be exposed on externally — Streamlit's default `8501`, or a different host port?
- Should the image be pushed to a container registry (e.g., GitHub Container Registry) as part of the feature, or is that out of scope?
