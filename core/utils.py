import os
import time
from typing import Optional


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
