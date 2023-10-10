import aiosqlite
import datetime
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

DB_PATH = 'C:\\Users\\p7016\\OneDrive\\Work\\P2Pbot\\ads_data.db'

async def create_database():
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        await c.execute('''CREATE TABLE IF NOT EXISTS ads 
                            (
                                advNo TEXT PRIMARY KEY, 
                                target_spot INTEGER NOT NULL,
                                asset_type TEXT NOT NULL, 
                                price REAL, 
                                floating_ratio REAL, 
                                last_updated TIMESTAMP,
                                account TEXT NOT NULL
                            )''')
        await conn.commit()
async def fetch_all_ads_from_database():
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        await c.execute("SELECT * FROM ads")
        ads = await c.fetchall()
    return [
        {
            'advNo': ad[0],
            'target_spot': ad[1],
            'asset_type': ad[2],
            'price': ad[3],
            'floating_ratio': ad[4],
            'account': ad[6] 
        }
        for ad in ads
    ]

async def get_ad_from_database(advNo):
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        await c.execute("SELECT * FROM ads WHERE advNo=?", (advNo,))
        ad = await c.fetchone()
    if ad:
        return {
            'advNo': ad[0],
            'target_spot': ad[1],
            'asset_type': ad[2],
            'price': ad[3],
            'floating_ratio': ad[4]
        }
    return None

async def update_ad_in_database(advNo, target_spot, asset_type, price, floating_ratio, account):
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        try:
            await c.execute("""
            INSERT OR REPLACE INTO ads (advNo, target_spot, asset_type, price, floating_ratio, last_updated, account) 
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)""", 
            (advNo, target_spot, asset_type, price, floating_ratio, account))
            updated = c.rowcount
            if updated:
                logger.debug(f"Updated ad {advNo} successfully.")
            else:
                logger.warning(f"Failed to update ad {advNo}.")
            await conn.commit()
        except Exception as e:
            logger.error(f"Exception during updating ad {advNo}: {e}")

async def insert_multiple_ads(ads_list):
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        for ad in ads_list:
            await c.execute(
                """INSERT OR REPLACE INTO ads (advNo, target_spot, asset_type, account) 
                VALUES (?, ?, ?, ?)""", 
                (ad['advNo'], ad['target_spot'], ad['asset_type'], ad['account'])
            )
        await conn.commit()

async def print_all_ads():
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            c = await conn.cursor()
            await c.execute("SELECT * FROM ads")
            all_ads = await c.fetchall()

            for ad in all_ads:
                print({
                    'advNo': ad[0],
                    'target_spot': ad[1],
                    'asset_type': ad[2],
                    'price': ad[3],
                    'floating_ratio': ad[4],
                    'last_updated': ad[5],
                    'account': ad[6]
                })
    except Exception as e:
        print(f"An error occurred: {e}")
async def update_ads(ad):
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        advNo = ad["data"]["advNo"]
        asset_type = ad["data"]["asset"]
        price = ad["data"]["price"]
        floating_ratio = ad["data"]["priceFloatingRatio"]
        last_updated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
        await c.execute('''UPDATE ads SET 
                asset_type = ?,
                price = ?,
                floating_ratio = ?,
                last_updated = ? 
                WHERE advNo = ?''', (asset_type, price, floating_ratio, last_updated, advNo))
        
        await conn.commit()
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_database())
    loop.run_until_complete(print_all_ads())