# Ультра-оптимизированный multi-stage build для максимального кэширования
FROM python:3.11-slim as dependencies

# Кэшируем системные зависимости
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev

# Обновляем pip и инструменты сборки
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# Копируем только requirements.txt для максимального кэширования
COPY requirements.txt /tmp/

# Устанавливаем зависимости с кэшированием pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/opt/venv -r /tmp/requirements.txt

# Production stage - минимальный размер
FROM python:3.11-slim

# Копируем установленные пакеты
COPY --from=dependencies /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH="/opt/venv/lib/python3.11/site-packages"

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 botuser

# Переключаемся на пользователя и создаем рабочую директорию
USER botuser
WORKDIR /app

# Переменные окружения для оптимизации
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_URL=sqlite:///app/data/db.sqlite3

# Копируем код последним для лучшего кэширования
COPY --chown=botuser:botuser . .

# Создание директории для данных с правильными правами
RUN mkdir -p /app/data && chmod 755 /app/data

# Команда запуска
CMD ["python", "main.py"]