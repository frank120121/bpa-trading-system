# bpa/ads_database.py

import json
import aiosqlite

from src.utils.common_vars import ads_dict
from src.data.database.connection import DB_FILE
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)



async def recreate_database():
    """Drop existing database and create fresh one with correct schema"""
    async with aiosqlite.connect(DB_FILE) as conn:
        logger.info("Dropping existing ads table and creating fresh one...")
        
        # Drop the existing table completely
        await conn.execute('DROP TABLE IF EXISTS ads')
        
        # Create fresh table with correct schema
        await conn.execute('''
            CREATE TABLE ads (
                advNo TEXT PRIMARY KEY,
                target_spot INTEGER DEFAULT 0,
                asset_type TEXT NOT NULL,
                price REAL,
                floating_ratio REAL,
                last_updated TIMESTAMP,
                account TEXT NOT NULL,
                surplused_amount REAL DEFAULT 0,
                fiat TEXT NOT NULL DEFAULT 'Unknown',
                transAmount REAL,
                payTypes TEXT NOT NULL DEFAULT '[]',
                `Group` TEXT NOT NULL DEFAULT 'Unknown',
                trade_type TEXT NOT NULL,
                minTransAmount REAL DEFAULT 0.0
            )
        ''')
        
        await conn.commit()
        logger.info("Fresh ads table created successfully")


async def fetch_all_ads_from_database(trade_type=None):
    """Fetch ads from database with C2C API compatible data types"""
    async with aiosqlite.connect(DB_FILE) as conn:
        c = await conn.cursor()
        query = "SELECT * FROM ads"
        params = ()
        if trade_type is not None:
            query += " WHERE trade_type = ?"
            params = (trade_type,)
        await c.execute(query, params)
        ads = await c.fetchall()
    
    return [
        {
            'advNo': ad[0],                                    # string
            'target_spot': ad[1] if ad[1] is not None else 0,  # integer
            'asset_type': ad[2],                               # string
            'price': ad[3],                                    # float/None
            'floating_ratio': ad[4],                           # float/None
            'last_updated': ad[5],                             # timestamp
            'account': ad[6],                                  # string
            'surplused_amount': ad[7],                         # float
            'fiat': ad[8],                                     # string
            'transAmount': ad[9],                              # float
            'payTypes': json.loads(ad[10]) if ad[10] and ad[10].strip().startswith('[') else None,
            'Group': ad[11],                                   # string
            'trade_type': ad[12],                              # string
            'minTransAmount': ad[13] if ad[13] is not None else 0.0  # float
        }
        for ad in ads
    ]

async def get_ad_from_database(advNo):
    """Get single ad from database with C2C API compatible data types"""
    async with aiosqlite.connect(DB_FILE) as conn:
        c = await conn.cursor()
        await c.execute("SELECT * FROM ads WHERE advNo=?", (advNo,))
        ad = await c.fetchone()
    
    if ad:
        return {
            'advNo': ad[0],                                    # string
            'target_spot': ad[1] if ad[1] is not None else 0,  # integer
            'asset_type': ad[2],                               # string
            'price': ad[3],                                    # float/None
            'floating_ratio': ad[4],                           # float/None
            'last_updated': ad[5],                             # timestamp
            'account': ad[6],                                  # string
            'surplused_amount': ad[7],                         # float
            'fiat': ad[8],                                     # string
            'transAmount': ad[9],                              # float 
            'payTypes': json.loads(ad[10]) if ad[10] is not None else None,
            'Group': ad[11],                                   # string
            'trade_type': ad[12],                              # string
            'minTransAmount': ad[13] if ad[13] is not None else 0.0  # float
        }
    return None

async def update_ad_in_database(target_spot, advNo, asset_type, floating_ratio, price, surplusAmount, account, fiat, transAmount, minTransAmount):
    """Update ad with C2C API compatible data types and validation"""
    logger.debug(f"Attempting to update {advNo} with price: {price}, floating_ratio: {floating_ratio}, asset_type: {asset_type}, target_spot: {target_spot}, fiat: {fiat}, transAmount: {transAmount}, minTransAmount: {minTransAmount}")

    # Ensure numeric types for C2C API compatibility
    if target_spot is None:
        target_spot = 0
    
    # Ensure transAmount and minTransAmount are numeric (float/int)
    if isinstance(transAmount, str):
        try:
            transAmount = float(transAmount)
        except (ValueError, TypeError):
            transAmount = 0.0
    
    if isinstance(minTransAmount, str):
        try:
            minTransAmount = float(minTransAmount)
        except (ValueError, TypeError):
            minTransAmount = 0.0

    async with aiosqlite.connect(DB_FILE) as conn:
        c = await conn.cursor()
        try:
            # Update only specific fields without changing payTypes and Group
            await c.execute("""
                UPDATE ads
                SET target_spot = ?, asset_type = ?, price = ?, floating_ratio = ?, last_updated = datetime('now'), account = ?, surplused_amount = ?, fiat = ?, transAmount = ?, minTransAmount = ?
                WHERE advNo = ?""", 
                (target_spot, asset_type, price, floating_ratio, account, surplusAmount, fiat, transAmount, minTransAmount, advNo))
            await conn.commit()

            logger.debug(f"Updated ad {advNo} successfully without modifying payTypes and Group.")
        except Exception as e:
            logger.error(f"Exception during updating ad {advNo}: {e}")


async def insert_initial_ads():
    """Insert initial ads with C2C API compatible data types"""
    ads_to_insert = []
    for account_name, ads in ads_dict.items():
        for ad in ads:
            # Handle payType properly - can be list, string, or None
            pay_type = ad.get('payType')  # Note: using 'payType' (singular) to match your ads_dict
            if pay_type is None:
                pay_types_serialized = json.dumps([])  # Empty array for None
            elif isinstance(pay_type, list):
                pay_types_serialized = json.dumps(pay_type)  # Already a list
            else:
                pay_types_serialized = json.dumps([pay_type])  # Convert single string to list
            
            # Ensure target_spot is integer and amounts are numeric
            target_spot = ad.get('target_spot', 0)
            if isinstance(target_spot, str):
                target_spot = int(target_spot) if target_spot.isdigit() else 0
            
            # Ensure transAmount and minTransAmount are numeric
            transAmount = ad.get('transAmount', 0)
            if isinstance(transAmount, str):
                transAmount = float(transAmount) if transAmount.replace('.', '').isdigit() else 0.0
            
            minTransAmount = ad.get('minTransAmount', 0)
            if isinstance(minTransAmount, str):
                minTransAmount = float(minTransAmount) if minTransAmount.replace('.', '').isdigit() else 0.0
            
            ads_to_insert.append((
                ad['advNo'],           # string
                target_spot,           # integer
                ad['asset_type'],      # string
                account_name,          # string
                ad['fiat'],           # string
                transAmount,          # float/int 
                pay_types_serialized, # string 
                ad['Group'],          # string
                ad['trade_type'],     # string
                minTransAmount        # float/int
            ))
    await insert_multiple_ads(ads_to_insert)

async def insert_multiple_ads(ads_list):
    """Insert multiple ads ensuring C2C API compatibility"""
    async with aiosqlite.connect(DB_FILE) as conn:
        c = await conn.cursor()
        for ad in ads_list:
            await c.execute(
                """INSERT OR REPLACE INTO ads (advNo, target_spot, asset_type, account, fiat, transAmount, payTypes, `Group`, trade_type, minTransAmount) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ad
            )
        await conn.commit()


async def convert_to_c2c_format(ad_data):
    """Convert internal ad format to Binance C2C API format"""
    # Map payTypes to tradeMethods
    trade_methods = []
    if ad_data.get('payTypes'):
        for pay_type in ad_data['payTypes']:
            trade_methods.append({
                "identifier": pay_type,
                "payId": 0, 
                "payType": pay_type
            })
    
    return {
        "advNo": ad_data['advNo'],                          # string
        "asset": ad_data['asset_type'],                     # string
        "fiatUnit": ad_data['fiat'],                        # string
        "tradeType": ad_data['trade_type'],                 # string
        "initAmount": float(ad_data['transAmount']),        # number
        "maxSingleTransAmount": float(ad_data['transAmount']), # number
        "minSingleTransAmount": float(ad_data['minTransAmount']), # number
        "tradeMethods": trade_methods,                      # array of objects
        "price": float(ad_data.get('price', 0)) if ad_data.get('price') else 0,  # number
        "priceFloatingRatio": float(ad_data.get('floating_ratio', 0)) if ad_data.get('floating_ratio') else 0,
        "autoReplyMsg": "Payment confirmed, crypto will be released quickly",
        "payTimeLimit": 15,                                
        "onlineNow": True,
        "classify": "mass",
        "priceType": 1,  
        "saveAsTemplate": 0,
        "takerAdditionalKycRequired": 0,
    }