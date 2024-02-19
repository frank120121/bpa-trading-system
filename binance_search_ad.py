import aiohttp
import asyncio
from credentials import credentials_dict
from common_utils import get_server_timestamp, hashing
import logging
from binance_endpoints import SEARCH_ADS
logger = logging.getLogger(__name__)


async def search_ads(KEY, SECRET, asset_type, fiat, transAmount, payTypes=None):

    timestamp = str(get_server_timestamp())

    payload = {
        "asset": asset_type,
        "fiat": fiat,
        "page": 1,
        "publisherType": "merchant",
        "rows": 20,
        "tradeType": "BUY",
        "transAmount": transAmount,
    }
    
    if payTypes:
        payload["payTypes"] = payTypes

    query_string = f"timestamp={timestamp}"
    signature = hashing(query_string, SECRET)

    full_url = f"{SEARCH_ADS}?{query_string}&signature={signature}"

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

    def get_credentials():
        account = 'account_1' 
        if account in credentials_dict:
            return credentials_dict[account]['KEY'], credentials_dict[account]['SECRET']
        else:
            logger.error("Account not found in credentials.")
            return None, None
    KEY, SECRET = get_credentials()

    if KEY and SECRET:
        async def main():
            # Define your asset types, fiat, and transAmount combinations
            search_params = [
                {'asset_type': 'USDT', 'fiat': 'USD', 'transAmount': 100, 'payTypes': None},
                # Add more combinations if necessary
            ]

            # Create tasks for each combination
            tasks = [search_ads(KEY, SECRET, param['asset_type'], param['fiat'], param['transAmount'], param['payTypes']) for param in search_params]
            
            results = await asyncio.gather(*tasks)

            # Print results
            for param, ads in zip(search_params, results):
                print(f"{param['asset_type']} Ads with fiat {param['fiat']} and transAmount {param['transAmount']}:\n", ads)
                print()

        asyncio.run(main())
