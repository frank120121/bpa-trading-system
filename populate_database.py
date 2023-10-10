import asyncio
import aiohttp
from ads_database import fetch_all_ads_from_database, update_ad_in_database
from common_vars import ads_dict
from credentials import credentials_dict
from binance_api import BinanceAPI
import logging
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

advNo_to_target_spot = {ad['advNo']: ad['target_spot'] for _, ads in ads_dict.items() for ad in ads}

async def populate_ads_with_details():
    api_instances = {}
    async with aiohttp.ClientSession() as session:
        try:
            ads_info = await fetch_all_ads_from_database()
            logger.debug(f"Fetched ads from database: {ads_info}")
            for ad_info in ads_info:
                account = ad_info['account']
                if account not in api_instances:
                    KEY = credentials_dict[account]['KEY']
                    SECRET = credentials_dict[account]['SECRET']
                    api_instance = BinanceAPI(KEY, SECRET, session)
                    api_instances[account] = api_instance
                await process_ad(ad_info, api_instances[account])
        finally:
            for api_instance in api_instances.values():
                await api_instance.close_session()

async def process_ad(ad_info, api_instance):
    advNo = ad_info['advNo']
    ad_details = await api_instance.get_ad_detail(advNo)
    logger.debug(f"Ad details fetched from BinanceAPI for advNo {advNo}: {ad_details}")
    if ad_details and advNo in advNo_to_target_spot:
        ad_details['target_spot'] = advNo_to_target_spot[advNo]
        logger.debug(f"Updated target_spot for advNo {advNo} to {advNo_to_target_spot[advNo]}")
        await update_ad_in_database(
            advNo=advNo,
            target_spot=ad_details['target_spot'],
            asset_type=ad_details['data']['asset'],
            price=ad_details['data']['price'],
            floating_ratio=ad_details['data']['priceFloatingRatio'],
            account=ad_info['account']
        )


if __name__ == "__main__":
    asyncio.run(populate_ads_with_details())
