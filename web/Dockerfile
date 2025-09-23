# ================================
# Stage 1 — development
# ================================
FROM node:20-alpine AS dev

WORKDIR /app

# Установим зависимости
COPY package*.json ./
COPY scripts ./scripts 
RUN npm install

# Копируем исходники
COPY . .

# Экспонируем порт для vite dev server
EXPOSE 5173

# Запуск в режиме разработки
CMD ["npm", "run", "dev", "--", "--host"]

# ================================
# Stage 2 — production
# ================================
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Сборка фронта
RUN npm run build

# ================================
# Stage 3 — production server
# ================================
FROM node:20-alpine AS prod

WORKDIR /app

# Установим express только для прод-сервера
RUN npm install express serve-static

# Скопируем билд
COPY --from=build /app/dist ./dist

# Простейший express-сервер
COPY <<EOF server.js
import express from 'express';
import serveStatic from 'serve-static';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();

app.use(serveStatic(join(__dirname, 'dist')));

app.listen(3000, () => {
  console.log('🚀 Web app running at http://localhost:3000');
});
EOF

EXPOSE 3000

CMD ["node", "server.js"]
