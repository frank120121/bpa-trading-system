import aiohttp
import hashlib
import hmac
import asyncio
from credentials import credentials_dict
from common_utils import get_server_timestamp
import logging
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

async def fetch_ads_search(KEY, SECRET, asset_type, fiat, transAmount):
    timestamp = str(await get_server_timestamp())
    if fiat == 'USD':
            payTypes = ["Zelle"]
    elif fiat == 'MXN':
        if asset_type == 'BTC':
            payTypes = None
        else:
            payTypes = ["BBVABank"]

    payload = {
        "asset": asset_type,
        "fiat": fiat,
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
            # Define your asset types, fiat, and transAmount combinations
            search_params = [
                {'asset_type': 'BTC', 'fiat': 'USD', 'transAmount': 990},
                # Add more combinations if necessary
            ]

            # Create tasks for each combination
            tasks = [fetch_ads_search(KEY, SECRET, param['asset_type'], param['fiat'], param['transAmount']) for param in search_params]
            
            results = await asyncio.gather(*tasks)

            # Print results
            for param, ads in zip(search_params, results):
                print(f"{param['asset_type']} Ads with fiat {param['fiat']} and transAmount {param['transAmount']}:\n", ads)
                print()

        asyncio.run(main())
