# main.py
import asyncio
import logging
from tortoise import Tortoise
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted
from core.config import BOT_TOKEN, DB_URL

# === ХЕНДЛЕРЫ ===
from bot.handlers.tasks import register_tasks_handlers
from bot.handlers.ai import register_ai_handlers
from bot.handlers.schedule import register_schedule_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# === РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ===
register_tasks_handlers(dp)
register_ai_handlers(dp)
register_schedule_handlers(dp)

@dp.bot_started()
async def start(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="Привет! Я Кузя — твой умный помощник.\n"
             "Напиши задачу или используй /decompose"
    )

async def main():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["core.models"]})
    await Tortoise.generate_schemas()

    try:
        logger.info("Кузя запущен — start_polling")
        await dp.start_polling(bot)  # ВСЁ РАБОТАЕТ
    finally:
        await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())