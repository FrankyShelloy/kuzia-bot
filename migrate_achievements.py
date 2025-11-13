"""Migration script to add achievements table."""
import asyncio
from tortoise import Tortoise
from core.config import DB_URL


async def migrate():
    url = DB_URL or "sqlite://db.sqlite3"
    await Tortoise.init(db_url=url, modules={"models": ["core.models"]})
    
    # Generate schemas (will create new tables if they don't exist)
    await Tortoise.generate_schemas()
    
    print("✅ Migration completed: achievements table created")
    
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())
