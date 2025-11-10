import asyncio
import logging
from typing import Optional

from core.config import BOT_TOKEN, DB_URL
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.filters import F
from tortoise import Tortoise
from core.models import Task

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
  /add <текст задачи>
  Или просто напиши текст — я сохраню его как задачу

• Посмотреть список задач:
  /list

• Отметить задачу выполненной:
  /done <id задачи>

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