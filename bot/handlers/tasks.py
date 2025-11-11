# bot/handlers/tasks.py
import logging  # ДОБАВЬ!
from maxapi import Dispatcher
from maxapi.types import MessageCreated, Command
from maxapi.filters import F
from maxapi.enums.sender_action import SenderAction
from core.models import Task
from bot.utils import resolve_chat_id, not_bot
from bot.ai_core import get_response
logger = logging.getLogger(__name__)  # ДОБАВЬ!
def register_tasks_handlers(dp: Dispatcher):
    @dp.message_created(Command('add') & not_bot)
    async def add_task(event: MessageCreated):
        parts = (event.message.body.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await event.message.answer("Использование: /add <текст>")
            return
        await Task.create(
            chat_id=resolve_chat_id(event),
            user_id=str(event.message.sender.user_id),
            text=parts[1].strip()
        )
        await event.message.answer("Задача добавлена")

    @dp.message_created(F.message.body.text & ~F.message.body.text.startswith('/') & not_bot)
    async def plain_text_task(event: MessageCreated):
        logger.info(f"ХЕНДЛЕР: plain_text_task вызван, текст: {event.message.body.text}")
        text = event.message.body.text.strip()
        chat_id = resolve_chat_id(event)
        await Task.create(chat_id=chat_id, user_id=str(event.message.sender.user_id), text=text)
        await event.message.answer("Задача принята")
        await event.bot.send_action(chat_id=int(chat_id), action=SenderAction.TYPING_ON)
        answer = await get_response(int(chat_id), text)
        await event.message.answer(f"AI: {answer}")
        await event.message.answer("Оцени от 1 до 5?")

    @dp.message_created(Command('list') & not_bot)
    async def list_tasks(event: MessageCreated):
        chat_id = resolve_chat_id(event)
        tasks = await Task.filter(chat_id=chat_id).order_by("-status", "created_at")
        if not tasks:
            await event.message.answer("Задач нет")
            return
        lines = [f"{t.id}. {'done' if t.status == 'done' else 'pending'} {t.text}" for t in tasks]
        await event.message.answer("Задачи:\n" + "\n".join(lines))

    @dp.message_created(Command('done') & not_bot)
    async def done_task(event: MessageCreated):
        parts = (event.message.body.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await event.message.answer("Использование: /done <id>")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await event.message.answer("ID — число")
            return
        chat_id = resolve_chat_id(event)
        task = await Task.get_or_none(id=task_id, chat_id=chat_id)
        if not task:
            await event.message.answer("Не найдено")
            return
        if task.status == "done":
            await event.message.answer("Уже выполнено")
            return
        task.status = "done"
        await task.save()
        await event.message.answer(f"Задача {task_id} выполнена")