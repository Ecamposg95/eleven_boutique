FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra postgres
COPY . .

# Migra, siembra lo base (idempotente: nunca toca filas existentes) y arranca. Escucha en :: para la red privada de Railway (IPv6).
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.import_brands && python -m scripts.seed_base && exec uvicorn app.main:app --host :: --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
