# ================================
# Stage 1 — Development
# ================================
FROM node:20-alpine AS dev

WORKDIR /app

# Устанавливаем dev-зависимости
COPY package*.json ./
COPY scripts ./scripts
RUN npm install

# Копируем исходники
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# ================================
# Stage 2 — Build
# ================================
FROM node:20-alpine AS build

WORKDIR /app

# Устанавливаем зависимости (включая dev)
COPY package*.json ./
COPY scripts ./scripts
RUN npm install

# Копируем исходники проекта
COPY . .

# Сборка фронта
RUN npm run build

# ================================
# Stage 3 — Production
# ================================
FROM node:20-alpine AS prod

WORKDIR /app

# Минимизируем образ — ставим только serve
RUN npm install -g serve

# Копируем готовый билд из build-стадии
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:3000"]
