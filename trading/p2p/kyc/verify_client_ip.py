import asyncio
from exchanges.binance.api import BinanceAPI
from core.credentials import credentials_dict

async def debug_main():
    binance_api = await BinanceAPI.get_instance()
    
    # Replace 'your_account' with the actual account name that has this ad
    account = 'account_1'
    KEY = credentials_dict[account]['KEY']
    SECRET = credentials_dict[account]['SECRET']
    
    await binance_api.investigate_problematic_ad(KEY, SECRET)
    await binance_api.close_session()

if __name__ == "__main__":
    asyncio.run(debug_main())