import asyncio
import logging
import time

from core.config import BOT_TOKEN, DB_URL
from maxapi import Bot, Dispatcher
from tortoise import Tortoise

from core import utils
from core.handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logging.getLogger('dispatcher').setLevel(logging.WARNING)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

register_handlers(dp, bot)


async def main():
    url = DB_URL or "sqlite://db.sqlite3"
    await Tortoise.init(db_url=url, modules={"models": ["core.models"]})
    await Tortoise.generate_schemas()
    utils.STARTUP_TS = time.time()
    try:
        await dp.start_polling(bot)
    finally:
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())