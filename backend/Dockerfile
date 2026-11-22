# Backend image. Build from the REPOSITORY ROOT so the shared packages are in the context:
#   docker build -f backend/Dockerfile -t clouddesk-backend .
# Base images are pinned by tag only: pin by digest before production.

# ---- builder: resolve and install locked dependencies with uv ----
FROM python:3.12-slim AS builder
# Pin by digest before production (tool versions are pinned here).
RUN pip install --no-cache-dir uv==0.10.7
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- runtime: venv and source only, no uv, no build tools ----
FROM python:3.12-slim AS runtime
# Pin by digest before production.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/backend:/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 app && mkdir -p /app/data && chown app:app /app /app/data
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Only the packages that exist today. When agents/ and memory/ land, add their COPY lines.
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app rag/ ./rag/
COPY --chown=app:app integrations/ ./integrations/
COPY --chown=app:app sample_data/ ./sample_data/
COPY --chown=app:app database/ ./database/
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
