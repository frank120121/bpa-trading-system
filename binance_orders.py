import asyncio
from binance_wallets import BinanceWallets
import traceback
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

async def get_wallets():
    wallets = BinanceWallets()
    await wallets.main()
    return wallets

async def new_order(wallets, account_to_use, most_usd_asset, missing_balance):
    try: 
        await wallets.place_order(
            api_key=wallets.credentials_dict[account_to_use]['KEY'],
            api_secret=wallets.credentials_dict[account_to_use]['SECRET'],
            symbol=f"BTC{most_usd_asset}",
            side="BUY",
            order_type="MARKET",
            quantity=round(missing_balance, 5),
            price=None,
            timeInForce=None,
            quoteOrderQty=None
        )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        logging.error(traceback.format_exc())

async def binance_buy_order(asset_type):
    try: 
        btc_target = 0.35000
        wallets = await get_wallets()
        missing_balance = wallets.check_asset_balance(asset_type, btc_target)

        logger.info(f"Inside binance_buy_order for {asset_type}")
        logger.info(f"Missing balance for {asset_type}: {missing_balance}")

        if missing_balance > 0.00025:
            account_to_use, most_usd_asset = wallets.get_account_with_most_usd()
            logger.debug(f'account to use:{account_to_use}, most usd asset: {most_usd_asset}')

            await new_order(wallets, account_to_use, most_usd_asset, missing_balance)
        
        else: 
            logger.info(f"No missing balance for {asset_type}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        logging.error(traceback.format_exc())

async def binance_orders_main(loop):
    print("Inside binance_buy_order main")
    await asyncio.gather(
        binance_buy_order('BTC'),
    )
    print("Exiting binance_buy_order main")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(binance_orders_main(loop))

