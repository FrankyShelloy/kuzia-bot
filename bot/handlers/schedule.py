# bot/handlers/schedule.py
from maxapi import Dispatcher
from maxapi.types import MessageCreated, Command
from core.models import Schedule
from bot.utils import resolve_chat_id, not_bot

# === Дни недели ===
DAY_NAMES = {
    "пн": 0, "понедельник": 0, "пнд": 0, "monday": 0, "mon": 0,
    "вт": 1, "вторник": 1, "втр": 1, "tuesday": 1, "tue": 1,
    "ср": 2, "среда": 2, "срд": 2, "wednesday": 2, "wed": 2,
    "чт": 3, "четверг": 3, "чтв": 3, "thursday": 3, "thu": 3,
    "пт": 4, "пятница": 4, "птн": 4, "friday": 4, "fri": 4,
    "сб": 5, "суббота": 5, "сбт": 5, "saturday": 5, "sat": 5,
    "вс": 6, "воскресенье": 6, "вск": 6, "sunday": 6, "sun": 6,
}
DAY_NAMES_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье"
]

def register_schedule_handlers(dp: Dispatcher):
    @dp.message_created(Command('schedule_add') & not_bot)
    async def schedule_add(event: MessageCreated):
        text = event.message.body.text or ""
        parts = text.split(maxsplit=3)
        if len(parts) < 4:
            await event.message.answer(
                "Использование: /schedule_add <день> <время> <текст>\n"
                "Пример: /schedule_add пн 09:00 Зарядка"
            )
            return

        day_str = parts[1].strip().lower()
        time_str = parts[2].strip()
        task_text = parts[3].strip()

        # --- День недели ---
        day_of_week = None
        if day_str.isdigit():
            try:
                day_of_week = int(day_str)
                if not 0 <= day_of_week <= 6:
                    raise ValueError
            except ValueError:
                await event.message.answer("День: 0–6")
                return
        else:
            day_of_week = DAY_NAMES.get(day_str)
            if day_of_week is None:
                await event.message.answer("Неизвестный день. Используй: пн, вт, ср...")
                return

        # --- Время ---
        if not (len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit()):
            await event.message.answer("Время: HH:MM")
            return
        hour, minute = int(time_str[:2]), int(time_str[3:])
        if hour > 23 or minute > 59:
            await event.message.answer("Некорректное время")
            return

        # --- Сохраняем ---
        chat_id = resolve_chat_id(event)
        await Schedule.create(
            chat_id=chat_id,
            user_id=str(event.message.sender.user_id),
            text=task_text,
            day_of_week=day_of_week,
            time=time_str
        )

        day_name = DAY_NAMES_RU[day_of_week]
        await event.message.answer(f"{day_name} {time_str} — {task_text}")

    @dp.message_created(Command('schedule') & not_bot)
    async def schedule_list(event: MessageCreated):
        chat_id = resolve_chat_id(event)
        schedules = await Schedule.filter(chat_id=chat_id, enabled=True).order_by("day_of_week", "time")
        if not schedules:
            await event.message.answer("Расписание пусто")
            return

        lines = []
        current_day = None
        for s in schedules:
            day_name = DAY_NAMES_RU[s.day_of_week]
            if current_day != s.day_of_week:
                if current_day is not None:
                    lines.append("")
                lines.append(f"{day_name}:")
                current_day = s.day_of_week
            lines.append(f" {s.id}. {s.time} — {s.text}")

        await event.message.answer("Расписание:\n\n" + "\n".join(lines))

    @dp.message_created(Command('schedule_remove') & not_bot)
    async def schedule_remove(event: MessageCreated):
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("Использование: /schedule_remove <id>")
            return

        try:
            sid = int(parts[1].strip())
        except ValueError:
            await event.message.answer("ID — число")
            return

        chat_id = resolve_chat_id(event)
        s = await Schedule.filter(id=sid, chat_id=chat_id).first()
        if not s:
            await event.message.answer("Не найдено")
            return

        s.enabled = False
        await s.save(update_fields=["enabled", "updated_at"])
        await event.message.answer(f"Запись {sid} удалена")