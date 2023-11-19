import asyncio
import traceback
from ads_database import update_ad_in_database, fetch_all_ads_from_database, get_ad_from_database
from populate_database import populate_ads_with_details
from credentials import credentials_dict
from binance_api import BinanceAPI
import logging
from logging_config import setup_logging
setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)

def filter_ads(ads_data, base_price, all_ads):
    price_threshold = 1.018
    own_ads = [entry['advNo'] for entry in all_ads]
    return [
        ad for ad in ads_data
        if ad['adv']['advNo'] not in own_ads
        and float(ad['adv']['price']) >= base_price * price_threshold
    ]
def compute_base_price(price: float, floating_ratio: float) -> float:
    base_price = price / (floating_ratio / 100)
    return round(base_price, 2)

def check_if_ads_avail(ads_list, adjusted_target_spot):
        if len(ads_list) < adjusted_target_spot:
            adjusted_target_spot = len(ads_list)
            logger.debug("Adjusted the target spot due to insufficient ads after filtering.")
            return adjusted_target_spot
        else:
            return adjusted_target_spot

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
            logger.debug(f"Ad with advNo: {advNo} not found in the returned list. Fetching from database.")
            our_ad_data_db = await get_ad_from_database(advNo)
            if not our_ad_data_db:
                logger.error(f"Ad with advNo: {advNo} not found in the database either. Skipping...")
                return
            our_current_price = float(our_ad_data_db['price'])
        base_price = compute_base_price(our_current_price, current_priceFloatingRatio)
        filtered_ads = filter_ads(ads_data, base_price, all_ads)
        adjusted_target_spot = check_if_ads_avail(filtered_ads, adjusted_target_spot)


        if not filtered_ads:
            logger.warning(f"Filtered Ads was empty")
            return
        
        competitor_ad = filtered_ads[adjusted_target_spot - 1]
        competitor_price = float(competitor_ad['adv']['price'])
        competitor_ratio = (competitor_price / base_price) * 100


        if our_current_price >= competitor_price:
            new_ratio_unbounded = competitor_ratio - 0.04
        else:
            diff_ratio = competitor_ratio - current_priceFloatingRatio
            if diff_ratio > 0.09:
                new_ratio_unbounded = competitor_ratio - 0.04
            else:
                logger.debug(f"Competitor ad - spot: {adjusted_target_spot}, price: {competitor_price}, base: {base_price} ratio: {competitor_ratio}. Not enough diff: {diff_ratio}")
                return
        new_ratio = max(101.3, min(110, round(new_ratio_unbounded, 2)))
        if new_ratio == current_priceFloatingRatio:
            logger.debug(f"Ratio unchcanged")
            return
        else:       
            await api_instance.update_ad(advNo, new_ratio)
            await update_ad_in_database(advNo, target_spot, asset_type, our_current_price, new_ratio, ad['account'])
            logger.debug(f"ad: {asset_type} - start price: {our_current_price}, ratio: {current_priceFloatingRatio}. Competitor ad - spot: {adjusted_target_spot}, price: {competitor_price}, base: {base_price}, ratio: {competitor_ratio}")
            await asyncio.sleep(2)
    except Exception as e:
        traceback.print_exc()
async def main_loop():
    # Step 1: Fetch all ads from the database
    all_ads = await fetch_all_ads_from_database()
    btc_ads = []
    usdt_ads = []
    for ad in all_ads:
        if ad['asset_type'] == 'BTC':
            btc_ads.append(ad)
        elif ad['asset_type'] == 'USDT':
            usdt_ads.append(ad)

    btc_ads.sort(key=lambda x: x['target_spot'])
    usdt_ads.sort(key=lambda x: x['target_spot'])
    
    # Step 2: Group unique accounts and initialize Binance API instances
    unique_accounts = set(ad['account'] for ad in all_ads)
    api_instances = {account: BinanceAPI(credentials_dict[account]['KEY'], credentials_dict[account]['SECRET']) for account in unique_accounts}

    # Step 3: Process ads by type (BTC & USDT)
    ads_by_type = [('BTC', btc_ads), ('USDT', usdt_ads)]
    for asset_type, ads_list in ads_by_type:
        # Fetch top 10 ads posted for the current asset type from Binance
        first_ad = ads_list[0]
        ads_data = await api_instances[first_ad['account']].fetch_ads_search(asset_type)
        
        # Validate ads_data
        if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
            logger.error(f"Failed to fetch {asset_type} ads data.")
            continue
        
        current_ads_data = ads_data['data']
        if not isinstance(current_ads_data, list):
            logger.error(f"{asset_type} ads_data is not a list.")
            continue
        if not current_ads_data:
            logger.error(f"{asset_type} ads_data list is empty.")
            continue

        # Analyze and update each ad
        for ad in ads_list:
            api_instance = api_instances[ad['account']]
            await analyze_and_update_ads(ad, api_instance, current_ads_data, all_ads)
            await asyncio.sleep(5)

    # Close all API sessions
    for api_instance in api_instances.values():
        await api_instance.close_session()

async def start_update_ads():
    while True: 
        await populate_ads_with_details()
        await asyncio.sleep(5)
        await main_loop()
        await asyncio.sleep(90)
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_update_ads())