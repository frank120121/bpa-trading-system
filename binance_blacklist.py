import asyncio
import aiosqlite
from database import create_connection, print_table_contents

DB_FILE = "C:/Users/p7016/Documents/bpa/orders_data.db"

async def initialize_database(conn):
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS P2PBlacklist (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            order_no TEXT,
            country TEXT
        )
        """
    )
    await conn.commit()

async def clear_blacklist(conn):
    await conn.execute("DELETE FROM P2PBlacklist")
    await conn.commit()

async def add_to_blacklist(conn, name, order_no, country):
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO P2PBlacklist (name, order_no, country) VALUES (?, ?, ?)", 
            (name, order_no, country)
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        pass

async def is_blacklisted(conn, name):
    cursor = await conn.execute("SELECT id FROM P2PBlacklist WHERE name = ?", (name,))
    result = await cursor.fetchone()
    return result is not None

async def remove_from_blacklist(conn, name):
    await conn.execute("DELETE FROM P2PBlacklist WHERE name = ?", (name,))
    await conn.commit()

async def main():
    conn = await create_connection(DB_FILE)
    await print_table_contents(conn, 'P2PBlacklist')
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
