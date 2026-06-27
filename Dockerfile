# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile
#
# Builds the Docker image used by both `api` and `worker` services.
# Same image, different startup commands (uvicorn vs celery).
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies for building python packages (e.g., psycopg2)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Force uv to use python 3.12
ENV UV_PYTHON=3.12

# Install dependencies (frozen means it won't update uv.lock, similar to npm ci)
RUN uv sync --frozen --no-dev

# Copy the application code
COPY . .

# Create a non-root user (security best practice)
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Expose FastAPI port (only used by the api service, not worker)
EXPOSE 8000
