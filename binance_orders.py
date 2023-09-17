import asyncio
from binance_wallets import BinanceWallets
from binance_price_listener import BinancePriceListener
from datetime import datetime
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

async def get_wallets():
    wallets = BinanceWallets()
    await wallets.main()
    return wallets
async def get_price_listener(asset_symbol):
    price_listener = BinancePriceListener(asset_symbol)
    # Don't await here; you want the function to return immediately
    asyncio.create_task(price_listener.start()) 
    return price_listener
async def new_order(wallets, account_to_use, most_usd_asset, missing_balance, current_btc_price):
    required_usd = missing_balance * current_btc_price
    available_usd = wallets.detailed_free_usd[account_to_use][most_usd_asset]
    if available_usd >= required_usd:     
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{current_time}] Sufficient {most_usd_asset} available in account {account_to_use} to buy missing BTC.")
        
        quantity = required_usd / current_btc_price
        await wallets.place_order(
            api_key=wallets.credentials_dict[account_to_use]['KEY'],
            api_secret=wallets.credentials_dict[account_to_use]['SECRET'],
            symbol=f"BTC{most_usd_asset}",
            side="BUY",
            order_type="MARKET",
            quantity=round(quantity, 5),
            price=None,
            timeInForce=None,
            quoteOrderQty=None
        )
    else:
        print(f"Insufficient {most_usd_asset} in account {account_to_use} to buy missing BTC.")
async def binance_buy_order(asset_type):
    btc_target = 0.35000
    wallets = await get_wallets()
    missing_balance = wallets.check_asset_balance(asset_type, btc_target)
    if missing_balance > 0.00025:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{current_time}] Missing {missing_balance} {asset_type} to reach the target of {btc_target}.")
        account_to_use, most_usd_asset = wallets.get_account_with_most_usd()
        price_listener = await get_price_listener(f'BTC{most_usd_asset}')
        
        current_btc_price = None
        while current_btc_price is None:
            current_btc_price = price_listener.get_current_price()
            await asyncio.sleep(0.5)
        
        await new_order(wallets, account_to_use, most_usd_asset, missing_balance, current_btc_price)
async def main():
    price_listener = await get_price_listener('BTCUSDC')
    await asyncio.gather(
        binance_buy_order('BTC'),
    )
if __name__ == "__main__":
    asyncio.run(binance_buy_order('BTC'))
