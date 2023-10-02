import asyncio
from Binance_user_data_ws import main_user_data_ws
from binance_c2c import main_binance_c2c
from merchant_account import MerchantAccount
from logging_config import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__) 

# Enable asyncio debug mode
asyncio.get_event_loop().set_debug(True)

async def main():
    merchant_account = MerchantAccount()
    task1 = asyncio.create_task(main_user_data_ws(merchant_account))
    task2 = asyncio.create_task(main_binance_c2c(merchant_account))
    
    try:
        await asyncio.gather(task1, task2)
    except KeyboardInterrupt:
        logger.error("KeyboardInterrupt received. Cleaning up...")

        # Add cleanup actions here:
        # 1. Close WebSocket connections
        # 2. Log a message
        # 3. Save state if needed
        # 4. Release resources
        # 5. Signal background tasks to stop gracefully
        # ...

if __name__ == "__main__":
    asyncio.run(main())
