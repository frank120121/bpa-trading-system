import asyncio
import traceback
import logging
from ads_database import update_ad_in_database, fetch_all_ads_from_database, get_ad_from_database
from populate_database import populate_ads_with_details
from credentials import credentials_dict
from binance_api import BinanceAPI
from common_vars import ads_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async def start_update_ads():
    await main_loop_forever()
def filter_ads(ads_data, base_price, all_ads):
    own_ads = [entry['advNo'] for entry in all_ads]
    return [
        ad for ad in ads_data
        if ad['adv']['advNo'] not in own_ads
        and float(ad['adv']['price']) >= base_price * 1.0142
    ]
def compute_base_price(price: float, floating_ratio: float) -> float:
    base_price = price / (floating_ratio / 100)
    return round(base_price, 2)
def compute_median_price(top_ads):
    prices = sorted([float(ad['adv']['price']) for ad in top_ads])
    n = len(prices)
    m = n - 1
    return (prices[m // 2] + prices[(m + 1) // 2]) / 2
def check_if_ads_avail(ads_list, adjusted_target_spot):
        if len(ads_list) < adjusted_target_spot:
            adjusted_target_spot = len(ads_list)
            logger.info("Adjusted the target spot due to insufficient ads after filtering.")
            return adjusted_target_spot
        else:
            return adjusted_target_spot
async def fetch_ads_data(api_instance, asset_type):
    ads_data = await api_instance.fetch_ads_search(asset_type)
    if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
        logger.error(f"Failed to fetch {asset_type} ads data.")
        return None
    return ads_data['data']


async def analyze_and_update_ads(ad, api_instance, ads_data, all_ads):
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
            logger.warning(f"Ad with advNo: {advNo} not found in the returned list. Fetching from database.")
            our_ad_data_db = await get_ad_from_database(advNo)
            if not our_ad_data_db:
                logger.error(f"Ad with advNo: {advNo} not found in the database either. Skipping...")
                return
            our_current_price = float(our_ad_data_db['price'])
        base_price = compute_base_price(our_current_price, current_priceFloatingRatio)
        filtered_ads = filter_ads(ads_data, base_price, all_ads)
  

        if asset_type == "USDT":
            log_data = [(ad['adv']['advNo'], ad['adv']['price']) for ad in ads_data]
            logger.info(f"All competitor ads: {log_data}")

            top_ads = filtered_ads[:4]
            log_data = [(ad['adv']['advNo'], ad['adv']['price']) for ad in top_ads]
            logger.info(f"Top ads after filter_ads: {log_data}")

            med_price = compute_median_price(top_ads)
            logger.info(f"Med price: {med_price}")
            filtered_ads_med = [ad for ad in filtered_ads if float(ad['adv']['price']) >= med_price]
            log_data = [(ad['adv']['advNo'], ad['adv']['price']) for ad in filtered_ads_med]
            logger.info(f"Filtered ads after removing ads <= med_price: {log_data}")


            top_filtered = filtered_ads_med[:4]
            log_data = [(ad['adv']['advNo'], ad['adv']['price']) for ad in top_filtered]
            logger.info(f"Top filtered ads: {log_data}")

            

            if len(top_filtered) > 1:
        
                if adjusted_target_spot == 1:
                    top_ads_gaps = [float(top_ads[i + 1]['adv']['price']) - float(top_ads[i]['adv']['price']) for i in range(len(top_ads) - 1)]
                    if top_ads_gaps[0] >= 0.05:
                        adjusted_target_spot = 2
                        adjusted_target_spot = check_if_ads_avail(filtered_ads, adjusted_target_spot)
                        competitor_ad = filtered_ads[adjusted_target_spot - 1]
                    else: 
                        adjusted_target_spot = check_if_ads_avail(top_filtered, adjusted_target_spot)
                        competitor_ad = top_filtered[adjusted_target_spot - 1]
                else:
                    gaps = [float(top_filtered[i + 1]['adv']['price']) - float(top_filtered[i]['adv']['price']) for i in range(len(top_filtered) - 1)]
                    if max(gaps) >= 0.05:
                        max_gap_index = gaps.index(max(gaps))
                        adjusted_target_spot = max_gap_index + 1
                        adjusted_target_spot = check_if_ads_avail(top_filtered, adjusted_target_spot)
                        competitor_ad = top_filtered[adjusted_target_spot - 1]
                    else:
                        
                        adjusted_target_spot = len(top_filtered)
                        adjusted_target_spot = check_if_ads_avail(filtered_ads, adjusted_target_spot)
                        competitor_ad = filtered_ads_med[adjusted_target_spot - 1]

            competitor_price = float(competitor_ad['adv']['price'])
            price_diff_ratio = (our_current_price / competitor_price)
            log_data = (competitor_ad['adv']['advNo'], competitor_ad['adv']['price'])
            logger.info(f"comp ad: {log_data}")

        adjusted_target_spot = check_if_ads_avail(filtered_ads, adjusted_target_spot)
        if asset_type == "BTC":
            competitor_ad = filtered_ads[adjusted_target_spot - 1]
            competitor_price = float(competitor_ad['adv']['price'])
            price_diff_ratio = (our_current_price / competitor_price)

        new_ratio_unbounded = None
        diff_ratio = None
        if price_diff_ratio >= 1:
            new_ratio_unbounded = (current_priceFloatingRatio - ((abs(price_diff_ratio - 1) * 100))) - 0.03
        else:
            new_ratio_unbounded = current_priceFloatingRatio + (((1 - price_diff_ratio) * 100)) - 0.01
            diff_ratio = new_ratio_unbounded  - current_priceFloatingRatio
            if diff_ratio <= 0.07:
                logger.debug(f"Not enough Diff: {diff_ratio}")
                return
        new_ratio = max(101.5, min(110, round(new_ratio_unbounded, 2)))
        
        if new_ratio == current_priceFloatingRatio:
            logger.debug(f"Ratio unchcanged")
            return
        else:       
            logger.info(f"{asset_type} - start price: {our_current_price}, ratio: {current_priceFloatingRatio}")
            logger.info(f"Competitor - spot: {adjusted_target_spot}, price: {competitor_price}, base: {base_price}")
            await api_instance.update_ad(advNo, new_ratio)
            await update_ad_in_database(advNo, target_spot, asset_type, our_current_price, new_ratio, ad['account'])
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
        ads_data = await fetch_ads_data(api_instances[first_ad['account']], asset_type)
        if not ads_data:
            continue
        if isinstance(ads_data, dict) and 'data' in ads_data:
            ads_data = ads_data['data']
        if not isinstance(ads_data, list):
            logger.error(f"{asset_type} ads_data is not a list.")
            continue
        if not ads_data:
            logger.error(f"{asset_type} ads_data list is empty.")
            continue
        for ad in ads_list:
            api_instance = api_instances[ad['account']]
            await analyze_and_update_ads(ad, api_instance, ads_data, all_ads)
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