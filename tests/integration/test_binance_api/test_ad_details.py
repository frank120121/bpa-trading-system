#TESTbinance_getAdDetails.py
import asyncio
from core.credentials import credentials_dict
from exchanges.binance.api import BinanceAPI
from data.cache.share_data import SharedSession
import logging
import sys

logger = logging.getLogger(__name__)





async def main():
    account='account_1'
    api_key = credentials_dict[account]['KEY']
    api_secret = credentials_dict[account]['SECRET']
    try:
        binance_api = await BinanceAPI.get_instance()
        ad = '13797718790974595072'
        response = await binance_api.get_ad_detail(api_key, api_secret, ad)
        print(response)
    finally:
        await binance_api.close_session()
        await SharedSession.close_session()

if __name__ == "__main__":
    asyncio.run(main())