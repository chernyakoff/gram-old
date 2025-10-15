# ================================
# Stage 1 — development
# ================================
FROM node:20-alpine AS dev

WORKDIR /app

# Установим зависимости для разработки
COPY package*.json ./
COPY scripts ./scripts
RUN npm install --include=dev

# Копируем исходники
COPY . .

# Экспонируем порт для vite dev server
EXPOSE 5173

# Запуск в режиме разработки
CMD ["npm", "run", "dev", "--", "--host"]

# ================================
# Stage 2 — production build
# ================================
FROM node:20-alpine AS build

WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./
COPY scripts ./scripts

# Установим все зависимости, включая devDependencies
RUN npm install --include=dev

# Копируем исходники
COPY . .

# Сборка фронта
RUN npm run build

# ================================
# Stage 3 — production server
# ================================
FROM node:20-alpine AS prod

WORKDIR /app

# Установим serve
RUN npm install -g serve

# Скопируем только готовый билд
COPY --from=build /app/dist ./dist

EXPOSE 3000

# Запуск production сервера
CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:3000"]
