#!/bin/sh
set -e

# root credentials
export MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
export MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}

# старт MinIO в фоне
minio server /data --address ":9000" --console-address ":9001" &
MINIO_PID=$!

# ждём готовности MinIO
echo "Waiting for MinIO to start..."
until curl -s http://127.0.0.1:9000/minio/health/ready >/dev/null 2>&1; do
    echo "Still waiting..."
    sleep 2
done

echo "MinIO is ready!"

# настройка mc для локального подключения (НЕ через PUBLIC_URL!)
mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# создаём access key
ACCESS_KEY=${S3_ACCESS_KEY:-defaultaccesskey}
SECRET_KEY=${S3_SECRET_KEY:-defaultsecretkey}

echo "Creating service account..."
mc admin user svcacct add local "$MINIO_ROOT_USER" \
    --access-key "$ACCESS_KEY" \
    --secret-key "$SECRET_KEY" || echo "Service account already exists"

# создаём бакеты
echo "Creating buckets..."
for bucket in media service; do
    mc ls local/$bucket >/dev/null 2>&1 || mc mb local/$bucket
done

# публичный доступ для media
mc anonymous set download local/media

echo "Initialization complete!"

# держим процесс MinIO активным
wait $MINIO_PID