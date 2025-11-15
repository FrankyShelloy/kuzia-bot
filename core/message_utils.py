"""
Утилиты для управления сообщениями бота
"""
import logging
from typing import Dict, Optional

# Простое хранилище для отслеживания последних сообщений по типу
_last_messages: Dict[str, str] = {}

def save_message_id(chat_id: str, message_type: str, message_id: str):
    """Сохранить ID сообщения для возможного редактирования"""
    key = f"{chat_id}_{message_type}"
    _last_messages[key] = message_id
    logging.debug(f"Saved message {message_id} for {message_type} in chat {chat_id}")

def get_last_message_id(chat_id: str, message_type: str) -> Optional[str]:
    """Получить ID последнего сообщения данного типа для редактирования"""
    key = f"{chat_id}_{message_type}"
    return _last_messages.get(key)

def clear_message_id(chat_id: str, message_type: str):
    """Очистить сохраненный ID сообщения"""
    key = f"{chat_id}_{message_type}"
    _last_messages.pop(key, None)
    logging.debug(f"Cleared message for {message_type} in chat {chat_id}")

async def smart_send_or_edit(bot, event, text: str, chat_id: str, message_type: str = "general", 
                           attachments=None, parse_mode=None) -> bool:
    """
    Попытаться отредактировать предыдущее сообщение или отправить новое
    
    Returns:
        True если сообщение было отредактировано, False если отправлено новое
    """
    # Пытаемся найти сообщение для редактирования
    last_message_id = get_last_message_id(chat_id, message_type)
    
    if last_message_id:
        try:
            # Пытаемся отредактировать
            kwargs = {
                "message_id": last_message_id,
                "text": text
            }
            if parse_mode:
                kwargs["parse_mode"] = parse_mode
            if attachments:
                kwargs["attachments"] = attachments
                
            await bot.edit_message(**kwargs)
            logging.debug(f"Successfully edited message {last_message_id}")
            return True
        except Exception as e:
            logging.debug(f"Failed to edit message {last_message_id}: {e}")
            # Очищаем недействительный ID
            clear_message_id(chat_id, message_type)
    
    # Отправляем новое сообщение
    try:
        kwargs = {"text": text}
        if attachments:
            kwargs["attachments"] = attachments
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
            
        sent_msg = await event.message.answer(**kwargs)
        
        # Сохраняем ID нового сообщения для будущего редактирования
        if hasattr(sent_msg, 'id'):
            save_message_id(chat_id, message_type, sent_msg.id)
        
        logging.debug(f"Sent new message for {message_type}")
        return False
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
        return False