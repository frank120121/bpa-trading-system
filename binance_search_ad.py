import aiohttp
import hashlib
import hmac
import asyncio
from credentials import credentials_dict
from common_utils import get_server_timestamp
import logging
from logging_config import setup_logging
setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)

url = "https://api.binance.com/sapi/v1/c2c/ads/search"

def get_credentials():
    account = 'account_1' 
    if account in credentials_dict:
        return credentials_dict[account]['KEY'], credentials_dict[account]['SECRET']
    else:
        logger.error("Account not found in credentials.")
        return None, None

def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

async def fetch_ads_search(KEY, SECRET, asset_type):
    timestamp = str(await get_server_timestamp())
    if asset_type == 'BTC':
        transAmount = 5000
        payTypes = None
    else:
        transAmount = 50000
        payTypes = ["BBVABank"]

    payload = {
        "asset": asset_type,
        "fiat": "MXN",
        "page": 1,
        "publisherType": "merchant",
        "rows": 10,
        "tradeType": "BUY",
        "transAmount": transAmount,
    }
    
    if payTypes:
        payload["payTypes"] = payTypes

    query_string = f"timestamp={timestamp}"
    signature = hashing(query_string, SECRET)

    full_url = f"{url}?{query_string}&signature={signature}"

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(full_url, json=payload, headers=headers) as response:
            if response.status == 200:
                response_data = await response.json()
                logger.debug("Fetched ads search: success")
                return response_data
            else:
                logger.error(f"Request failed with status code {response.status}: {await response.text()}")
                return None
            

if __name__ == "__main__":
    import sys
    import asyncio

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    KEY, SECRET = get_credentials()

    if KEY and SECRET:
        async def main():
            tasks = [fetch_ads_search(KEY, SECRET, asset_type) for asset_type in ["BTC", "USDT"]]
            results = await asyncio.gather(*tasks)
            for asset_type, ads in zip(["BTC", "USDT"], results):
                print(f"{asset_type} Ads:\n", ads)
                print()

        asyncio.run(main())