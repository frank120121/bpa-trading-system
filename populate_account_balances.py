import aiosqlite
import logging

DATABASE_PATH = "crypto_bot.db"
logging.basicConfig(level=logging.DEBUG)

async def drop_bank_accounts_table(conn):
    """Drop the bank_accounts table."""
    async with conn.cursor() as cursor:
        await cursor.execute("DROP TABLE IF EXISTS bank_accounts")
        await conn.commit()

async def drop_exchange_accounts_table(conn):
    """Drop the exchange_accounts table."""
    async with conn.cursor() as cursor:
        await cursor.execute("DROP TABLE IF EXISTS exchange_accounts")
        await conn.commit()

async def drop_account_balances_table(conn):
    """Drop the account_balances table."""
    async with conn.cursor() as cursor:
        await cursor.execute("DROP TABLE IF EXISTS account_balances")
        await conn.commit()

async def main():
    conn = await aiosqlite.connect(DATABASE_PATH)
    
    await drop_bank_accounts_table(conn)
    await drop_exchange_accounts_table(conn)
    await drop_account_balances_table(conn)
    
    await conn.close()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
