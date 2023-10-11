import aiosqlite
import asyncio
class AssetBalanceDB:
    def __init__(self):
        self.db_path = "C:/Users/p7016/Documents/bpa/asset_balance.db"
    async def create_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS asset_balances (
                    asset TEXT NOT NULL PRIMARY KEY,
                    balance REAL NOT NULL
                );
            ''')
            await db.commit()
    async def insert_or_update_balance(self, asset, balance):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute('''
                INSERT OR REPLACE INTO asset_balances (asset, balance)
                VALUES (?, COALESCE((SELECT balance FROM asset_balances WHERE asset = ?), 0) + ?);
            ''', (asset, asset, balance))
            await db.commit()
    async def fetch_all_balances(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute('SELECT asset, balance FROM asset_balances;')
            rows = await cursor.fetchall()
            return rows
    async def fetch_balance(self, asset):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute('SELECT balance FROM asset_balances WHERE asset = ?', (asset,))
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None
    async def display_all_balances(self):
        balances = await self.fetch_all_balances()
        print("Asset Balances:")
        for asset, balance in balances:
            if balance > 0:
                print(f"{asset}: {balance}")
    async def get_conn(self):
        if not hasattr(self, "_conn"):
            self._conn = await aiosqlite.connect(self.db_path)
        return self._conn
    async def execute(self, query, params=None):
        conn = await self.get_conn()
        cursor = await conn.cursor()
        if params:
            await cursor.execute(query, params)
        else:
            await cursor.execute(query)
        await conn.commit()
        return cursor
    async def reset_all_balances_to_zero(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute('UPDATE asset_balances SET balance = 0;')
            await db.commit()
if __name__ == "__main__":
    db_manager = AssetBalanceDB()
    asyncio.run(db_manager.create_table())
    asyncio.run(db_manager.display_all_balances())
