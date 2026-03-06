# ---------- base stage ----------
FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ставим uv
RUN pip install --no-cache-dir uv

# Копируем только зависимости
COPY pyproject.toml uv.lock ./

# Устанавливаем prod зависимости
RUN uv sync --frozen --no-dev

# ---------- dev stage ----------
FROM base AS dev
RUN uv sync --frozen --dev

# ---------- prod stage ----------
FROM base AS prod
COPY . .
CMD ["uv", "run", "-m", "app"]
