# core/middleware.py
import time
from maxapi.types import MessageCreated

START_TIME = time.time()

def ignore_old_events(event):
    # Игнорируем события, пришедшие ДО старта бота
    if hasattr(event, 'message') and hasattr(event.message, 'date'):
        if event.message.date < START_TIME - 5:  # 5 секунд запаса
            return True
    return False