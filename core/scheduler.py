# core/scheduler.py
import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from tortoise.functions import Coalesce
from core.models import Schedule
from core.task_manager import mark_expired_tasks
from maxapi import Bot

logger = logging.getLogger(__name__)

WEEKDAY_MAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}  # Понедельник = 0

# Отслеживание отправленных напоминаний (чтобы не отправить дважды)
sent_main_reminders = set()  # {schedule_id}
sent_preliminary_reminders = set()  # {schedule_id}

# Отслеживание ежедневных задач
last_daily_check = None

async def send_reminders(bot: Bot):
    global last_daily_check
    
    now_utc = datetime.now(pytz.UTC)
    current_date = now_utc.date()
    
    logger.info(f"Scheduler check: UTC time={now_utc.strftime('%Y-%m-%d %H:%M:%S')}")

    # Проверяем нужно ли запустить ежедневные задачи
    # Временно для тестирования: запускаем каждый раз
    try:
        logger.info("Running daily tasks (test mode)...")
        expired_count = await mark_expired_tasks()
        logger.info(f"Daily tasks completed. Expired tasks: {expired_count}")
        last_daily_check = current_date
    except Exception as e:
        logger.error(f"Error in daily tasks: {e}", exc_info=True)

    # Ищем ВСЕ включённые расписания (не фильтруем по дню)
    all_schedules = await Schedule.filter(enabled=True).all()

    if not all_schedules:
        logger.debug(f"No enabled schedules found")
        return

    logger.info(f"Found {len(all_schedules)} total enabled schedules")

    for sched in all_schedules:
        try:
            # Валидируем timezone
            try:
                user_tz = pytz.timezone(sched.timezone)
            except Exception as tz_err:
                logger.error(f"Invalid timezone '{sched.timezone}' for schedule {sched.id}: {tz_err}")
                user_tz = pytz.UTC
            
            # Получаем текущее время в timezone пользователя
            local_now = now_utc.astimezone(user_tz)
            local_weekday = local_now.weekday()  # День недели в timezone пользователя
            local_date = local_now.date()
            
            # Проверяем совпадает ли день недели
            if local_weekday != sched.day_of_week:
                logger.debug(f"Schedule {sched.id}: day mismatch (local={local_weekday}, sched={sched.day_of_week}), skip")
                continue
            
            logger.debug(f"Schedule {sched.id}: day match! local_weekday={local_weekday}, sched.day_of_week={sched.day_of_week}")
            
            local_time = local_now.time()
            sched_time = datetime.strptime(sched.time, "%H:%M").time()
            
            logger.info(f"Schedule {sched.id}: text='{sched.text}', local_time={local_time}, sched_time={sched_time}, tz={sched.timezone}, reminder_min={sched.reminder_minutes}")
            
            # Создаём datetime события в локальной зоне
            sched_datetime = local_now.replace(
                hour=sched_time.hour,
                minute=sched_time.minute,
                second=0,
                microsecond=0
            )
            
            # Время разницы в минутах (если отрицательное - событие в будущем)
            time_diff_seconds = (sched_datetime - local_now).total_seconds()
            time_diff_minutes = time_diff_seconds / 60

            logger.info(f"Schedule {sched.id}: time_diff={time_diff_minutes:.1f} min, reminder_minutes={sched.reminder_minutes}")

            # 1. Проверяем основное напоминание (в нужное время ±1 минута)
            if abs(time_diff_seconds) <= 60:
                # Создаём уникальный ключ для отслеживания (включаем дату)
                reminder_key = f"{sched.id}_{local_date}"
                if reminder_key not in sent_main_reminders:
                    try:
                        await bot.send_message(
                            chat_id=int(sched.chat_id),
                            text=f"🔔 НАПОМИНАНИЕ: {sched.text}\n⏰ Время: {sched.time}"
                        )
                        logger.warning(f"✅ SENT MAIN REMINDER: schedule_id={sched.id}, chat_id={sched.chat_id}, text='{sched.text}'")
                        sent_main_reminders.add(reminder_key)
                    except Exception as send_err:
                        logger.error(f"Failed to send main reminder {sched.id}: {send_err}")
                else:
                    logger.debug(f"Main reminder for {sched.id} already sent today")
            else:
                # Если событие прошло, удаляем из отслеживания для следующей недели
                reminder_key = f"{sched.id}_{local_date}"
                if reminder_key in sent_main_reminders:
                    sent_main_reminders.discard(reminder_key)
                    logger.debug(f"Reset main reminder for {sched.id} (event has passed)")

            # 2. Проверяем предварительное напоминание (если установлено)
            if sched.reminder_minutes > 0:
                # Проверяем, совпадает ли время предварительного напоминания (±30 секунд = ±0.5 минуты)
                # Напоминание должно прийти когда time_diff_minutes ≈ reminder_minutes
                reminder_time_diff = time_diff_minutes - sched.reminder_minutes
                logger.info(f"Schedule {sched.id}: reminder_time_diff={reminder_time_diff:.1f} min (threshold ±0.5 min)")
                if abs(reminder_time_diff) <= 0.5:
                    # Создаём уникальный ключ для отслеживания (включаем дату)
                    preliminary_key = f"{sched.id}_{local_date}_prelim"
                    if preliminary_key not in sent_preliminary_reminders:
                        try:
                            from core.utils import minutes_to_human_readable
                            reminder_text = minutes_to_human_readable(sched.reminder_minutes)
                            await bot.send_message(
                                chat_id=int(sched.chat_id),
                                text=f"⏳ ПРЕДВАРИТЕЛЬНОЕ НАПОМИНАНИЕ:\n{sched.text}\n\n⏰ Начало через: {reminder_text}"
                            )
                            logger.warning(f"✅ SENT PRELIMINARY REMINDER: schedule_id={sched.id}, chat_id={sched.chat_id}, in {sched.reminder_minutes} min, text='{sched.text}'")
                            sent_preliminary_reminders.add(preliminary_key)
                        except Exception as send_err:
                            logger.error(f"Failed to send preliminary reminder {sched.id}: {send_err}")
                    else:
                        logger.debug(f"Preliminary reminder for {sched.id} already sent today")
                else:
                    # Если время предварительного напоминания прошло, удаляем из отслеживания
                    preliminary_key = f"{sched.id}_{local_date}_prelim"
                    if preliminary_key in sent_preliminary_reminders:
                        sent_preliminary_reminders.discard(preliminary_key)
                        logger.debug(f"Reset preliminary reminder for {sched.id} (reminder time has passed)")

        except Exception as e:
            logger.error(f"Ошибка напоминания {sched.id}: {e}", exc_info=True)

async def start_scheduler(bot: Bot, interval: int = 30):
    """Запустить scheduler для отправки напоминаний"""
    logger.info(f"Scheduler запущен (интервал проверки: {interval} сек)")
    while True:
        try:
            await send_reminders(bot)
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        await asyncio.sleep(interval)
