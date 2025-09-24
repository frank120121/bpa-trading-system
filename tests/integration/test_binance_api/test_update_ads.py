# bpa/binance_update_ads.py
import asyncio
import traceback
import logging
from core.credentials import credentials_dict
from data.cache.share_data import SharedSession, SharedData
from data.database.operations.ads_database import update_ad_in_database
from exchanges.binance.api import BinanceAPI
from TESTbitso_order_book_cache import reference_prices
from data.database.populate_database import populate_ads_with_details
from TESTBitsoOrderBook import start_bitso_order_book

logger = logging.getLogger(__name__)

# Constants
SELL_PRICE_THRESHOLD = 0.9960
SELL_PRICE_ADJUSTMENT = 0
BUY_PRICE_THRESHOLD = 1.0128  
PRICE_THRESHOLD_2 = 1.0548
MIN_RATIO = 90.00
MAX_RATIO = 110.00
RATIO_ADJUSTMENT = 0.05
DIFF_THRESHOLD = 0.15
BASE = 0.005
OXXO_PRICE_THRESHOLD = 1.03

def validate_constants():
    """Validate that all price thresholds are reasonable"""
    thresholds = {
        'SELL_PRICE_THRESHOLD': SELL_PRICE_THRESHOLD,
        'BUY_PRICE_THRESHOLD': BUY_PRICE_THRESHOLD,
        'PRICE_THRESHOLD_2': PRICE_THRESHOLD_2,
        'OXXO_PRICE_THRESHOLD': OXXO_PRICE_THRESHOLD
    }
    
    logger.info("=== VALIDATING PRICE THRESHOLDS ===")
    for name, value in thresholds.items():
        if value < 0.5 or value > 2.0:
            logger.error(f"SUSPICIOUS threshold value: {name} = {value}")
        else:
            logger.info(f"Valid threshold {name} = {value}")

def ensure_numeric(value, default=0.0):
    """Ensure value is numeric (for C2C API compatibility)"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value) if '.' in value else int(value)
        except (ValueError, TypeError):
            return default
    return default

def ensure_integer(value, default=0):
    """Ensure value is integer (for target_spot)"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    return default

def filter_ads(ads_data, base_price, own_ads, trans_amount_threshold, price_threshold, minTransAmount, is_buy=True):
    """Filter ads with detailed logging"""
    own_adv_nos = [ad['advNo'] for ad in own_ads]
    
    logger.info(f"=== FILTERING ADS ===")
    logger.info(f"  base_price: {base_price}")
    logger.info(f"  price_threshold: {price_threshold}")
    logger.info(f"  trans_amount_threshold: {trans_amount_threshold}")
    logger.info(f"  minTransAmount: {minTransAmount}")
    logger.info(f"  is_buy: {is_buy}")
    logger.info(f"  Target price range: {'>' if is_buy else '<='} {base_price * price_threshold}")
    logger.info(f"  Total ads to filter: {len(ads_data)}")
    
    filtered = []
    for i, ad in enumerate(ads_data):
        adv_data = ad['adv']
        price = float(adv_data['price'])
        max_amount = float(adv_data['dynamicMaxSingleTransAmount'])
        min_amount = float(adv_data['minSingleTransAmount'])
        
        # Check each condition separately for debugging
        own_ad_check = adv_data['advNo'] not in own_adv_nos
        price_check = (price > (base_price * price_threshold)) if is_buy else (price <= base_price * price_threshold)
        max_amount_check = max_amount >= trans_amount_threshold
        min_amount_check = min_amount <= minTransAmount
        
        logger.info(f"  Ad {i+1} ({adv_data['advNo'][:10]}...): price={price}")
        
        if not own_ad_check:
            logger.info(f"    FILTERED: own ad")
        elif not price_check:
            logger.info(f"    FILTERED: price {price} doesn't meet threshold (need {'>' if is_buy else '<='} {base_price * price_threshold})")
        elif not max_amount_check:
            logger.info(f"    FILTERED: max amount {max_amount} < {trans_amount_threshold}")
        elif not min_amount_check:
            logger.info(f"    FILTERED: min amount {min_amount} > {minTransAmount}")
        else:
            logger.info(f"    KEPT: meets all criteria")
            filtered.append(ad)
    
    logger.info(f"RESULT: Filtered {len(filtered)} ads from {len(ads_data)} total")
    return filtered

def determine_price_threshold(payTypes, is_buy=True):
    """Determine price threshold with proper debugging and strict limits"""
    logger.info(f"=== DETERMINING PRICE THRESHOLD ===")
    logger.info(f"  payTypes: {payTypes}")
    logger.info(f"  payTypes type: {type(payTypes)}")
    logger.info(f"  is_buy: {is_buy}")
    
    # Handle both string and list payTypes
    if payTypes is not None:
        if isinstance(payTypes, str):
            payTypes_to_check = [payTypes]
        elif isinstance(payTypes, list):
            payTypes_to_check = payTypes
        else:
            logger.warning(f"Unexpected payTypes type: {type(payTypes)}")
            payTypes_to_check = []
            
        logger.info(f"  payTypes_to_check: {payTypes_to_check}")
        
        # Check OXXO FIRST (most specific)
        if 'OXXO' in payTypes_to_check:
            threshold = OXXO_PRICE_THRESHOLD if is_buy else SELL_PRICE_THRESHOLD
            logger.info(f"  Using OXXO threshold: {threshold}")
            return threshold
        
        # Then check other special payment types
        special_payTypes = ['BANK', 'ZELLE', 'SkrillMoneybookers']
        if any(payType in payTypes_to_check for payType in special_payTypes):
            threshold = PRICE_THRESHOLD_2 if is_buy else SELL_PRICE_THRESHOLD
            logger.info(f"  Using special payTypes threshold: {threshold}")
            return threshold
    
    threshold = BUY_PRICE_THRESHOLD if is_buy else SELL_PRICE_THRESHOLD
    logger.info(f"  Using default threshold: {threshold}")
    return threshold

def compute_base_price(price: float, floating_ratio: float) -> float:
    result = round(price / (floating_ratio / 100), 2)
    logger.info(f"compute_base_price: {price} / ({floating_ratio} / 100) = {result}")
    return result

def check_if_ads_avail(ads_list, adjusted_target_spot):
    original_spot = adjusted_target_spot
    if len(ads_list) < adjusted_target_spot:
        adjusted_target_spot = len(ads_list)
        logger.info(f"Adjusted target_spot from {original_spot} to {adjusted_target_spot} (available ads: {len(ads_list)})")
        return adjusted_target_spot
    else:
        logger.info(f"Target_spot {adjusted_target_spot} is available (ads available: {len(ads_list)})")
        return adjusted_target_spot
    
def adjust_ratio(new_ratio_unbounded, is_buy):
    if is_buy:
        THRESHOLD = round((BUY_PRICE_THRESHOLD * 100), 2)
        new_ratio = max(THRESHOLD, min(MAX_RATIO, round(new_ratio_unbounded, 2)))
    else:
        THRESHOLD = round((SELL_PRICE_THRESHOLD * 100), 2)
        new_ratio = max(MIN_RATIO, min(THRESHOLD, round(new_ratio_unbounded, 2)))
    
    logger.info(f"adjust_ratio: {new_ratio_unbounded} -> {new_ratio} (is_buy: {is_buy})")
    return new_ratio
    
async def retry_fetch_ads(binance_api, KEY, SECRET, ad, is_buy, page_start=1, page_end=10):
    advNo = ad.get('advNo')
    logger.info(f"=== RETRY FETCH ADS for {advNo} ===")
    
    for page in range(page_start, page_end):
        transAmount = ensure_numeric(ad['transAmount'])
        logger.info(f"  Trying page {page} with transAmount {transAmount}")
        
        ads_data = await binance_api.fetch_ads_search(KEY, SECRET, 'BUY' if is_buy else 'SELL', ad['asset_type'], ad['fiat'], transAmount, ad['payTypes'], page)
        if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
            logger.error(f"  Failed to fetch ads data for page {page}")
            continue

        current_ads_data = ads_data['data']
        our_ad_data = next((item for item in current_ads_data if item['adv']['advNo'] == advNo), None)
        if our_ad_data:
            logger.info(f"  Found ad {advNo} on page {page}")
            return current_ads_data

    logger.error(f"Failed to fetch ads for ad number {advNo} after checking {page_end - page_start} pages.")
    return []

async def is_ad_online(binance_api, KEY, SECRET, advNo):
    try:
        response = await binance_api.get_ad_detail(KEY, SECRET, advNo)
        if response and response.get('code') == '000000' and 'data' in response:
            ad_status = response['data'].get('advStatus')
            is_online = ad_status == 1
            logger.info(f"Ad {advNo} online status: {is_online} (status={ad_status})")
            return is_online
        else:
            logger.error(f"Failed to get ad details for advNo {advNo}: {response}")
            return False
    except Exception as e:
        logger.error(f"An error occurred while checking ad status for advNo {advNo}: {e}")
        return False

async def analyze_and_update_ads(ad, binance_api, KEY, SECRET, ads_data, all_ads, is_buy: bool, batch_updates: list = None, shared_data_updates: list = None):
    if not ad:
        logger.error("Ad data is missing. Skipping...")
        return

    advNo = ad.get('advNo')
    logger.info(f"=== ANALYZING AD {advNo} ===")
    
    target_spot = ensure_integer(ad.get('target_spot', 0))
    asset_type = ad.get('asset_type')
    current_priceFloatingRatio = ensure_numeric(ad.get('floating_ratio', 0))
    surplusAmount = ensure_numeric(ad.get('surplused_amount', 0))
    fiat = ad.get('fiat')
    transAmount = ensure_numeric(ad.get('transAmount', 0))
    minTransAmount = ensure_numeric(ad.get('minTransAmount', 0))
    
    logger.info(f"  Ad details: target_spot={target_spot}, asset={asset_type}, fiat={fiat}")
    logger.info(f"  Amounts: transAmount={transAmount}, minTransAmount={minTransAmount}")
    logger.info(f"  Current ratio: {current_priceFloatingRatio}")
        
    try:
        our_ad_data = next((item for item in ads_data if item['adv']['advNo'] == advNo), None)
        if our_ad_data:
            our_current_price = float(our_ad_data['adv']['price'])
            logger.info(f"  Found our ad in data: price={our_current_price}")
        else:
            logger.info(f"  Ad {advNo} not found in ads_data, checking if online...")
            if not await is_ad_online(binance_api, KEY, SECRET, advNo):
                logger.info(f"  Ad {advNo} is offline, skipping")
                return
            our_ad_detail = await binance_api.get_ad_detail(KEY, SECRET, advNo)
            if our_ad_detail.get('code') == '000000' and 'data' in our_ad_detail:
                our_ad_data = our_ad_detail['data']
                if our_ad_data['advNo'] == advNo:
                    our_current_price = float(our_ad_data['price'])
                    logger.info(f"  Retrieved our ad details: price={our_current_price}")
                else:
                    logger.error(f"  No matching ad data found for ad number {advNo}.")
                    return

        base_price = compute_base_price(our_current_price, current_priceFloatingRatio)

        ask = reference_prices.get("lowest_ask")
        bid = reference_prices.get("highest_bid")
        logger.info(f"  Reference prices: ask={ask}, bid={bid}")

        if ask is not None and bid is not None and asset_type == 'USDT' and fiat != 'USD':
            global BUY_PRICE_THRESHOLD
            global SELL_PRICE_THRESHOLD

            previous_sell_price_threshold = SELL_PRICE_THRESHOLD
            previous_buy_price_threshold = BUY_PRICE_THRESHOLD
            min_diff = 0.0005
            
            logger.info(f"  Adjusting thresholds based on reference prices")
            
            if base_price < bid:
                # Use a slightly more flexible threshold when our base price is below bid
                new_sell_price_threshold = max(0.9960, round(((bid * 0.9935) / base_price), 4))
            else:
                new_sell_price_threshold = round(((bid * 0.9935) / base_price), 4)
            
            if base_price > ask:
                new_buy_price_threshold = 1.0110
            else:
                price_diff = round((ask / base_price), 4)
                if price_diff > 1.010:
                    new_buy_price_threshold = price_diff
                else:
                    new_buy_price_threshold = 1.0110
            
            current_diff = 0

            if is_buy:
                current_diff = abs(new_buy_price_threshold - previous_buy_price_threshold)
                if current_diff > min_diff:
                    BUY_PRICE_THRESHOLD = new_buy_price_threshold
                    logger.info(f"  Updated BUY_PRICE_THRESHOLD: {previous_buy_price_threshold} -> {BUY_PRICE_THRESHOLD}")
            else:
                current_diff = abs(new_sell_price_threshold - previous_sell_price_threshold)
                if current_diff > min_diff:
                    SELL_PRICE_THRESHOLD = new_sell_price_threshold
                    logger.info(f"  Updated SELL_PRICE_THRESHOLD: {previous_sell_price_threshold} -> {SELL_PRICE_THRESHOLD}")

        custom_price_threshold = determine_price_threshold(ad['payTypes'], is_buy)
        
        # Add validation for reasonable thresholds
        if custom_price_threshold > 10:  # Threshold should be close to 1.0, not 18+
            logger.error(f"UNREASONABLE price threshold {custom_price_threshold} for ad {advNo}")
            logger.error(f"Constants: BUY={BUY_PRICE_THRESHOLD}, SELL={SELL_PRICE_THRESHOLD}, THRESHOLD_2={PRICE_THRESHOLD_2}")
            logger.error(f"payTypes: {ad['payTypes']}")
            return
        
        filtered_ads = filter_ads(ads_data, base_price, all_ads, transAmount, custom_price_threshold, minTransAmount, is_buy)
        
        if not filtered_ads:
            logger.warning(f"No filtered ads for {advNo} - trying relaxed criteria")
            
            # Try with more relaxed price threshold
            relaxed_threshold = BUY_PRICE_THRESHOLD * 0.8 if is_buy else SELL_PRICE_THRESHOLD * 1.2
            logger.info(f"  Trying relaxed threshold: {relaxed_threshold}")
            
            filtered_ads = filter_ads(ads_data, base_price, all_ads, transAmount, relaxed_threshold, minTransAmount, is_buy)
            
            if not filtered_ads:
                logger.info(f"  Still no ads with relaxed criteria, trying retry fetch...")
                ads_data = await retry_fetch_ads(binance_api, KEY, SECRET, ad, is_buy)
                if ads_data:
                    filtered_ads = filter_ads(ads_data, base_price, all_ads, transAmount, relaxed_threshold, minTransAmount, is_buy)
                
                if not filtered_ads:
                    logger.warning(f"FINAL: Still no filtered ads for {advNo} after all attempts")
                    return

        adjusted_target_spot = check_if_ads_avail(filtered_ads, target_spot)
        competitor_ad = filtered_ads[adjusted_target_spot - 1]
        competitor_price = float(competitor_ad['adv']['price'])
        competitor_ratio = round(((competitor_price / base_price) * 100), 2)

        logger.info(f"  Competitor analysis:")
        logger.info(f"    Our price: {our_current_price}")
        logger.info(f"    Competitor price: {competitor_price}")
        logger.info(f"    Competitor ratio: {competitor_ratio}")

        if (our_current_price >= competitor_price and is_buy) or (our_current_price <= competitor_price and not is_buy):
            new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT if is_buy else competitor_ratio + RATIO_ADJUSTMENT
            logger.info(f"  Price comparison triggered update: {new_ratio_unbounded}")
        else:
            diff_ratio = competitor_ratio - current_priceFloatingRatio if is_buy else current_priceFloatingRatio - competitor_ratio
            logger.info(f"  Diff ratio: {diff_ratio} (threshold: {DIFF_THRESHOLD})")
            if diff_ratio > DIFF_THRESHOLD:
                new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT if is_buy else competitor_ratio + RATIO_ADJUSTMENT
                logger.info(f"  Diff ratio triggered update: {new_ratio_unbounded}")
            else:
                logger.info(f"  No update needed (diff ratio {diff_ratio} <= {DIFF_THRESHOLD})")
                return
        
        new_ratio = adjust_ratio(new_ratio_unbounded, is_buy)
        new_diff = abs(new_ratio - current_priceFloatingRatio)
        
        if new_ratio == current_priceFloatingRatio and new_diff < 0.001:
            logger.info(f"  No change needed: ratio stays at {new_ratio}")
            return
        else:
            logger.info(f"UPDATING Ad {advNo}: ratio {current_priceFloatingRatio} -> {new_ratio}")
            await binance_api.update_ad(KEY, SECRET, advNo, new_ratio)

            if batch_updates is not None:
                batch_updates.append({
                    'target_spot': target_spot,
                    'advNo': advNo,
                    'asset_type': asset_type,
                    'floating_ratio': new_ratio,
                    'price': our_current_price,
                    'surplusAmount': surplusAmount,
                    'account': ad['account'],
                    'fiat': fiat,
                    'transAmount': transAmount,
                    'minTransAmount': minTransAmount
                })
            if shared_data_updates is not None:
                shared_data_updates.append({
                    'advNo': advNo,
                    'target_spot': target_spot,
                    'asset_type': asset_type,
                    'floating_ratio': new_ratio,
                    'price': our_current_price,
                    'surplused_amount': surplusAmount,
                    'account': ad['account'],
                    'fiat': fiat,
                    'transAmount': transAmount,
                    'minTransAmount': minTransAmount,
                    'payTypes': ad.get('payTypes'),
                    'Group': ad.get('Group'),
                    'trade_type': ad.get('trade_type')
                })

    except Exception as e:
        logger.error(f"An error occurred while analyzing and updating ad {advNo}: {e}")
        traceback.print_exc()

async def main_loop(binance_api, is_buy=True, batch_updates=None, shared_data_updates=None):
    trade_type = 'BUY' if is_buy else 'SELL'
    logger.info(f"=== STARTING MAIN LOOP FOR {trade_type} ADS ===")
    
    all_ads = await SharedData.fetch_all_ads(trade_type)
        
    if not all_ads:
        logger.warning(f"No {trade_type} ads found in SharedData")
        return
    
    logger.info(f"Found {len(all_ads)} {trade_type} ads")
    
    grouped_ads = {}
    tasks = []
    for ad in all_ads:
        group_key = ad['Group']
        grouped_ads.setdefault(group_key, []).append(ad)
    
    logger.info(f"Grouped into {len(grouped_ads)} groups")
    
    for group_key, ads_group in grouped_ads.items():
        logger.info(f"Processing group {group_key} with {len(ads_group)} ads")
        tasks.append(process_ads(ads_group, binance_api, all_ads, is_buy, batch_updates, shared_data_updates))
    
    if tasks:
        await asyncio.gather(*tasks)

async def process_ads(ads_group, binance_api, all_ads, is_buy=True, batch_updates=None, shared_data_updates=None):
    if not ads_group:
        logger.error("No ads to process.")
        return
    
    logger.info(f"=== PROCESSING {len(ads_group)} ADS ===")
    
    tasks = []
    for ad in ads_group:
        account = ad['account']
        KEY = credentials_dict[account]['KEY']
        SECRET = credentials_dict[account]['SECRET']
        payTypes_list = ad['payTypes'] if ad['payTypes'] is not None else []

        logger.info(f"Processing ad {ad['advNo']} for account {account}")

        transAmount = ensure_numeric(ad['transAmount'])        
        ads_data = await binance_api.fetch_ads_search(
            KEY, SECRET,
            'BUY' if is_buy else 'SELL',
            ad['asset_type'], ad['fiat'],
            transAmount, payTypes_list, page=1
        )
        if isinstance(ads_data, str):
            logger.error(f"Received unexpected string response: {ads_data}")
            continue

        if ads_data is None or ads_data.get('code') != '000000' or 'data' not in ads_data:
            logger.error(f"Invalid ads_data response: {ads_data}")
            continue

        current_ads_data = ads_data['data']
        if not isinstance(current_ads_data, list):
            logger.error(f'Current ads data is not a list: {current_ads_data}. API response: {ads_data}')
            continue
        if not current_ads_data:
            logger.info(f"Empty ads data for account {account}")
            continue

        logger.info(f"Retrieved {len(current_ads_data)} ads for processing")

        tasks.append(analyze_and_update_ads(ad, binance_api, KEY, SECRET, current_ads_data, all_ads, is_buy, batch_updates, shared_data_updates))
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        logger.info("No tasks created for processing ads")

async def batch_update(updates, update_function, description=""):
    try:
        if updates:
            logger.info(f"Performing {len(updates)} {description} updates")
            for update in updates:
                await update_function(**update)
        else:
            logger.info(f"No updates to perform for {description}")
    except Exception as e:
        logger.error(f"An error occurred while performing batch {description} update: {e}")
        traceback.print_exc()

async def validate_update_data(updates, update_type="database"):
    """Validate data before batch updates"""
    validation_errors = []
    
    for i, update in enumerate(updates):
        if 'advNo' not in update:
            validation_errors.append(f"Update {i}: Missing advNo")
            continue
            
        advNo = update['advNo']
        
        if 'target_spot' in update and not isinstance(update['target_spot'], (int, type(None))):
            validation_errors.append(f"Update {advNo}: target_spot should be integer, got {type(update['target_spot'])}")
        
        if 'transAmount' in update and not isinstance(update['transAmount'], (int, float, type(None))):
            validation_errors.append(f"Update {advNo}: transAmount should be numeric, got {type(update['transAmount'])}")
        
        if 'minTransAmount' in update and not isinstance(update['minTransAmount'], (int, float, type(None))):
            validation_errors.append(f"Update {advNo}: minTransAmount should be numeric, got {type(update['minTransAmount'])}")
    
    if validation_errors:
        logger.warning(f"Validation errors found in {update_type} updates:")
        for error in validation_errors:
            logger.warning(f"  - {error}")
        return False
    
    return True

async def update_ads_main(binance_api):
    logger.info("=== STARTING UPDATE ADS MAIN LOOP ===")
    
    while True:
        batch_updates = []
        shared_data_updates = []
        tasks = []
        tasks.append(asyncio.create_task(main_loop(binance_api, is_buy=True, batch_updates=batch_updates, shared_data_updates=shared_data_updates)))
        tasks.append(asyncio.create_task(main_loop(binance_api, is_buy=False, batch_updates=batch_updates, shared_data_updates=shared_data_updates)))
        await asyncio.gather(*tasks)

        logger.info(f"Update cycle completed. Database updates: {len(batch_updates)}, Shared data updates: {len(shared_data_updates)}")
        
        if batch_updates and await validate_update_data(batch_updates, "database"):
            await batch_update(batch_updates, update_ad_in_database, "ads in the database")
        
        if shared_data_updates and await validate_update_data(shared_data_updates, "shared data"):
            await batch_update(shared_data_updates, SharedData.update_ad, "shared data for ads")

        logger.info("Sleeping for 1 second before next cycle...")
        await asyncio.sleep(1)

async def main():
    logger.info("=== BINANCE UPDATE ADS STARTING ===")
    validate_constants()
    
    try:
        binance_api = await BinanceAPI.get_instance()
        await populate_ads_with_details(binance_api)
        tasks = []
        tasks.append(asyncio.create_task(start_bitso_order_book()))
        tasks.append(asyncio.create_task(update_ads_main(binance_api)))
        await asyncio.gather(*tasks)
    except Exception as e:
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"An error occurred: {tb_str}")
    finally:
        await binance_api.close_session()
        await SharedSession.close_session()

if __name__ == "__main__":
    asyncio.run(main())