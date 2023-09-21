import asyncio
import time
from credentials import credentials_dict  
from TESTbinance_update_ads import analyze_and_update_ads, fetch_ads_search, update_ad
from TESTbitso_price_listener import fetch_btcmxn

async def manage_account(account):
    if account in credentials_dict:
        KEY = credentials_dict[account]['KEY']
        SECRET = credentials_dict[account]['SECRET']
        while True:
            await analyze_and_update_ads(KEY, SECRET)
            await asyncio.sleep(5) 

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(manage_account(account)) for account in credentials_dict.keys()]
    tasks.append(loop.create_task(fetch_btcmxn()))
    loop.run_until_complete(asyncio.gather(*tasks))
