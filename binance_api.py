import asyncio
import aiohttp
from urllib.parse import urlencode
import hashlib
import hmac
from common_utils import get_server_timestamp
from binance_search_ad import search_ads
import logging
logger = logging.getLogger(__name__)
class BinanceAPI:

    def __init__(self, KEY, SECRET, session=None):
        self.KEY = KEY
        self.SECRET = SECRET
        if session is None:
            self.session = aiohttp.ClientSession()
        else:
            self.session = session

    def hashing(self, query_string):
        return hmac.new(self.SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    async def api_call(self, method, endpoint, payload, max_retries=3, retry_delay=3):
        for retry_count in range(max_retries):
            try:
                query_string = urlencode(payload)
                signature = self.hashing(query_string)
                headers = {
                    "Content-Type": "application/json;charset=utf-8",
                    "X-MBX-APIKEY": self.KEY,
                    "clientType": "WEB",
                }
                query_string += f"&signature={signature}"
                async with self.session.post(f"{endpoint}?{query_string}", json=payload, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API call to '{method} {endpoint}' with payload '{str(payload)[:50]}...' failed with status code {response.status}: {await response.text()}")
                        return None
            except Exception as e:
                logger.error(f"API call to '{method} {endpoint}' with payload '{str(payload)[:50]}...' failed: {e}") 
        
            if retry_count < max_retries - 1:
                logger.warning(f"Retrying API call in {retry_delay} seconds (attempt {retry_count + 2}/{max_retries})")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Exiting.")

    async def close_session(self):
        await self.session.close()

    async def get_ad_detail(self, advNo):
        logger.info(f'calling get_ad_detail')
        return await self.api_call(
            'post',
            "https://api.binance.com/sapi/v1/c2c/ads/getDetailByNo",
            {
                "adsNo": advNo,
                "timestamp": get_server_timestamp()
            }
        )
    async def update_ad(self, advNo, priceFloatingRatio):
        logger.info(f"Updating ad: {advNo} with rate: {priceFloatingRatio}")
        return await self.api_call(
            'post',
            "https://api.binance.com/sapi/v1/c2c/ads/update",
            {
                "advNo": advNo,
                "priceFloatingRatio": priceFloatingRatio,
                "timestamp": get_server_timestamp()
            }
        )
    async def fetch_ads_search(self, asset_type, fiat, transAmount, payTypes=None):
        logger.info(f'calling fetch_ads_search')
        try:
            # Pass asset_type, fiat, and transAmount to the fetch_ads_search function
            result = await search_ads(self.KEY, self.SECRET, asset_type, fiat, transAmount, payTypes)
            if not result:
                logger.error("Failed to fetch ads data.")
            
            return result
        except Exception as e:
            logger.error(f"An error occurred: {e}")