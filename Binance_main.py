import asyncio
from Binance_user_data_ws import main_user_data_ws
from TESTbinance_c2c import main_binance_c2c
from merchant_account import MerchantAccount 

async def main():
    merchant_account = MerchantAccount()
    task1 = asyncio.create_task(main_user_data_ws(merchant_account))
    task2 = asyncio.create_task(main_binance_c2c(merchant_account))
    
    await asyncio.gather(task1, task2)

if __name__ == "__main__":
    asyncio.run(main())

