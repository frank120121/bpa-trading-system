from binance_price_listener import BinancePriceListener
from TESTuser_data_ws import start_binance_user_stream
import asyncio

async def main():
    price_listener = BinancePriceListener('BTCUSDT')
    try:
        await price_listener.start()
    except KeyboardInterrupt:
        await price_listener.stop()
    try:
        await start_binance_user_stream()
    except Exception as e:
        print(f"An error occurred while running Binance user stream: {e}")
if __name__ == "__main__":
    asyncio.run(main())
