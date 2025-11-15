# Makefile для упрощения работы с Docker

.PHONY: build run stop clean logs restart dev

# Переменные
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = kuzia.bot

# Основные команды
build:
	@echo "🏗️  Сборка с кэшированием..."
	DOCKER_BUILDKIT=1 docker compose build --parallel

run: build
	@echo "▶️  Запуск контейнера..."
	docker compose up -d

stop:
	@echo "🛑 Остановка контейнера..."
	docker compose down

restart: stop run
	@echo "🔄 Перезапуск завершен"

logs:
	@echo "📊 Просмотр логов..."
	docker compose logs -f $(SERVICE_NAME)

# Команды разработки
dev:
	@echo "🛠️  Запуск в режиме разработки..."
	DOCKER_BUILDKIT=1 docker compose up --build

clean:
	@echo "🧹 Очистка Docker ресурсов..."
	docker compose down -v --remove-orphans
	docker system prune -f
	docker builder prune -f

# Быстрая пересборка без кэша
rebuild:
	@echo "🔥 Полная пересборка без кэша..."
	DOCKER_BUILDKIT=1 docker compose build --no-cache --parallel

# Проверка статуса
status:
	@echo "📋 Статус контейнеров:"
	docker compose ps

# Вход в контейнер
shell:
	@echo "🐚 Вход в контейнер..."
	docker compose exec $(SERVICE_NAME) /bin/bash

# Помощь
help:
	@echo "🚀 Доступные команды:"
	@echo "  make build     - Собрать образ с кэшированием"
	@echo "  make run       - Собрать и запустить"
	@echo "  make stop      - Остановить контейнер"
	@echo "  make restart   - Перезапустить"
	@echo "  make logs      - Показать логи"
	@echo "  make dev       - Запуск в режиме разработки"
	@echo "  make clean     - Очистить Docker ресурсы"
	@echo "  make rebuild   - Полная пересборка"
	@echo "  make status    - Статус контейнеров"
	@echo "  make shell     - Войти в контейнер"