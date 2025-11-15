import asyncio
import logging
import time
from core.middleware import ignore_old_events
from core.config import BOT_TOKEN, DB_URL
from maxapi import Bot, Dispatcher
from tortoise import Tortoise

from core import utils
from core.handlers import register_handlers
from core.scheduler import start_scheduler

# Минимальное логирование - только ошибки и важная информация
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

# Отключаем избыточные логи от библиотек
logging.getLogger('maxapi').setLevel(logging.ERROR)
logging.getLogger('dispatcher').setLevel(logging.ERROR)
logging.getLogger('tortoise').setLevel(logging.ERROR)
logging.getLogger('aiosqlite').setLevel(logging.ERROR)
logging.getLogger('LiteLLM').setLevel(logging.ERROR)
logging.getLogger('litellm').setLevel(logging.ERROR)
logging.getLogger('aiohttp').setLevel(logging.ERROR)

# Для важных событий приложения оставляем INFO
app_logger = logging.getLogger('kuzia-bot')
app_logger.setLevel(logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

register_handlers(dp, bot)


async def main():
    app_logger.info("🤖 Запуск Кузя-бота...")
    
    url = DB_URL or "sqlite://db.sqlite3"
    await Tortoise.init(db_url=url, modules={"models": ["core.models"]})
    await Tortoise.generate_schemas()
    utils.STARTUP_TS = time.time()
    
    app_logger.info("✅ База данных инициализирована")
    
    try:
        # Запускаем scheduler и dispatcher одновременно
        scheduler_task = asyncio.create_task(start_scheduler(bot, interval=30))
        polling_task = asyncio.create_task(dp.start_polling(bot))
        
        app_logger.info("🚀 Бот запущен и готов к работе")
        
        # Если один из них упадёт, отменяем оба
        done, pending = await asyncio.wait(
            [scheduler_task, polling_task],
            return_when=asyncio.FIRST_EXCEPTION
        )
        
        for task in done:
            exc = task.exception()
            if exc:
                app_logger.error(f"💥 Критическая ошибка: {exc}")
                for pending_task in pending:
                    pending_task.cancel()
                raise exc
    except asyncio.CancelledError:
        app_logger.info("⏹️ Бот остановлен")
    except Exception as e:
        app_logger.error(f"💥 Ошибка запуска: {e}")
    finally:
        await Tortoise.close_connections()
        app_logger.info("🔌 Соединения с БД закрыты")


if __name__ == '__main__':
    asyncio.run(main())