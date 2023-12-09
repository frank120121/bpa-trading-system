import asyncio
import aiosqlite
from database import create_connection, print_table_contents

DB_FILE = "C:/Users/p7016/Documents/bpa/orders_data.db"

async def initialize_database(conn):
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            order_no TEXT,
            country TEXT
        )
        """
    )
    await conn.commit()

async def add_to_blacklist(conn, name, order_no, country):
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO blacklist (name, order_no, country) VALUES (?, ?, ?)", 
            (name, order_no, country)
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        pass

async def is_blacklisted(conn, name):
    cursor = await conn.execute("SELECT id FROM blacklist WHERE name = ?", (name,))
    result = await cursor.fetchone()
    return result is not None

async def main():
    conn = await create_connection(DB_FILE)
    #await initialize_database(conn)
    await print_table_contents(conn, 'blacklist')
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
