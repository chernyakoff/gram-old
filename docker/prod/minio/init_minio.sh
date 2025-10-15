#!/bin/sh
set -e

# root credentials
export MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
export MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}

# публичный URL для Traefik
PUBLIC_URL=${MINIO_PUBLIC_URL:-https://mi.lidorub.online}

# старт MinIO
minio server /data --address ":9000" --console-address ":9001" &
MINIO_PID=$!

# ждём готовности
until curl -s http://127.0.0.1:9000/minio/health/ready; do
    echo "Waiting for MinIO..."
    sleep 2
done

echo "MinIO is ready!"

# настройка mc
mc alias set local "$PUBLIC_URL" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# создаём access key
ACCESS_KEY=${S3_ACCESS_KEY:-defaultaccesskey}
SECRET_KEY=${S3_SECRET_KEY:-defaultsecretkey}

mc admin accesskey create local "$MINIO_ROOT_USER" \
    --access-key "$ACCESS_KEY" \
    --secret-key "$SECRET_KEY" || true

mc admin policy attach local readwrite --user "$ACCESS_KEY" || true

# создаём бакеты
for bucket in media service; do
    mc ls local/$bucket >/dev/null 2>&1 || mc mb local/$bucket
done

mc anonymous set download local/media

echo "Initialization complete!"

wait $MINIO_PID
