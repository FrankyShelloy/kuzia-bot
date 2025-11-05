import asyncio
import logging

from core.config import TOKEN
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()


@dp.bot_started()
async def on_bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Я Кузя — твой персональный помощник по продуктивности и развитию. Начнем с команды /start или /menu!'
    )

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())