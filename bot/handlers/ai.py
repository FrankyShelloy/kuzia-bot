# bot/handlers/ai.py
from maxapi import Dispatcher
from maxapi.types import MessageCreated, Command
from maxapi.enums.sender_action import SenderAction
from core.models import Task
from bot.utils import resolve_chat_id, not_bot
from bot.ai_core import get_response

def register_ai_handlers(dp: Dispatcher):
    @dp.message_created(Command('ai') & not_bot)
    async def ai_command(event: MessageCreated):
        parts = (event.message.body.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await event.message.answer("Использование: /ai <вопрос>")
            return
        question = parts[1].strip()
        chat_id = resolve_chat_id(event)
        await event.bot.send_action(chat_id=int(chat_id), action=SenderAction.TYPING_ON)
        answer = await get_response(int(chat_id), question)
        await event.message.answer(f"AI: {answer}")
        await event.message.answer("Оцени от 1 до 5?")

    @dp.message_created(Command('decompose') & not_bot)
    async def decompose(event: MessageCreated):
        parts = (event.message.body.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await event.message.answer("Использование: /decompose <задача>")
            return
        task = parts[1].strip()
        chat_id = resolve_chat_id(event)
        await event.bot.send_action(chat_id=int(chat_id), action=SenderAction.TYPING_ON)

        prompt = f"Разбей на 3-5 подзадач с приоритетами. Задача: '{task}'. Формат: 1. [Название] ([приоритет])"
        answer = await get_response(int(chat_id), prompt)

        lines = [l.strip() for l in answer.split('\n') if l.strip() and '.' in l]
        for line in lines:
            sub = line.split('.', 1)[1].strip().split(' (')[0].strip()
            await Task.create(chat_id=chat_id, user_id=str(event.message.sender.user_id), text=sub)

        await event.message.answer(f"Разбил:\n{answer}\n\nПодзадачи в /list")
        await event.message.answer("Оцени от 1 до 5?")