#!/bin/sh
set -e

# root credentials
export MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
export MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}

# старт MinIO в фоне
minio server /data --console-address ":9001" &
MINIO_PID=$!

# ждём готовности
until curl -s http://127.0.0.1:9000/minio/health/ready; do
    echo "Waiting for MinIO..."
    sleep 2
done

echo "MinIO is ready!"

# Настройка mc alias (без проверки)
mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# Переменные S3
ACCESS_KEY=${S3_ACCESS_KEY:-defaultaccesskey}
SECRET_KEY=${S3_SECRET_KEY:-defaultsecretkey}

# Создаём пользователя / access key (для root)
mc admin accesskey create local "$MINIO_ROOT_USER" \
    --access-key "$ACCESS_KEY" \
    --secret-key "$SECRET_KEY" || true

# Прикрепляем встроенную политику readwrite
mc admin policy attach local readwrite --user "$ACCESS_KEY" || true

# Создаём бакеты, если их нет
for bucket in media service; do
    mc ls local/$bucket >/dev/null 2>&1 || mc mb local/$bucket
done

mc anonymous set download local/media

echo "Initialization complete!"

wait $MINIO_PID
