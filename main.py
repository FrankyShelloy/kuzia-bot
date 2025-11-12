# main.py
import asyncio
import logging
from tortoise import Tortoise
from maxapi import Bot, Dispatcher
from core.config import BOT_TOKEN, DB_URL

# === ХЕНДЛЕРЫ ===
from bot.handlers.tasks import register_tasks_handlers

logging.getLogger('maxapi.dispatcher').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# === РЕГИСТРАЦИЯ ===
register_tasks_handlers(dp)

# === ПРИВЕТСТВИЕ — ТОЛЬКО ОДИН РАЗ ===
WELCOME_SENT = False

@dp.bot_started()
async def on_bot_started(event):
    global WELCOME_SENT
    if not WELCOME_SENT:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text="Привет! Я Кузя — твой умный помощник.\n"
                 "Напиши задачу или используй /decompose"
        )
        WELCOME_SENT = True

async def main():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["core.models"]})
    await Tortoise.generate_schemas()

    try:
        logger.info("Кузя запущен — start_polling")

        # === SKIP OLD: ПОЛУЧАЕМ ПОСЛЕДНИЙ update_id ===
        response = await bot.get_updates(limit=1)
        last_id = 0
        if isinstance(response, dict) and 'result' in response and response['result']:
            last_id = response['result'][0].get('update_id', 0)
        logger.info(f"Пропускаем обновления до ID: {last_id + 1}")

        # === ПЕРЕОПРЕДЕЛЯЕМ get_updates ===
        original = bot.get_updates
        async def get_updates_skip_old(*args, **kwargs):
            nonlocal last_id  # ВЛОЖЕННАЯ ФУНКЦИЯ — ИСПОЛЬЗУЕМ nonlocal!
            kwargs['marker'] = last_id + 1
            resp = await original(*args, **kwargs)
            if isinstance(resp, dict) and 'result' in resp and resp['result']:
                last_id = resp['result'][-1].get('update_id', last_id)
            return resp

        bot.get_updates = get_updates_skip_old

        await dp.start_polling(bot)

    finally:
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())