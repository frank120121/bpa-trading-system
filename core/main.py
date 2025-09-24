# bpa/core/main.py
import asyncio
import traceback

from utils.logging_config import setup_logging
from trading.p2p.customer_service.c2c_websocket import main_binance_c2c
from trading.p2p.automation.ads_updater import update_ads_main
from data.database.populate_database import populate_ads_with_details
from data.database.connection import create_connection, DB_FILE
from data.database.deposits.binance_bank_deposit import PaymentManager
from exchanges.binance.api import BinanceAPI
from data.cache.share_data import SharedData, SharedSession
from exchanges.bitso.orderbook import start_bitso_order_book
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

try:
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
except RuntimeError:
    asyncio.new_event_loop().set_debug(True)

async def main(payment_manager, binance_api):
    tasks = []
    try:
        tasks.append(asyncio.create_task(start_bitso_order_book()))
        
        await asyncio.sleep(5)

        tasks.append(asyncio.create_task(main_binance_c2c(payment_manager, binance_api)))
        tasks.append(asyncio.create_task(update_ads_main(binance_api)))
        
        await asyncio.gather(*tasks)
    except Exception as e:
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"An error occurred: {tb_str}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

async def run():
    conn = None
    try:
        conn = await create_connection(DB_FILE)
        binance_api = await BinanceAPI.get_instance()
        payment_manager = await PaymentManager.get_instance()
        await payment_manager.initialize_payment_account_cache(conn)
        await populate_ads_with_details(binance_api)
        await main(payment_manager, binance_api)
    except Exception as e:
        logger.error(f"An error occurred during initialization: {e}")
    finally:
        if conn:
            await conn.close()
        await SharedData.save_all_ads_to_database()
        await binance_api.close_session() 
        await SharedSession.close_session()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received exit signal, shutting down...")
        asyncio.run(SharedData.save_all_ads_to_database())
