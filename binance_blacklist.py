import asyncio
import aiosqlite

DB_FILE = "C:/Users/p7016/Documents/bpa/binance_blacklist.db"

async def initialize_database():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """
        )
        await db.commit()

async def add_to_blacklist(name):
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT OR IGNORE INTO blacklist (name) VALUES (?)", (name,))
            await db.commit()
    except aiosqlite.IntegrityError:
        # Name already exists in the blacklist, handle accordingly
        pass

async def is_blacklisted(name):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id FROM blacklist WHERE name = ?", (name,))
        result = await cursor.fetchone()
        return result is not None
async def main():
    await initialize_database()

if __name__ == "__main__":
    asyncio.run(main())