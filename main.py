import asyncio
import logging
from typing import Optional

from core.config import BOT_TOKEN, DB_URL
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.filters import F
from tortoise import Tortoise
from core.models import Task, Schedule

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def _resolve_chat_id(event: MessageCreated) -> str:
    recipient = event.message.recipient
    chat_id: Optional[int] = recipient.chat_id
    if chat_id is None and event.chat is not None:
        chat_id = getattr(event.chat, "chat_id", None)
    if chat_id is None:
        chat_id = recipient.user_id or event.message.sender.user_id
    return str(chat_id)


# Словарь для преобразования названий дней недели
DAY_NAMES = {
    "пн": 0, "понедельник": 0, "пнд": 0, "monday": 0, "mon": 0,
    "вт": 1, "вторник": 1, "втр": 1, "tuesday": 1, "tue": 1,
    "ср": 2, "среда": 2, "срд": 2, "wednesday": 2, "wed": 2,
    "чт": 3, "четверг": 3, "чтв": 3, "thursday": 3, "thu": 3,
    "пт": 4, "пятница": 4, "птн": 4, "friday": 4, "fri": 4,
    "сб": 5, "суббота": 5, "сбт": 5, "saturday": 5, "sat": 5,
    "вс": 6, "воскресенье": 6, "вск": 6, "sunday": 6, "sun": 6,
}

DAY_NAMES_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


@dp.bot_started()
async def on_bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Я Кузя — твой персональный помощник по продуктивности и развитию. Начнем с команды /start или /menu!'
    )


@dp.message_created(Command('start'))
async def start_command(event: MessageCreated):
    start_message = """👋 Привет! Я Кузя — твой персональный помощник по продуктивности и развитию.

📋 Вот что я умею:

• Добавить задачу:
  /add  <текст задачи>
  Или просто напиши текст — я сохраню его как задачу

• Посмотреть список задач:
  /list

• Отметить задачу выполненной:
  /done <id задачи>

📅 Расписание:
  /schedule_add <день> <время> <текст>
  /schedule - посмотреть расписание
  /schedule_remove <id> - удалить из расписания

Пример: /schedule_add понедельник 09:00 Утренняя зарядка

Начни с добавления первой задачи! 🚀"""
    
    await event.message.answer(start_message)

@dp.message_created(Command('add'))
async def add_task_command(event: MessageCreated):
    text = event.message.body.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await event.message.answer("Использование: /add <текст задачи>")
        return
    task_text = parts[1].strip()
    await Task.create(
        chat_id=_resolve_chat_id(event),
        user_id=str(event.message.sender.user_id),
        text=task_text
    )
    await event.message.answer("✅ Задача добавлена")

@dp.message_created(F.message.body.text & ~F.message.body.text.startswith('/'))
async def add_task_plain_text(event: MessageCreated):
    task_text = event.message.body.text.strip()
    if not task_text:
        return
    await Task.create(
        chat_id=_resolve_chat_id(event),
        user_id=str(event.message.sender.user_id),
        text=task_text
    )
    await event.message.answer("📝 Задача принята")


@dp.message_created(Command('list'))
async def list_tasks(event: MessageCreated):
    chat_id = _resolve_chat_id(event)
    tasks = await Task.filter(chat_id=chat_id).order_by("status", "created_at")
    if not tasks:
        await event.message.answer("Задач пока нет. Добавьте новую командой /add <текст>")
        return
    lines = []
    for task in tasks:
        status = "✅" if task.status == "done" else "🔸"
        lines.append(f"{task.id}. {status} {task.text}")
    await event.message.answer("Список задач:\n" + "\n".join(lines))


@dp.message_created(Command('done'))
async def mark_task_done(event: MessageCreated):
    text = event.message.body.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await event.message.answer("Использование: /done <id задачи>")
        return
    try:
        task_id = int(parts[1].strip())
    except ValueError:
        await event.message.answer("ID задачи должен быть числом. Пример: /done 3")
        return

    chat_id = _resolve_chat_id(event)
    task = await Task.filter(id=task_id, chat_id=chat_id).first()
    if task is None:
        await event.message.answer("Задача не найдена.")
        return
    if task.status == "done":
        await event.message.answer("Эта задача уже выполнена ✅")
        return
    task.status = "done"
    await task.save(update_fields=["status", "updated_at"])
    await event.message.answer(f"Задача {task.id} отмечена как выполненная ✅")


@dp.message_created(Command('schedule_add'))
async def add_schedule(event: MessageCreated):
    text = event.message.body.text or ""
    parts = text.split(maxsplit=3)
    if len(parts) < 4:
        await event.message.answer(
            "Использование: /schedule_add <день> <время> <текст>\n"
            "Пример: /schedule_add понедельник 09:00 Утренняя зарядка\n"
            "Дни: пн, вт, ср, чт, пт, сб, вс (или полные названия)"
        )
        return
    
    day_str = parts[1].strip().lower()
    time_str = parts[2].strip()
    task_text = parts[3].strip()
    
    # Преобразование дня недели
    day_of_week = None
    if day_str.isdigit():
        day_of_week = int(day_str)
        if day_of_week < 0 or day_of_week > 6:
            await event.message.answer("День недели должен быть от 0 (понедельник) до 6 (воскресенье)")
            return
    else:
        day_of_week = DAY_NAMES.get(day_str)
        if day_of_week is None:
            await event.message.answer(
                f"Неизвестный день недели: {parts[1]}\n"
                "Используйте: пн, вт, ср, чт, пт, сб, вс или числа 0-6"
            )
            return
    
    # Проверка формата времени
    if not (len(time_str) == 5 and time_str[2] == ':' and 
            time_str[:2].isdigit() and time_str[3:].isdigit()):
        await event.message.answer("Время должно быть в формате HH:MM (например, 09:00)")
        return
    
    hour, minute = int(time_str[:2]), int(time_str[3:])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        await event.message.answer("Некорректное время. Часы: 0-23, минуты: 0-59")
        return
    
    chat_id = _resolve_chat_id(event)
    await Schedule.create(
        chat_id=chat_id,
        user_id=str(event.message.sender.user_id),
        text=task_text,
        day_of_week=day_of_week,
        time=time_str
    )
    
    day_name = DAY_NAMES_RU[day_of_week]
    await event.message.answer(f"✅ Расписание добавлено: {day_name} в {time_str} - {task_text}")


@dp.message_created(Command('schedule'))
async def list_schedule(event: MessageCreated):
    chat_id = _resolve_chat_id(event)
    schedules = await Schedule.filter(chat_id=chat_id, enabled=True).order_by("day_of_week", "time")
    
    if not schedules:
        await event.message.answer("Расписание пусто. Добавьте задачу командой /schedule_add")
        return
    
    lines = []
    current_day = None
    for schedule in schedules:
        day_name = DAY_NAMES_RU[schedule.day_of_week]
        if current_day != schedule.day_of_week:
            if current_day is not None:
                lines.append("")  # Пустая строка между днями
            lines.append(f"📅 {day_name}:")
            current_day = schedule.day_of_week
        lines.append(f"  {schedule.id}. {schedule.time} - {schedule.text}")
    
    await event.message.answer("📅 Ваше расписание:\n\n" + "\n".join(lines))


@dp.message_created(Command('schedule_remove'))
async def remove_schedule(event: MessageCreated):
    text = event.message.body.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await event.message.answer("Использование: /schedule_remove <id>")
        return
    
    try:
        schedule_id = int(parts[1].strip())
    except ValueError:
        await event.message.answer("ID должен быть числом. Пример: /schedule_remove 3")
        return
    
    chat_id = _resolve_chat_id(event)
    schedule = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
    if schedule is None:
        await event.message.answer("Запись в расписании не найдена.")
        return
    
    schedule.enabled = False
    await schedule.save(update_fields=["enabled", "updated_at"])
    await event.message.answer(f"✅ Запись {schedule_id} удалена из расписания")

async def main():
    url = DB_URL or "sqlite://db.sqlite3"
    await Tortoise.init(
        db_url=url,
        modules={"models": ["core.models"]},
    )
    await Tortoise.generate_schemas()
    try:
        await dp.start_polling(bot)
    finally:
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())