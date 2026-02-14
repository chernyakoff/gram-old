# ---------- base stage ----------
FROM python:3.13-slim AS base
WORKDIR /app

# Install uv (package manager)
RUN pip install --no-cache-dir uv

# Copy only dependency metadata
COPY app/pyproject.toml app/uv.lock ./

# Install production dependencies
RUN uv sync --frozen --no-dev

# ---------- dev stage ----------
FROM base AS dev
RUN uv sync --frozen --dev
# Code is mounted via volume in docker compose (no COPY needed).

# ---------- prod stage ----------
FROM base AS prod
COPY app/ ./
CMD ["uv", "run", "python", "-m", "api"]

