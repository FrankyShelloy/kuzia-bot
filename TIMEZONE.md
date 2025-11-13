# Функция Timezone (Временные зоны)

## Описание

Функция timezone позволяет пользователям установить свою временную зону, которая будет использоваться для отправки напоминаний из расписания.

## Как использовать

### Команда `/timezone`

```
/timezone <название_зоны>
```

### Примеры:

1. **По полному названию зоны:**
   ```
   /timezone Europe/Moscow
   /timezone America/New_York
   /timezone Asia/Tokyo
   ```

2. **По городу/стране (на русском):**
   ```
   /timezone Москва
   /timezone Нью-Йорк
   /timezone Токио
   ```

3. **Без параметров (просмотр текущей зоны):**
   ```
   /timezone
   ```
   Выведет вашу текущую временную зону и справку по использованию.

## Популярные временные зоны

| Город | Зона | UTC Offset |
|-------|------|-----------|
| Москва | Europe/Moscow | UTC+3 |
| Киев | Europe/Kyiv | UTC+2/+3 |
| Лондон | Europe/London | GMT/BST |
| Париж | Europe/Paris | CET/CEST |
| Нью-Йорк | America/New_York | EST/EDT |
| Токио | Asia/Tokyo | JST |
| Пекин | Asia/Shanghai | CST |
| Индия | Asia/Kolkata | IST |
| Сидней | Australia/Sydney | AEDT/AEST |
| Дубай | Asia/Dubai | GST |

## Как это работает

1. **Сохранение настроек:** При установке timezone создаётся запись в таблице `user_settings` с указанной зоной.

2. **Применение к расписанию:** Все текущие и новые записи в расписании получают timezone пользователя.

3. **Использование в напоминаниях:** При проверке расписания бот конвертирует текущее UTC время в timezone пользователя и отправляет напоминание в нужное время.

## База данных

### Таблица `user_settings`

```python
class UserSettings(Model):
    id: int (PK)
    user_id: str (unique, indexed)
    chat_id: str (indexed)
    timezone: str (default="UTC")
    created_at: datetime
    updated_at: datetime
```

### Обновления в таблице `schedules`

Добавлено поле:
```python
timezone: str (default="UTC")
```

## Функции утилит

### `core/utils.py`

- `get_valid_timezones() -> list` — Получить все доступные временные зоны
- `is_valid_timezone(tz_name: str) -> bool` — Проверить, является ли строка действительной зоной
- `get_timezone_offset(tz_name: str) -> Optional[str]` — Получить UTC offset
- `find_timezone_by_keyword(keyword: str) -> Optional[str]` — Найти зону по ключевому слову
- `format_timezone_list() -> str` — Форматировать список популярных зон для пользователя

## Обработчик в `core/handlers.py`

Команда `/timezone` регистрирует обработчик `set_timezone`, который:

1. Получает timezone из аргумента команды
2. Валидирует введённую зону
3. Пытается найти зону по ключевому слову, если точного совпадения нет
4. Сохраняет или обновляет настройки пользователя
5. Обновляет все расписания пользователя с новой timezone
6. Отправляет подтверждение

## Примеры использования

### Установить московское время
```
/timezone Москва
```
или
```
/timezone Europe/Moscow
```

### Установить время Нью-Йорка
```
/timezone Нью-Йорк
```
или
```
/timezone America/New_York
```

### Посмотреть текущую настройку
```
/timezone
```

## Интеграция с другими компонентами

### Scheduler (`core/scheduler.py`)

Функция `send_reminders()` использует timezone из расписания:

```python
user_tz = pytz.timezone(sched.timezone)
local_time = now_utc.astimezone(user_tz).time()
```

Это позволяет отправлять напоминания в правильное время для каждого пользователя независимо от их часового пояса.

## Примечания

- Временная зона по умолчанию: `UTC`
- Изменение timezone автоматически обновляет все расписания пользователя
- Поддерживается все 600+ официальных часовых поясов из базы данных `pytz`
- Функция поиска по ключевому слову работает как на русском, так и на английском языке
