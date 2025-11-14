"""
Управление жизненным циклом задач: просрочка, очистка и автоматические действия.
"""
import logging
from datetime import datetime, timedelta, time
import pytz
from core.models import Task, UserSettings


async def increment_completed_tasks_counter(chat_id: str, count: int = 1):
    """
    Увеличивает счетчик выполненных задач для пользователя.
    Этот счетчик не сбрасывается при удалении задач.
    """
    try:
        # Получаем или создаем настройки пользователя
        user_settings = await UserSettings.filter(chat_id=chat_id).first()
        if not user_settings:
            # Создаем новые настройки если не существует
            user_settings = await UserSettings.create(
                user_id=chat_id,  # Временно используем chat_id как user_id
                chat_id=chat_id,
                total_completed_tasks=count
            )
        else:
            # Увеличиваем счетчик
            user_settings.total_completed_tasks += count
            await user_settings.save(update_fields=["total_completed_tasks", "updated_at"])
        
        logging.info(f"Chat {chat_id}: incremented completed tasks counter by {count}, total: {user_settings.total_completed_tasks}")
        return user_settings.total_completed_tasks
        
    except Exception as e:
        logging.exception(f"Error incrementing completed tasks counter for chat {chat_id}: {e}")
        return 0


async def get_total_completed_tasks(chat_id: str) -> int:
    """
    Получает общее количество выполненных задач для пользователя.
    """
    try:
        user_settings = await UserSettings.filter(chat_id=chat_id).first()
        if user_settings:
            return user_settings.total_completed_tasks
        return 0
    except Exception as e:
        logging.exception(f"Error getting completed tasks counter for chat {chat_id}: {e}")
        return 0

# Время ежедневного сброса задач в просроченные (по локальному времени пользователя)
TASK_RESET_TIME = time(3, 17)  # 3:05 утра

async def mark_expired_tasks():
    """
    Ежедневная функция для перевода невыполненных задач в статус 'expired'.
    Сбрасывает все pending задачи в TASK_RESET_TIME по часовому поясу пользователя.
    """
    try:
        now_utc = datetime.now(pytz.UTC)
        logging.info(f"Starting mark_expired_tasks at UTC: {now_utc}")
        
        # Получаем все уникальные чаты с pending задачами
        pending_tasks = await Task.filter(status="pending").all()
        logging.info(f"Found {len(pending_tasks)} pending tasks in database")
        
        if not pending_tasks:
            logging.info("No pending tasks to check for expiration")
            return 0
        
        # Группируем задачи по chat_id
        tasks_by_chat = {}
        for task in pending_tasks:
            if task.chat_id not in tasks_by_chat:
                tasks_by_chat[task.chat_id] = []
            tasks_by_chat[task.chat_id].append(task)
        
        total_expired = 0
        
        for chat_id, chat_tasks in tasks_by_chat.items():
            try:
                # Получаем часовой пояс пользователя
                user_settings = await UserSettings.filter(chat_id=chat_id).first()
                if user_settings and user_settings.timezone:
                    user_tz_name = user_settings.timezone
                else:
                    user_tz_name = "UTC"
                
                try:
                    user_tz = pytz.timezone(user_tz_name)
                except Exception:
                    logging.warning(f"Invalid timezone '{user_tz_name}' for chat {chat_id}, using UTC")
                    user_tz = pytz.UTC
                
                # Получаем текущее время в часовом поясе пользователя
                local_now = now_utc.astimezone(user_tz)
                local_time = local_now.time()
                
                # Проверяем, прошло ли время сброса
                # Сбрасываем задачи если сейчас после времени сброса и задача была создана до сегодняшнего времени сброса
                reset_time = TASK_RESET_TIME
                
                if local_time >= reset_time:
                    # Если сейчас после времени сброса, то задачи созданные до сегодняшнего времени сброса должны быть просрочены
                    today_reset_datetime = local_now.replace(hour=TASK_RESET_TIME.hour, minute=TASK_RESET_TIME.minute, second=0, microsecond=0)
                else:
                    # Если сейчас до времени сброса, то задачи созданные до вчерашнего времени сброса должны быть просрочены  
                    yesterday = local_now - timedelta(days=1)
                    today_reset_datetime = yesterday.replace(hour=TASK_RESET_TIME.hour, minute=TASK_RESET_TIME.minute, second=0, microsecond=0)
                
                # Конвертируем время сброса в UTC для сравнения с created_at
                reset_utc = today_reset_datetime.astimezone(pytz.UTC)
                
                logging.info(f"Chat {chat_id}: timezone={user_tz_name}, local_time={local_time}, reset_cutoff={reset_utc}")
                
                # Сбрасываем задачи созданные до времени сброса
                chat_expired_count = 0
                for task in chat_tasks:
                    if task.created_at < reset_utc:
                        task.status = "expired"
                        task.expired_at = now_utc
                        await task.save(update_fields=["status", "expired_at", "updated_at"])
                        chat_expired_count += 1
                        logging.debug(f"Expired task {task.id}: '{task.text}' (created {task.created_at}, cutoff {reset_utc})")
                
                if chat_expired_count > 0:
                    logging.info(f"Chat {chat_id}: marked {chat_expired_count} tasks as expired")
                
                total_expired += chat_expired_count
                
            except Exception as chat_err:
                logging.exception(f"Error processing tasks for chat {chat_id}: {chat_err}")
                continue
        
        if total_expired > 0:
            logging.info(f"Total marked {total_expired} tasks as expired across all chats")
        else:
            logging.info("No tasks needed to be marked as expired")
            
        return total_expired
        
    except Exception as e:
        logging.exception(f"Error in mark_expired_tasks: {e}")
        return 0


async def clear_all_tasks(chat_id: str) -> int:
    """
    Очистка всех задач для конкретного чата.
    Возвращает количество удаленных задач.
    """
    try:
        # Удаляем все задачи для данного чата
        deleted_count = await Task.filter(chat_id=chat_id).delete()
        
        logging.info(f"Cleared {deleted_count} tasks for chat {chat_id}")
        return deleted_count
        
    except Exception as e:
        logging.exception(f"Error clearing tasks for chat {chat_id}: {e}")
        return 0


async def clear_completed_tasks(chat_id: str) -> int:
    """
    Очистка только выполненных задач для конкретного чата.
    Возвращает количество удаленных задач.
    """
    try:
        # Удаляем только выполненные задачи для данного чата
        deleted_count = await Task.filter(chat_id=chat_id, status="done").delete()
        
        logging.info(f"Cleared {deleted_count} completed tasks for chat {chat_id}")
        return deleted_count
        
    except Exception as e:
        logging.exception(f"Error clearing completed tasks for chat {chat_id}: {e}")
        return 0


async def clear_expired_tasks(chat_id: str) -> int:
    """
    Очистка только просроченных задач для конкретного чата.
    Возвращает количество удаленных задач.
    """
    try:
        # Удаляем только просроченные задачи для данного чата
        deleted_count = await Task.filter(chat_id=chat_id, status="expired").delete()
        
        logging.info(f"Cleared {deleted_count} expired tasks for chat {chat_id}")
        return deleted_count
        
    except Exception as e:
        logging.exception(f"Error clearing expired tasks for chat {chat_id}: {e}")
        return 0


async def get_task_statistics(chat_id: str) -> dict:
    """
    Получение статистики задач для конкретного чата.
    """
    try:
        pending_count = await Task.filter(chat_id=chat_id, status="pending").count()
        done_count = await Task.filter(chat_id=chat_id, status="done").count()
        expired_count = await Task.filter(chat_id=chat_id, status="expired").count()
        
        return {
            "pending": pending_count,
            "done": done_count,
            "expired": expired_count,
            "total": pending_count + done_count + expired_count
        }
        
    except Exception as e:
        logging.exception(f"Error getting task statistics for chat {chat_id}: {e}")
        return {"pending": 0, "done": 0, "expired": 0, "total": 0}