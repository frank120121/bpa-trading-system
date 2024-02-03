import asyncio
import traceback
import logging
from logging_config import setup_logging
from ads_database import update_ad_in_database, fetch_all_ads_from_database
from credentials import credentials_dict
from binance_api import BinanceAPI

setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)

PRICE_THRESHOLD = 1.0163
MIN_RATIO = 101.14
MAX_RATIO = 110
RATIO_ADJUSTMENT = 0.04
DIFF_THRESHOLD = 0.09
DELAY_BETWEEN_ASSET_TYPES = 5
DELAY_BETWEEN_MAIN_LOOPS = 180

def filter_ads(ads_data, base_price, own_ads):
    own_adv_nos = [ad['advNo'] for ad in own_ads]
    logger.debug(f'own ad numbers: {own_adv_nos}')
    return [ad for ad in ads_data if ad['adv']['advNo'] not in own_adv_nos and float(ad['adv']['price']) >= base_price * PRICE_THRESHOLD]


def compute_base_price(price: float, floating_ratio: float) -> float:
    return round(price / (floating_ratio / 100), 2)

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
    asset_type = ad['asset_type']
    current_priceFloatingRatio = float(ad['floating_ratio'])
    surplusAmount = ad['surplused_amount']
    fiat = ad['fiat']
    transAmount = ad['transAmount']

    try:
        our_ad_data = next((item for item in ads_data if item['adv']['advNo'] == advNo), None)
        logger.debug(f'Ads_data: {ads_data}')

        if not our_ad_data:
            our_ad_data = await api_instance.get_ad_detail(advNo)
            if our_ad_data is None or 'data' not in our_ad_data:
                logger.error(f"Failed to get details for ad number {advNo}")
                return
            await update_ad_in_database(
                target_spot=target_spot,
                advNo=advNo,
                asset_type=our_ad_data['data']['asset'],
                floating_ratio=our_ad_data['data']['priceFloatingRatio'],
                price=our_ad_data['data']['price'],
                surplusAmount=our_ad_data['data']['surplusAmount'],
                account=ad['account'],
                fiat=fiat,
                transAmount=transAmount
            )
            our_current_price = float(our_ad_data['data']['price'])
        else:
            our_current_price = float(our_ad_data['adv']['price'])

        base_price = compute_base_price(our_current_price, current_priceFloatingRatio)
        logger.info(f"Base Price: {base_price}")
        filtered_ads = filter_ads(ads_data, base_price, all_ads)
        adjusted_target_spot = check_if_ads_avail(filtered_ads, target_spot)

        if not filtered_ads:
            logger.info(f"No competitor ads found for {advNo}")
            return

        competitor_ad = filtered_ads[adjusted_target_spot - 1]
        logger.debug(f'Competitor ad: {competitor_ad}')
        competitor_price = float(competitor_ad['adv']['price'])
        competitor_ratio = (competitor_price / base_price) * 100

        if our_current_price >= competitor_price:
            new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT
        else:
            diff_ratio = competitor_ratio - current_priceFloatingRatio
            if diff_ratio > DIFF_THRESHOLD:
                new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT
            else:
                logger.debug(f"Competitor ad - spot: {adjusted_target_spot}, price: {competitor_price}, base: {base_price}, ratio: {competitor_ratio}. Not enough diff: {diff_ratio}")
                return

        new_ratio = max(MIN_RATIO, min(MAX_RATIO, round(new_ratio_unbounded, 2)))
        if new_ratio == current_priceFloatingRatio:
            logger.debug(f"Ratio unchanged")
            return
        else:
            await api_instance.update_ad(advNo, new_ratio)
            await update_ad_in_database(target_spot, advNo, asset_type, new_ratio, None, surplusAmount, ad['account'], fiat, transAmount)
            logger.debug(f"Ad: {asset_type} - start price: {our_current_price}, ratio: {current_priceFloatingRatio}. Competitor ad - spot: {adjusted_target_spot}, price: {competitor_price}, base: {base_price}, ratio: {competitor_ratio}")
            await asyncio.sleep(5)

    except Exception as e:
        traceback.print_exc()
async def process_ads(ads_list, api_instances, all_ads):
    if not ads_list:
        return

    # Assuming all ads in the list have the same transAmount, fiat, and asset_type
    transAmount = ads_list[0]['transAmount']
    fiat = ads_list[0]['fiat']
    asset_type = ads_list[0]['asset_type']

    # Fetch ads data once for the entire group
    api_instance = api_instances[ads_list[0]['account']]
    ads_data = await api_instance.fetch_ads_search(asset_type, fiat, transAmount)

    # Validate ads_data
    if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
        logger.error(f"Failed to fetch ads data for asset_type {asset_type}, fiat {fiat}, and transAmount {transAmount}.")
        return

    current_ads_data = ads_data['data']
    if not isinstance(current_ads_data, list) or not current_ads_data:
        logger.error(f"Ads data list for asset_type {asset_type}, fiat {fiat}, and transAmount {transAmount} is not valid.")
        return

    # Sort ads by target_spot within the group
    sorted_ads_list = sorted(ads_list, key=lambda x: x['target_spot'])

    # Process each ad with the fetched ads_data
    for ad in sorted_ads_list:
        await analyze_and_update_ads(ad, api_instance, current_ads_data, all_ads)
        await asyncio.sleep(2)  # Delay between processing each ad


async def main_loop():
    all_ads = await fetch_all_ads_from_database()
    logger.debug(f'all ads: {all_ads}')

    # Group ads by transAmount
    grouped_ads = {}
    for ad in all_ads:
        transAmount_group = grouped_ads.setdefault(ad['transAmount'], [])
        transAmount_group.append(ad)

    api_instances = {account: BinanceAPI(credentials_dict[account]['KEY'], credentials_dict[account]['SECRET']) for account in set(ad['account'] for ad in all_ads)}

    # Process each transAmount group with a delay between each group
    for transAmount, ads_group in grouped_ads.items():
        await process_ads(ads_group, api_instances, all_ads)
        await asyncio.sleep(DELAY_BETWEEN_ASSET_TYPES)

    for api_instance in api_instances.values():
        await api_instance.close_session()



async def start_update_ads():
    while True: 
        await main_loop()
        await asyncio.sleep(DELAY_BETWEEN_MAIN_LOOPS)
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_update_ads())