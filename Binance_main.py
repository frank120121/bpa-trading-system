import asyncio
from Binance_user_data_ws import main_user_data_ws
from binance_c2c import main_binance_c2c
from merchant_account import MerchantAccount
from logging_config import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__) 
asyncio.get_event_loop().set_debug(True)
async def main():
    merchant_account = MerchantAccount()
    task1 = asyncio.create_task(main_user_data_ws(merchant_account))
    task2 = asyncio.create_task(main_binance_c2c(merchant_account))
    try:
        await asyncio.gather(task1, task2)
    except KeyboardInterrupt:
        logger.error("KeyboardInterrupt received. Cleaning up...")
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.stop()
    finally:
        loop.close()
