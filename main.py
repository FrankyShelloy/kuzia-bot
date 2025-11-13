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

logging.basicConfig(level=logging.DEBUG)
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
        # Запускаем scheduler и dispatcher одновременно
        scheduler_task = asyncio.create_task(start_scheduler(bot, interval=30))
        polling_task = asyncio.create_task(dp.start_polling(bot))
        
        # Если один из них упадёт, отменяем оба
        done, pending = await asyncio.wait(
            [scheduler_task, polling_task],
            return_when=asyncio.FIRST_EXCEPTION
        )
        
        for task in done:
            exc = task.exception()
            if exc:
                logging.error(f"Task failed with exception: {exc}")
                for pending_task in pending:
                    pending_task.cancel()
                raise exc
    except asyncio.CancelledError:
        logging.info("Tasks cancelled")
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
    finally:
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(main())