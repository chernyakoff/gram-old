# ---------- base stage ----------
FROM python:3.12-slim AS base
WORKDIR /app

# ставим uv
RUN pip install --no-cache-dir uv

# Копируем только зависимости
COPY pyproject.toml uv.lock ./

# Устанавливаем prod зависимости
RUN uv sync --frozen --no-dev

# ---------- dev stage ----------
FROM base AS dev
# Устанавливаем dev зависимости
RUN uv sync --frozen --dev
# CMD задаём только в compose
# код монтируется через volume, COPY не нужен

# ---------- prod stage ----------
FROM base AS prod
COPY . .
CMD ["uv", "run", "-m", "app"]