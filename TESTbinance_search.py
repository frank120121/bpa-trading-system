import asyncio
import aiohttp
from urllib.parse import urlencode
import hashlib
import hmac
import os
from dotenv import load_dotenv
import logging
import time
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
url = "https://api.binance.com/sapi/v1/c2c/ads/search"
credentials_dict = {
    'account_1': {
        'KEY': os.environ.get('API_KEY_MFMP'),
        'SECRET': os.environ.get('API_SECRET_MFMP')
    }
}
account = 'account_1'
if account in credentials_dict:
    KEY = credentials_dict[account]['KEY']
    SECRET = credentials_dict[account]['SECRET']
def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
async def fetch_ads_search(KEY, SECRET):
    payload = {
        "asset": "BTC",
        "fiat": "MXN",
        "page": 1,
        "payType": "BBVA",
        "publisherType": "merchant",
        "rows": 3,
        "tradeType": "BUY",
        "transAmount": 15000,
        "timestamp": int(time.time() * 1000)
    }
    query_string = urlencode(payload)
    signature = hashing(query_string, SECRET)

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB",
    }
    query_string += f"&signature={signature}"
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{url}?{query_string}", json=payload, headers=headers) as response:
            if response.status == 200:
                response_data = await response.json()
                print(response_data)
                logger.info("Fetched ads search: success")
                return response_data
            else:
                print(f"Request failed with status code {response.status}: {await response.text()}")
if __name__ == "__main__":
    asyncio.run(fetch_ads_search(KEY, SECRET))

