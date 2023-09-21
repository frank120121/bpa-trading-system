import asyncio
import time
from credentials import credentials_dict
from common_vars import ads_dict
from binance_update_ads import analyze_and_update_ads

async def manage_ads_for_account(account_key, ads):
    KEY = credentials_dict[account_key]['KEY']
    SECRET = credentials_dict[account_key]['SECRET']
    target_position = 1 if account_key == 'account_2' else 4

    while True:
        for ad in ads:
            await analyze_and_update_ads(KEY, SECRET, target_position, ad['advNo'], ad['asset'])
        time.sleep(90) 

if __name__ == "__main__":
   
    tasks = []
    for account_key, ads in ads_dict.items():
        task = asyncio.get_event_loop().create_task(manage_ads_for_account(account_key, ads))
        tasks.append(task)

    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))