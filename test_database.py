import asyncio
import aiosqlite

DB_PATH = 'C:/Users/p7016/Documents/bpa/ads_data.db'

async def test_data_retrieval():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            c = await conn.cursor()
            await c.execute("SELECT * FROM ads")
            all_ads = await c.fetchall()
            print(f"Number of rows retrieved: {len(all_ads)}")
    except Exception as e:
        print(f"An error occurred while retrieving data from the database: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_data_retrieval())
