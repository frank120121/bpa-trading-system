import aiosqlite
import datetime
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)
from common_vars import ads_dict

DB_PATH = 'C:/Users/p7016/Documents/bpa/ads_data.db'

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
    logger.debug(f"Attempting to update {advNo} with price: {price}, floating_ratio: {floating_ratio}, asset_type: {asset_type}, target_spot: {target_spot}")
    
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        try:
            await c.execute("""
            INSERT OR REPLACE INTO ads (advNo, target_spot, asset_type, price, floating_ratio, last_updated, account) 
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)""", 
            (advNo, target_spot, asset_type, price, floating_ratio, account))
            await conn.commit()

            logger.debug(f"Updated ad {advNo} successfully.")
        except Exception as e:
            logger.error(f"Exception during updating ad {advNo}: {e}")
def insert_initial_ads():
    ads_to_insert = []
    for account_name, ads in ads_dict.items():
        for ad in ads:
            ads_to_insert.append({
                'advNo': ad['advNo'],
                'target_spot': ad['target_spot'],
                'asset_type': ad['asset_type'],
                'account': account_name 
            })
    asyncio.run(insert_multiple_ads(ads_to_insert))
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
async def update_ads(ad):
    advNo = ad["data"]["advNo"]
    asset_type = ad["data"]["asset"]
    price = ad["data"]["price"]
    floating_ratio = ad["data"]["priceFloatingRatio"]
    last_updated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    logger.debug(f"Attempting to update {advNo} with price: {price}, floating_ratio: {floating_ratio}, asset_type: {asset_type}")
    
    async with aiosqlite.connect(DB_PATH) as conn:
        c = await conn.cursor()
        try:
            await c.execute('''UPDATE ads SET 
                asset_type = ?,
                price = ?,
                floating_ratio = ?,
                last_updated = ? 
                WHERE advNo = ?''', (asset_type, price, floating_ratio, last_updated, advNo))
            
            await conn.commit()
            logger.debug(f"Updated ad {advNo} successfully.")
        except Exception as e:
            logger.error(f"Exception during updating ad {advNo}: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(create_database())
    #insert_initial_ads()
    asyncio.run(print_all_ads())

