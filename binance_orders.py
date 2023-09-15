from binance_wallets import BinanceWallets
from binance_price_listener import BinancePriceListener
import time

def get_wallets():
    wallets = BinanceWallets()
    wallets.main()
    return wallets

def get_price_listener(asset_symbol):
    price_listener = BinancePriceListener(asset_symbol)
    price_listener.start()
    return price_listener

def new_order(wallets, account_to_use, most_usd_asset, missing_balance, current_btc_price):
    required_usd = missing_balance * current_btc_price
    available_usd = wallets.detailed_free_usd[account_to_use][most_usd_asset]

    if available_usd >= required_usd:
        print(f"Sufficient {most_usd_asset} available in account {account_to_use} to buy missing BTC.")
        
        # Calculate the quantity of BTC to buy with available USD
        quantity = required_usd / current_btc_price

        # Place a market order to buy BTC using the specified asset (e.g., USDC)
        wallets.place_order(
            api_key=wallets.credentials_dict[account_to_use]['KEY'],
            api_secret=wallets.credentials_dict[account_to_use]['SECRET'],
            symbol=f"BTC{most_usd_asset}",
            side="BUY",
            order_type="MARKET",
            quantity = round(quantity, 5),
            price = None,
            timeInForce=None,   # No need to specify timeInForce for a market order
            quoteOrderQty=None  # Set quoteOrderQty to None
        )
    else:
        print(f"Insufficient {most_usd_asset} in account {account_to_use} to buy missing BTC.")



def binance_buy_order(asset_type):
    wallets = get_wallets()
    
    btc_target = 0.35000
                
    missing_balance = wallets.check_asset_balance(asset_type, btc_target)
    if missing_balance > 0.00025:
        print(f"Missing {missing_balance} {asset_type} to reach the target of {btc_target}.")

        account_to_use, most_usd_asset = wallets.get_account_with_most_usd()
        
        price_listener = get_price_listener(f'BTC{most_usd_asset}')
        
        current_btc_price = None
        while current_btc_price is None:
            current_btc_price = price_listener.get_current_price()
            time.sleep(0.5)
        
        new_order(wallets, account_to_use, most_usd_asset, missing_balance, current_btc_price)


def binance_sell_order(asset_type):
    wallets = get_wallets()
    
    btc_target = 0.35000
                
    excess_balance = wallets.check_asset_balance(asset_type, btc_target)
    if excess_balance > btc_target:
        print(f"Excess {excess_balance} {asset_type} over the target of {btc_target}.")

        account_to_use, _ = wallets.get_account_with_most_usd()
        
        # TODO: Determine 
        print(f"Account to use for selling BTC: {account_to_use}")
        # TODO: Place order

if __name__ == "__main__":
    # For testing
    binance_buy_order('BTC')
    binance_sell_order('BTC')
