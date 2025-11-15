import logging
from typing import Any, Optional, Tuple

from core.keyboards import (
    back_to_menu_markup,
    main_keyboard_markup,
    action_menu_markup,
    action_schedule_menu_markup,
    action_schedule_remove_menu_markup,
)
from core.models import Task, Schedule


def derive_user_id(ce: Any) -> Optional[str]:
    """Try several plausible locations for the user id in a callback-like object."""
    for path in (
        ("callback", "user_id"),
        ("sender", "user_id"),
        ("message", "sender", "user_id"),
        ("message", "recipient", "user_id"),
    ):
        obj = ce
        try:
            for p in path:
                obj = getattr(obj, p, None)
                if obj is None:
                    break
            else:
                if isinstance(obj, (int, str)):
                    return str(obj)
        except Exception:
            continue
    return None


def derive_chat_id(ce: Any) -> Optional[str]:
    """Try common locations for chat id inside callback/message objects."""
    for path in (
        ("message", "recipient", "chat_id"),
        ("message", "chat", "chat_id"),
        ("message", "recipient", "user_id"),
        ("sender", "user_id"),
    ):
        obj = ce
        try:
            for p in path:
                obj = getattr(obj, p, None)
                if obj is None:
                    break
            else:
                if isinstance(obj, (int, str)):
                    return str(obj)
        except Exception:
            continue
    return None


def extract_payload(obj: Any) -> Tuple[Optional[str], Optional[str]]:
    """Attempt to find payload/data/value in several common places. Returns (value, where)."""
    if obj is None:
        return None, None
    for name in ("payload", "data", "value"):
        v = getattr(obj, name, None)
        if isinstance(v, str):
            return v, f".{name}"
    btn = getattr(obj, "button", None)
    if btn is not None:
        for name in ("payload", "data", "value"):
            v = getattr(btn, name, None)
            if isinstance(v, str):
                return v, ".button." + name
    try:
        if isinstance(obj, dict):
            for name in ("payload", "data", "value"):
                if name in obj and isinstance(obj[name], str):
                    return obj[name], f"[{name}]"
    except Exception:
        pass
    return None, None


async def deep_search(obj: Any, max_depth: int = 4, path: str = "root") -> Tuple[Optional[str], Optional[str]]:
    """Recursively search for payload/data/value inside nested objects/dicts/lists."""
    if max_depth < 0 or obj is None:
        return None, None
    if isinstance(obj, str):
        return None, None
    try:
        dump = None
        if hasattr(obj, 'model_dump'):
            dump = obj.model_dump()
        elif hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
            dump = obj.dict()
        elif isinstance(obj, dict):
            dump = obj
        else:
            dump = None
    except Exception:
        dump = None

    if isinstance(dump, dict):
        for k, v in dump.items():
            if k in ("payload", "data", "value") and isinstance(v, str):
                return v, f"{path}[{k}]"
        for k, v in dump.items():
            found, where = await deep_search(v, max_depth - 1, f"{path}[{k}]")
            if found:
                return found, where

    if isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            found, where = await deep_search(item, max_depth - 1, f"{path}[{idx}]")
            if found:
                return found, where

    for attr in ("callback", "data", "payload", "button"):
        if hasattr(obj, attr):
            try:
                sub = getattr(obj, attr)
            except Exception:
                sub = None
            if sub is not None:
                found, where = await deep_search(sub, max_depth - 1, f"{path}.{attr}")
                if found:
                    return found, where

    return None, None


async def respond(callback_event: Any, text: str, attachments=None, parse_mode=None):
    """
    Умная функция ответа: сначала пытается редактировать исходное сообщение,
    если не получается - отправляет новое.
    """
    try:
        # Сначала пытаемся отредактировать исходное сообщение
        msg = getattr(callback_event, 'message', None)
        if msg and hasattr(msg, 'edit'):
            try:
                kwargs = {"text": text}
                if attachments:
                    kwargs["attachments"] = attachments
                if parse_mode:
                    kwargs["parse_mode"] = parse_mode
                    
                await msg.edit(**kwargs)
                logging.debug("Successfully edited message via callback")
                return
            except Exception as edit_error:
                logging.debug(f"Message edit failed: {edit_error}")
                # Продолжаем к отправке нового сообщения
                pass
        
        # Если редактирование не удалось, отправляем новое сообщение
        if hasattr(callback_event, 'message') and hasattr(callback_event.message, 'answer'):
            kwargs = {"text": text}
            if attachments:
                kwargs["attachments"] = attachments
            if parse_mode:
                kwargs["parse_mode"] = parse_mode
                
            await callback_event.message.answer(**kwargs)
            logging.debug("Sent new message via callback")
            return
            
        # Последняя попытка - через бот API
        if hasattr(callback_event, 'bot') and msg:
            message_id = getattr(msg, 'id', None)
            if message_id:
                await callback_event.bot.edit_message(
                    message_id=message_id,
                    text=text,
                    parse_mode=parse_mode
                )
                logging.debug("Edited message via bot API")
                return
                
    except Exception as e:
        logging.error(f"All attempts to respond failed: {e}")
        # В крайнем случае пытаемся отправить простое сообщение
        try:
            await callback_event.message.answer(text)
        except Exception:
            logging.exception("Final fallback also failed")
