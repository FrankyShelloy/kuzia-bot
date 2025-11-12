import asyncio
import sqlite3


async def migrate():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'parent_id' not in columns:
            print("Adding parent_id column to tasks table...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER DEFAULT NULL")
            conn.commit()
            print("✓ Migration completed successfully!")
        else:
            print("Column parent_id already exists, skipping migration.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
