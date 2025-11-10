## Kuzia Bot — MAX чат-бот с приёмом задач

Функционал:
- Приём задач командой `/add <текст>`
- Приём задач обычным текстом (любое сообщение без команды)
- Просмотр списка задач `/list`
- Отметка задачи как выполненной `/done <id>`
- Хранение задач в БД (Tortoise ORM, по умолчанию SQLite)

### Требования
- Python 3.10+

### Установка и запуск
1) Клонирование и переход в папку проекта
```bash
git clone <repo-url>
cd kuzia-bot
```

2) Создать и активировать виртуальное окружение
```bash
python -m venv .venv
source .venv/bin/activate
```
На Windows:
```bash
.venv\Scripts\activate
```

3) Установка зависимостей
```bash
pip install -r requirements.txt
```

4) Настройка переменных окружения
- Скопируйте файл `example.env` в `.env` и укажите токен бота:
```bash
cp example.env .env
```
- Заполните `BOT_TOKEN=...`
- Опционально укажите `DB_URL` (по умолчанию `sqlite://db.sqlite3`)

5) Запуск бота (polling)
```bash
python main.py
```

### Использование
- Команда: `/add купить молоко`
- Любой текст без команды сохраняется как задача: `купить хлеб`
- Список задач: `/list`
- Выполнено: `/done 3`

### Конфигурация
- Токен и БД читаются из `core/config.py`:
  - `BOT_TOKEN` — из файла `.env`
  - `DB_URL` — из `.env`, по умолчанию SQLite файл `db.sqlite3` в корне

### Полезные ссылки
- Документация maxapi и примеры: `https://github.com/love-apples/maxapi/tree/main`