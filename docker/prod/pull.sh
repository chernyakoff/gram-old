#!/bin/sh

# Сохраняем текущий каталог
CURR_DIR=$(pwd)

# Находим корень репозитория
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$ROOT" ]; then
    echo "Это не git репозиторий."
    exit 1
fi

# Выполняем pull, не меняя текущий каталог
git -C "$ROOT" pull

# Возвращаться не нужно, так как мы не cd
