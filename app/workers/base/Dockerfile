# ---------- base stage ----------
FROM python:3.13-slim AS base
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --frozen --no-dev

# ---------- dev stage ----------
FROM base AS dev
RUN uv sync --frozen --dev

# ---------- prod stage ----------
FROM base AS prod
COPY app/ ./
CMD ["uv", "run", "python", "-m", "workers.base"]

