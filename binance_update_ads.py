import asyncio
import traceback
import logging
from ads_database import update_ad_in_database, fetch_all_ads_from_database, get_ad_from_database
from populate_database import populate_ads_with_details
from credentials import credentials_dict
from binance_api import BinanceAPI
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async def start_update_ads():
    await main_loop_forever()
def filter_ads(ads_data, advNo):
    unwanted_users = ['safc975e9b2f5388799527f59a7184c40', 'sf87c48750d303291a6b2761f410f149e']
    return [ad for ad in ads_data if ad['advertiser']['userNo'] not in unwanted_users and ad['adv']['advNo'] != advNo]

async def analyze_and_update_ads(ad, api_instance, ads_data):
    advNo = ad['advNo']
    target_spot = ad['target_spot']
    adjusted_target_spot = target_spot
    asset_type = ad['asset_type']
    current_priceFloatingRatio = float(ad['floating_ratio'])

    try:
        logger.debug(f"All advNos in ads_data: {[item['adv']['advNo'] for item in ads_data]}")
        our_ad_data = next((item for item in ads_data if item['adv']['advNo'] == advNo), None)
        
        if our_ad_data:
            our_current_price = float(our_ad_data['adv']['price'])
        else:
            logger.debug(f"Ad with advNo: {advNo} not found in the returned list. Fetching from database.")
            our_ad_data_db = await get_ad_from_database(advNo)
            if not our_ad_data_db:
                logger.error(f"Ad with advNo: {advNo} not found in the database either. Skipping...")
                return
            our_current_price = float(our_ad_data_db['price'])
    
        logger.info(f"{asset_type} - start: {our_current_price}, ratio: {current_priceFloatingRatio}")
        filtered_ads_data = filter_ads(ads_data, advNo)
        if len(filtered_ads_data) < adjusted_target_spot:
            adjusted_target_spot = len(filtered_ads_data)
            logger.debug("Adjusted the target spot due to insufficient ads after filtering.")
        competitor_ad = filtered_ads_data[adjusted_target_spot - 1]
        competitor_price = float(competitor_ad['adv']['price'])
        logger.info(f"Competitor price: {adjusted_target_spot}: {competitor_price}")
        price_diff_ratio = (our_current_price / competitor_price)
        new_ratio_unbounded = None
        if price_diff_ratio >= 1:
            new_ratio_unbounded = (current_priceFloatingRatio - ((abs(price_diff_ratio - 1) * 100))) - 0.01
        else:
            new_ratio_unbounded = current_priceFloatingRatio + (((1 - price_diff_ratio) * 100)) - 0.01
        new_ratio = max(101.43, min(110, round(new_ratio_unbounded, 2)))
        if new_ratio == current_priceFloatingRatio:
            logger.debug(f"Skipping update.")
            return
        else:
            await asyncio.sleep(1)
            await api_instance.update_ad(advNo, new_ratio)
            await update_ad_in_database(advNo, target_spot, asset_type, our_current_price, new_ratio, ad['account'])
            logger.debug(f"Updating ratio: {new_ratio}")
            await asyncio.sleep(1)
    except Exception as e:
        traceback.print_exc()
async def main_loop():
    api_instances = {}
    all_ads = await fetch_all_ads_from_database()
    btc_ads = sorted([ad for ad in all_ads if ad['asset_type'] == 'BTC'], key=lambda x: x['target_spot'])
    usdt_ads = sorted([ad for ad in all_ads if ad['asset_type'] == 'USDT'], key=lambda x: x['target_spot'])
    unique_accounts = set(ad['account'] for ad in all_ads)
    for account in unique_accounts:
        KEY = credentials_dict[account]['KEY']
        SECRET = credentials_dict[account]['SECRET']
        api_instance = BinanceAPI(KEY, SECRET)
        api_instances[account] = api_instance
    ads_by_type = [('BTC', btc_ads), ('USDT', usdt_ads)]
    for asset_type, ads_list in ads_by_type:
        first_ad = ads_list[0]
        ads_data = await api_instances[first_ad['account']].fetch_ads_search(asset_type)
        
        if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
            logger.error(f"Failed to fetch {asset_type} ads data.")
            continue
        ads_data = ads_data['data']
        if not ads_data:
            logger.error(f"{asset_type} ads_data list is empty.")
            continue
        for ad in ads_list:
            api_instance = api_instances[ad['account']]
            await analyze_and_update_ads(ad, api_instance, ads_data)
            await asyncio.sleep(2)
    for api_instance in api_instances.values():
        await api_instance.close_session()
async def chained_tasks():
    await asyncio.sleep(45)
    await populate_ads_with_details()
async def main_loop_forever():
    while True:
        await main_loop()
        populate_task = asyncio.create_task(chained_tasks())
        await asyncio.sleep(45)
        await populate_task
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main_loop_forever())