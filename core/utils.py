import os
import time
from datetime import datetime
from typing import Optional
import pytz


IGNORE_HISTORY_ON_START = os.getenv("IGNORE_HISTORY_ON_START", "1") in ("1", "true", "True")
STARTUP_AGE_SECONDS = int(os.getenv("STARTUP_AGE_SECONDS", "3"))
STARTUP_TS: float = 0.0

_ALLOWED_IDS_RAW = os.getenv("ALLOWED_IDS", "").strip()
ALLOWED_IDS = set()
if _ALLOWED_IDS_RAW:
    for token in _ALLOWED_IDS_RAW.split(','):
        t = token.strip()
        if t:
            ALLOWED_IDS.add(t)


def _to_timestamp(val):
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)
    except Exception:
        pass
    try:
        import datetime
        if isinstance(val, datetime.datetime):
            return float(val.timestamp())
    except Exception:
        pass
    try:
        s = str(val)
        return float(s)
    except Exception:
        return None


def _extract_timestamp_from_message_event(event) -> Optional[float]:
    if event is None:
        return None
    msg = getattr(event, 'message', None)
    if msg is None:
        return None
    for attr in ("created_at", "date", "timestamp", "time", "sent_at"):
        try:
            v = getattr(msg, attr, None)
            ts = _to_timestamp(v)
            if ts is not None:
                return ts
        except Exception:
            continue
    try:
        body = getattr(msg, 'body', None)
        if body is not None:
            v = getattr(body, 'created_at', None)
            ts = _to_timestamp(v)
            if ts is not None:
                return ts
    except Exception:
        pass
    return None


def _extract_timestamp_from_callback(callback_event) -> Optional[float]:
    if callback_event is None:
        return None
    try:
        msg = getattr(callback_event, 'message', None)
        if msg is not None:
            for attr in ("created_at", "date", "timestamp", "time", "sent_at"):
                v = getattr(msg, attr, None)
                ts = _to_timestamp(v)
                if ts is not None:
                    return ts
    except Exception:
        pass
    try:
        cb = getattr(callback_event, 'callback', None) or getattr(callback_event, 'data', None) or getattr(callback_event, 'payload', None)
        if cb is not None:
            for attr in ("created_at", "date", "timestamp", "time", "sent_at"):
                v = getattr(cb, attr, None)
                ts = _to_timestamp(v)
                if ts is not None:
                    return ts
    except Exception:
        pass
    return None


def _is_too_old_event_ts(ts: Optional[float]) -> bool:
    if not IGNORE_HISTORY_ON_START:
        return False
    if not STARTUP_TS:
        return False
    if ts is None:
        return False
    return ts < (STARTUP_TS - STARTUP_AGE_SECONDS)


def should_ignore_message_event_on_start(event) -> bool:
    ts = _extract_timestamp_from_message_event(event)
    if ts is None:
        return False
    return _is_too_old_event_ts(ts)


def should_ignore_callback_event_on_start(callback_event) -> bool:
    ts = _extract_timestamp_from_callback(callback_event)
    if ts is None:
        return False
    return _is_too_old_event_ts(ts)


def _is_allowed_user_chat(user_id: Optional[str], chat_id: Optional[str]) -> bool:
    if not ALLOWED_IDS:
        return True
    if user_id and str(user_id) in ALLOWED_IDS:
        return True
    if chat_id and str(chat_id) in ALLOWED_IDS:
        return True
    return False


def is_event_allowed(event) -> bool:
    try:
        user_id = str(event.message.sender.user_id)
    except Exception:
        user_id = None
    try:
        chat_id = _resolve_chat_id(event)
    except Exception:
        chat_id = None
    return _is_allowed_user_chat(user_id, chat_id)


def is_callback_allowed(callback_event) -> bool:
    try:
        user_id = None
        try:
            user_id = str(callback_event.message.sender.user_id)
        except Exception:
            user_id = None
        chat_id = None
        try:
            chat_id = callback_event.message.recipient.chat_id
        except Exception:
            chat_id = None
        if chat_id is None:
            try:
                chat_id = str(callback_event.message.sender.user_id)
            except Exception:
                chat_id = None
    except Exception:
        user_id = None
        chat_id = None
    return _is_allowed_user_chat(user_id, chat_id)


def _resolve_chat_id(event) -> str:
    recipient = event.message.recipient
    chat_id: Optional[int] = recipient.chat_id
    if chat_id is None and event.chat is not None:
        chat_id = getattr(event.chat, "chat_id", None)
    if chat_id is None:
        chat_id = recipient.user_id or event.message.sender.user_id
    return str(chat_id)


def get_valid_timezones() -> list:
    """Получить список всех доступных временных зон."""
    return pytz.all_timezones


def is_valid_timezone(tz_name: str) -> bool:
    """Проверить, является ли строка действительной временной зоной."""
    try:
        pytz.timezone(tz_name)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def get_timezone_offset(tz_name: str) -> Optional[str]:
    """Получить текущий UTC offset для временной зоны."""
    try:
        tz = pytz.timezone(tz_name)
        offset = datetime.now(tz).strftime('%z')
        hours = offset[:3]
        minutes = offset[3:]
        return f"UTC{hours}:{minutes}" if hours != "UTC" else f"UTC{hours[:-2]}:{minutes}"
    except Exception:
        return None


def find_timezone_by_keyword(keyword: str) -> Optional[str]:
    """Найти временную зону по ключевому слову (город, страна)."""
    keyword = keyword.lower().strip()
    
    # Список популярных временных зон по русским названиям
    popular_timezones = {
        "москва": "Europe/Moscow",
        "мск": "Europe/Moscow",
        "санкт-петербург": "Europe/Moscow",
        "питер": "Europe/Moscow",
        "киев": "Europe/Kyiv",
        "украина": "Europe/Kyiv",
        "нью-йорк": "America/New_York",
        "сша": "America/New_York",
        "лондон": "Europe/London",
        "англия": "Europe/London",
        "берлин": "Europe/Berlin",
        "германия": "Europe/Berlin",
        "париж": "Europe/Paris",
        "франция": "Europe/Paris",
        "токио": "Asia/Tokyo",
        "япония": "Asia/Tokyo",
        "пекин": "Asia/Shanghai",
        "китай": "Asia/Shanghai",
        "индия": "Asia/Kolkata",
        "дубай": "Asia/Dubai",
        "сингапур": "Asia/Singapore",
        "сидней": "Australia/Sydney",
        "австралия": "Australia/Sydney",
        "бангкок": "Asia/Bangkok",
        "таиланд": "Asia/Bangkok",
    }
    
    # Проверяем словарь популярных зон
    if keyword in popular_timezones:
        return popular_timezones[keyword]
    
    # Ищем в списке всех зон
    for tz in pytz.all_timezones:
        if keyword in tz.lower():
            return tz
    
    return None


def format_timezone_list() -> str:
    """Форматировать список популярных временных зон для отправки пользователю."""
    popular = [
        "Europe/Moscow (Москва, +03:00)",
        "Europe/Kyiv (Киев, +02:00/+03:00)",
        "Europe/London (Лондон, GMT/BST)",
        "Europe/Paris (Париж, CET/CEST)",
        "America/New_York (Нью-Йорк, EST/EDT)",
        "Asia/Tokyo (Токио, JST)",
        "Asia/Shanghai (Пекин, CST)",
        "Asia/Kolkata (Индия, IST)",
        "Australia/Sydney (Сидней, AEDT/AEST)",
        "Asia/Dubai (Дубай, GST)",
    ]
    return "\n".join(popular)


# ════════════════════════════════════════════════════════════════════
# ФУНКЦИИ ДЛЯ РАБОТЫ С НАПОМИНАНИЯМИ (REMINDER NOTIFICATIONS)
# ════════════════════════════════════════════════════════════════════

def get_reminder_presets() -> dict:
    """Получить список предустановленных времён напоминания."""
    return {
        0: "Не напоминать",
        15: "За 15 минут",
        30: "За 30 минут",
        60: "За 1 час",
        120: "За 2 часа",
        360: "За 6 часов",
        1440: "За 1 день",
        2880: "За 2 дня",
        10080: "За 1 неделю",
    }


def format_reminder_presets() -> str:
    """Форматировать список предустановок для пользователя."""
    presets = get_reminder_presets()
    lines = []
    for minutes, label in presets.items():
        if minutes > 0:
            lines.append(f"{minutes}. {label}")
    return "\n".join(lines)


def is_valid_reminder_minutes(minutes: int) -> bool:
    """Проверить, является ли значение корректным временем напоминания."""
    # Разрешаем 0 (без напоминания) и любые значения от 1 до 10080 минут (1 неделя)
    if minutes == 0:
        return True
    if 1 <= minutes <= 10080:
        return True
    return False


def minutes_to_human_readable(minutes: int) -> str:
    """Конвертировать минуты в человеческий формат."""
    if minutes == 0:
        return "Не напоминать"
    
    if minutes < 60:
        return f"{minutes} минут" if minutes % 10 != 1 else f"{minutes} минута"
    elif minutes < 1440:
        hours = minutes // 60
        return f"{hours} час" if hours == 1 else f"{hours} часов"
    elif minutes < 10080:
        days = minutes // 1440
        return f"{days} день" if days == 1 else f"{days} дней"
    else:
        weeks = minutes // 10080
        return f"{weeks} неделя" if weeks == 1 else f"{weeks} недель"
