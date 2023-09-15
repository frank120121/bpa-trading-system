from credentials import credentials_dict
import requests
import time
import hmac
import hashlib

class BinanceWallets:
    def __init__(self):
        self.combined_balances = {}
        self.free_usd_assets_per_account = {}
        self.detailed_free_usd = {}
        self.credentials_dict = credentials_dict

    def generate_signature(self, api_secret, payload):
        signature = hmac.new(api_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    def get_user_assets(self, api_key, api_secret, account):
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            
            signature = self.generate_signature(api_secret, query_string)
            url = f"https://api.binance.com/sapi/v3/asset/getUserAsset?{query_string}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": api_key
            }

            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                assets_data = response.json()
                self.update_balances(assets_data, account, is_funding=False)
        except Exception as e:
            print(f"An exception occurred in get_user_assets: {e}")

    def get_funding_assets(self, api_key, api_secret, account):
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"

            signature = self.generate_signature(api_secret, query_string)
            url = f"https://api.binance.com/sapi/v1/asset/get-funding-asset?{query_string}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": api_key
            }

            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                funding_data = response.json()
                self.update_balances(funding_data, account, is_funding=True)
        except Exception as e:
            print(f"An exception occurred in get_funding_assets: {e}")

    def update_balances(self, asset_data, account, is_funding):
        for data in asset_data:
            asset = data['asset']
            if asset not in self.combined_balances:
                self.combined_balances[asset] = 0

            for balance_type in ['free', 'locked', 'freeze']:
                if balance_type in data:
                    self.combined_balances[asset] += float(data[balance_type])

            if not is_funding:
                if asset == 'USDC' or asset == 'USDT':
                    if account not in self.detailed_free_usd:
                        self.detailed_free_usd[account] = {}
                    self.detailed_free_usd[account][asset] = float(data.get('free', 0))

        if not is_funding:
            usd_assets = ['USDC', 'USDT']
            free_usd = sum(float(data.get('free', 0)) for data in asset_data if data['asset'] in usd_assets)
            self.free_usd_assets_per_account[account] = free_usd

            self.detailed_free_usd[account] = {
                'USDC': sum(float(data.get('free', 0)) for data in asset_data if data['asset'] == 'USDC'),
                'USDT': sum(float(data.get('free', 0)) for data in asset_data if data['asset'] == 'USDT')
            }

    def check_asset_balance(self, asset, target):
        balance = self.combined_balances.get(asset, 0)
        if balance < target:
            return target - balance
        return 0

    def get_account_with_most_usd(self):
        max_free_usd = 0
        max_account = None
        most_usd_asset = None

        for account, assets in self.detailed_free_usd.items():
            total_usd = sum(assets.values())
            if total_usd > max_free_usd:
                max_free_usd = total_usd
                max_account = account
                most_usd_asset = max(assets, key=assets.get)

        return max_account, most_usd_asset
    
    def place_order(self, api_key, api_secret, symbol, side, order_type, quantity=None, price=None, timeInForce=None, quoteOrderQty=None):
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"symbol={symbol}&side={side}&type={order_type}&timestamp={timestamp}"
        
            if quantity is not None:
                query_string += f"&quantity={quantity}"
        
            if price is not None:
                query_string += f"&price={price}"
        
            if timeInForce is not None:
                query_string += f"&timeInForce={timeInForce}"
            
            signature = self.generate_signature(api_secret, query_string)
            url = f"https://api.binance.com/api/v3/order?{query_string}&signature={signature}"

            headers = {
                "X-MBX-APIKEY": api_key
            }

            response = requests.post(url, headers=headers)
        
            if response.status_code == 200:
                order_data = response.json()
                print(f"Order successfully placed: {order_data}")
            else:
                print(f"Failed to place order: {response.text}")

        except Exception as e:
            print(f"An exception occurred in place_order: {e}")

    def main(self):
        for account, cred in credentials_dict.items():
            self.get_user_assets(cred['KEY'], cred['SECRET'], account)
            self.get_funding_assets(cred['KEY'], cred['SECRET'], account)

if __name__ == "__main__":
    wallets = BinanceWallets()
    wallets.main()

