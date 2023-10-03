import aiosqlite
import asyncio
import logging

DATABASE = "crypto_bot.db"
logging.basicConfig(level=logging.INFO)

async def check_nickname_column_exists(conn):
    async with conn.cursor() as cursor:
        await cursor.execute("PRAGMA table_info(merchants)")
        columns = [column[1] for column in await cursor.fetchall()]
        return 'nickname' in columns

async def upgrade_database():
    async with aiosqlite.connect(DATABASE) as conn:
        if await check_nickname_column_exists(conn):
            logging.info("Detected 'nickname' column in merchants table. Starting upgrade process...")

            # 1. Rename the original merchants table
            await conn.execute("ALTER TABLE merchants RENAME TO merchants_old")
            logging.info("Renamed merchants table to merchants_old")

            # 2. Create a new merchants table without the nickname column
            await conn.execute("""
                CREATE TABLE merchants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sellerName TEXT NOT NULL UNIQUE
                )
            """)
            logging.info("Created new merchants table without 'nickname' column")

            # 3. Copy data from the old table to the new one
            await conn.execute("INSERT INTO merchants (id, sellerName) SELECT id, sellerName FROM merchants_old")
            logging.info("Copied data from merchants_old to merchants")

            # 4. Drop the old table
            await conn.execute("DROP TABLE merchants_old")
            logging.info("Dropped merchants_old table")

            await conn.commit()
            logging.info("Upgrade completed successfully!")
        else:
            logging.info("No 'nickname' column found in merchants table. No upgrade needed.")

if __name__ == "__main__":
    asyncio.run(upgrade_database())
