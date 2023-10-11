import asyncio
from builtins import open
from binance_user_data_ws import main_user_data_ws
from binance_c2c import main_binance_c2c
from binance_update_ads import start_update_ads
from merchant_account import MerchantAccount
from logging_config import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)
asyncio.get_event_loop().set_debug(True)
async def heartbeat():
    while True:
        logger.info("Heartbeat - I'm alive!")
        await asyncio.sleep(300)
async def main():
    merchant_account = MerchantAccount() 
    task1 = asyncio.create_task(main_user_data_ws(merchant_account))
    task2 = asyncio.create_task(main_binance_c2c(merchant_account))
    task3 = asyncio.create_task(start_update_ads()) 
    task4 = asyncio.create_task(heartbeat())
    tasks = [task1, task2, task3, task4]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.error("Tasks cancelled. Cleaning up...")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.error("KeyboardInterrupt received. Cleaning up...")
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.run_until_complete(asyncio.sleep(1))
        loop.stop()
    finally:
        loop.close()


