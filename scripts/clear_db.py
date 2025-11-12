#!/usr/bin/env python3
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tortoise import Tortoise
from core.config import DB_URL
from core.models import Task, Schedule

async def run():
    url = DB_URL or "sqlite://db.sqlite3"
    await Tortoise.init(db_url=url, modules={"models": ["core.models"]})
    try:
        before_tasks = await Task.all().count()
        before_sched = await Schedule.all().count()
        print(f"Before: tasks={before_tasks}, schedules={before_sched}")

        deleted_tasks = await Task.all().delete()
        deleted_sched = await Schedule.all().delete()

        after_tasks = await Task.all().count()
        after_sched = await Schedule.all().count()
        print(f"Deleted: tasks={deleted_tasks}, schedules={deleted_sched}")
        print(f"After: tasks={after_tasks}, schedules={after_sched}")
    finally:
        await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(run())
