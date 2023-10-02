import asyncio
import aiohttp
from urllib.parse import urlencode
import hashlib
import hmac
import traceback
import logging
from common_utils import get_server_time
from common_vars import ads_dict
from credentials import credentials_dict
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class BinanceAPI:
    def __init__(self, KEY, SECRET):
        self.KEY = KEY
        self.SECRET = SECRET
        self.session = aiohttp.ClientSession()

    def hashing(self, query_string):
        return hmac.new(self.SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    async def api_call(self, method, endpoint, payload):
        query_string = urlencode(payload)
        signature = self.hashing(query_string)
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": self.KEY,
            "clientType": "WEB",
        }
        query_string += f"&signature={signature}"
        async with self.session.post(f"{endpoint}?{query_string}", json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"API call failed with status code {response.status}: {await response.text()}")
                return None

    async def close_session(self):
        await self.session.close()

    async def get_ad_detail(self, advNo):
        return await self.api_call(
            'post',
            "https://api.binance.com/sapi/v1/c2c/ads/getDetailByNo",
            {
                "adsNo": advNo,
                "timestamp": await get_server_time()
            }
        )
    async def update_ad(self, advNo, priceFloatingRatio):
        return await self.api_call(
            'post',
            "https://api.binance.com/sapi/v1/c2c/ads/update",
            {
                "advNo": advNo,
                "priceFloatingRatio": priceFloatingRatio,
                "timestamp": await get_server_time()
            }
        )
    async def fetch_ads_search(self, asset_type):
        if asset_type == 'BTC':
            transAmount = 15000
            rows = 8
        else:
            rows = 20
            transAmount = 50000
        return await self.api_call(
            'post',
            "https://api.binance.com/sapi/v1/c2c/ads/search",
            {
                "asset": asset_type,
                "fiat": "MXN",
                "page": 1,
                "publisherType": "merchant",
                "rows": rows,
                "tradeType": "BUY",
                "transAmount": transAmount,
                "timestamp": await get_server_time()
            }
        )
async def analyze_and_update_ads(advNo, api_instance, target_spot, asset_type, KEY, SECRET):
    try:
        ad_details = await api_instance.get_ad_detail(advNo)
        if ad_details is None:
            logger.error(f"Failed to get {asset_type} ad details.")
            return
        current_priceFloatingRatio = float(ad_details['data']['priceFloatingRatio'])
        our_current_price = float(ad_details['data']['price'])
        logger.info(f"{asset_type} - start: {our_current_price}, ratio: {current_priceFloatingRatio}")

        ads_response = await api_instance.fetch_ads_search(asset_type)
        if ads_response is None or ads_response.get('code') != '000000' or 'data' not in ads_response:
            logger.error("Failed to fetch ads data.")
            return
        ads_data = ads_response['data']
        if not ads_data:
            logger.error("ads_data list is empty.")
            return
        if asset_type == 'BTC':
            filtered_ads_data = [ad for ad in ads_data if ad['advertiser']['userNo'] != 'sf87c48750d303291a6b2761f410f149e']
        else: 
            filtered_ads_data = [
                ad for ad in ads_data
                if ad['advertiser']['userNo'] != 'safc975e9b2f5388799527f59a7184c40'
                and 'tradeMethods' in ad['adv']
                and any(
                    payment_method.get('tradeMethodName') == 'BBVA'
                    for payment_method in ad['adv']['tradeMethods']
                )
            ]
        if len(filtered_ads_data) < target_spot:
            logger.error("Not enough ads to analyze. Exiting.")
            return
        is_target_ad = str(filtered_ads_data[target_spot - 1]['adv']['advNo']) == str(advNo)  
        if is_target_ad:
            competitor_price = float(filtered_ads_data[target_spot]['adv']['price'])
        else:
            competitor_price = float(filtered_ads_data[target_spot - 1]['adv']['price'])
        logger.info(f"Competitor price: {target_spot}: {competitor_price}")
        price_diff_ratio = (our_current_price / competitor_price)
        new_ratio_unbounded = None
        if price_diff_ratio >= 1:
            new_ratio_unbounded = (current_priceFloatingRatio - ((abs(price_diff_ratio - 1) * 100))) - 0.01
        else:
            new_ratio_unbounded = current_priceFloatingRatio + (((1 - price_diff_ratio) * 100)) - 0.01
        new_ratio = max(102.73, min(110, round(new_ratio_unbounded, 2)))
        if new_ratio == current_priceFloatingRatio:
            logger.info(f"Skipping update.")
            return
        else:
            await api_instance.update_ad(advNo, new_ratio)
            logger.info(f"Updating ratio: {new_ratio}")
    except Exception as e:
        traceback.print_exc()
async def main_loop():
    tasks = []
    api_instances = []
    for account, ads in ads_dict.items():
        KEY = credentials_dict[account]['KEY']
        SECRET = credentials_dict[account]['SECRET']
        api_instance = BinanceAPI(KEY, SECRET)
        api_instances.append(api_instance)
        for ad in ads:
            task = analyze_and_update_ads(ad['advNo'], api_instance, ad['target_spot'], ad['asset'], KEY, SECRET)
            tasks.append(task)
    await asyncio.gather(*tasks)
    for api_instance in api_instances:
        await api_instance.close_session()
async def main_loop_forever():
    while True:
        await main_loop()
        await asyncio.sleep(90)
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main_loop_forever())