# Contexto de build: raíz del repositorio (compose.yaml y Railway).
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Se conserva la estructura del repo (/repo/apps/api, /repo/fixtures) que asume la config.
WORKDIR /repo/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/ ./
COPY fixtures/ /repo/fixtures/
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 app
USER app

ENV PATH="/repo/apps/api/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
# Las migraciones se aplican antes de servir; con varias réplicas moverlas a un pre-deploy.
CMD ["sh", "-c", "alembic upgrade head && uvicorn eleven.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
