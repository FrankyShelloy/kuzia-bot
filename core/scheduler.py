# core/scheduler.py
import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from tortoise.functions import Coalesce
from core.models import Schedule
from maxapi import Bot

logger = logging.getLogger(__name__)

WEEKDAY_MAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}  # Понедельник = 0

# Отслеживание отправленных напоминаний (чтобы не отправить дважды)
sent_main_reminders = set()  # {schedule_id}
sent_preliminary_reminders = set()  # {schedule_id}

async def send_reminders(bot: Bot):
    now_utc = datetime.now(pytz.UTC)
    current_weekday = now_utc.weekday()  # 0 = понедельник
    current_hour = now_utc.hour
    current_minute = now_utc.minute

    logger.debug(f"Scheduler check: weekday={current_weekday}, UTC time={now_utc.strftime('%H:%M:%S')}")

    # Ищем записи, где день недели совпадает
    schedules = await Schedule.filter(
        enabled=True,
        day_of_week=WEEKDAY_MAP[current_weekday]
    ).all()

    if not schedules:
        logger.debug(f"No schedules found for weekday {current_weekday}")
        return

    logger.info(f"Found {len(schedules)} schedules for weekday {current_weekday}")

    for sched in schedules:
        try:
            user_tz = pytz.timezone(sched.timezone)
            local_now = now_utc.astimezone(user_tz)
            local_time = local_now.time()
            sched_time = datetime.strptime(sched.time, "%H:%M").time()
            
            logger.debug(f"Schedule {sched.id}: local_time={local_time}, sched_time={sched_time}, tz={sched.timezone}")
            
            # Создаём время события в локальной зоне
            sched_datetime = local_now.replace(
                hour=sched_time.hour,
                minute=sched_time.minute,
                second=0,
                microsecond=0
            )
            
            # Время разницы в минутах
            time_diff_seconds = (sched_datetime - local_now).total_seconds()
            time_diff_minutes = time_diff_seconds / 60

            logger.debug(f"Schedule {sched.id}: time_diff={time_diff_minutes:.1f} min, reminder_minutes={sched.reminder_minutes}")

            # 1. Проверяем основное напоминание (в нужное время ±1 минута)
            if abs(time_diff_seconds) <= 60:
                if sched.id not in sent_main_reminders:
                    await bot.send_message(
                        chat_id=int(sched.chat_id),
                        text=f"🔔 НАПОМИНАНИЕ: {sched.text}\n⏰ Время: {sched.time} ({sched.timezone})"
                    )
                    logger.info(f"Основное напоминание отправлено: {sched.id} → {sched.chat_id}")
                    sent_main_reminders.add(sched.id)
            else:
                # Если событие прошло, удаляем из отслеживания для следующего дня
                sent_main_reminders.discard(sched.id)

            # 2. Проверяем предварительное напоминание (если установлено)
            if sched.reminder_minutes > 0:
                # Проверяем, совпадает ли время предварительного напоминания (±30 секунд = ±0.5 минуты)
                # Напоминание должно прийти когда time_diff_minutes ≈ reminder_minutes
                reminder_time_diff = time_diff_minutes - sched.reminder_minutes
                logger.debug(f"Schedule {sched.id}: reminder_time_diff={reminder_time_diff:.1f} min (threshold ±0.5 min)")
                if abs(reminder_time_diff) <= 0.5:
                    if sched.id not in sent_preliminary_reminders:
                        from core.utils import minutes_to_human_readable
                        reminder_text = minutes_to_human_readable(sched.reminder_minutes)
                        await bot.send_message(
                            chat_id=int(sched.chat_id),
                            text=f"⏳ ПРЕДВАРИТЕЛЬНОЕ НАПОМИНАНИЕ:\n{sched.text}\n\n⏰ Начало через: {reminder_text}"
                        )
                        logger.info(f"Предварительное напоминание отправлено: {sched.id} → {sched.chat_id} (за {sched.reminder_minutes} минут)")
                        sent_preliminary_reminders.add(sched.id)
                else:
                    # Если время предварительного напоминания прошло, удаляем из отслеживания
                    sent_preliminary_reminders.discard(sched.id)

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
