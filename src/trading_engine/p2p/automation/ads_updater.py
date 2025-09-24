# bpa/binance_update_ads.py
"""
Automated Binance P2P Ad Pricing System

This module continuously monitors competitor ads and automatically adjusts
pricing ratios to maintain competitive positioning in the Binance P2P marketplace.

Key Features:
- Real-time competitor price monitoring
- Dynamic threshold adjustment based on market conditions
- Payment method specific pricing strategies
- Batch processing for optimal performance
"""

import asyncio
import traceback

from src.connectors.credentials import credentials_dict
from src.data.cache.share_data import SharedSession, SharedData
from src.data.database.operations.ads_database import update_ad_in_database
from src.connectors.binance.api import BinanceAPI
from src.data.cache.bitso_cache import reference_prices
from src.data.database.populate_database import populate_ads_with_details
from src.connectors.bitso.orderbook import start_bitso_order_book
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

# Pricing Configuration
SELL_PRICE_THRESHOLD = 0.9960
BUY_PRICE_THRESHOLD = 1.0128  
PRICE_THRESHOLD_2 = 1.0548  # For special payment methods[Wise, Zelle, Skrill]
OXXO_PRICE_THRESHOLD = 1.0420  # For OXXO payments
MIN_RATIO = 90.00
MAX_RATIO = 110.00
RATIO_ADJUSTMENT = 0.05
DIFF_THRESHOLD = 0.15

def ensure_numeric(value, default=0.0):
    """Convert value to numeric, handling various input types"""
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
    """Convert value to integer"""
    if isinstance(value, int):
        return value
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default

def compute_base_price(price: float, floating_ratio: float) -> float:
    """Calculate base price from current price and floating ratio"""
    return round(price / (floating_ratio / 100), 2)

def determine_price_threshold(payTypes, is_buy=True):
    """Determine appropriate price threshold based on payment method"""
    if payTypes is not None:
        payTypes_to_check = payTypes if isinstance(payTypes, list) else [payTypes]
        
        # OXXO has specific threshold
        if 'OXXO' in payTypes_to_check:
            return OXXO_PRICE_THRESHOLD if is_buy else SELL_PRICE_THRESHOLD
        
        # Other special payment methods
        special_payTypes = ['BANK', 'ZELLE', 'SkrillMoneybookers']
        if any(payType in payTypes_to_check for payType in special_payTypes):
            return PRICE_THRESHOLD_2 if is_buy else SELL_PRICE_THRESHOLD
    
    return BUY_PRICE_THRESHOLD if is_buy else SELL_PRICE_THRESHOLD

def filter_ads(ads_data, base_price, own_ads, trans_amount_threshold, price_threshold, minTransAmount, is_buy=True):
    """Filter competitor ads based on pricing and volume criteria"""
    own_adv_nos = [ad['advNo'] for ad in own_ads]
    
    filtered = []
    for ad in ads_data:
        adv_data = ad['adv']
        price = float(adv_data['price'])
        max_amount = float(adv_data['dynamicMaxSingleTransAmount'])
        min_amount = float(adv_data['minSingleTransAmount'])
        
        # Apply filtering criteria
        if (adv_data['advNo'] not in own_adv_nos and
            ((price > base_price * price_threshold) if is_buy else (price <= base_price * price_threshold)) and
            max_amount >= trans_amount_threshold and
            min_amount <= minTransAmount):
            filtered.append(ad)
    
    return filtered

def adjust_ratio(new_ratio_unbounded, is_buy):
    """Apply ratio bounds based on trading direction"""
    if is_buy:
        threshold = round(BUY_PRICE_THRESHOLD * 100, 2)
        return max(threshold, min(MAX_RATIO, round(new_ratio_unbounded, 2)))
    else:
        threshold = round(SELL_PRICE_THRESHOLD * 100, 2)
        return max(MIN_RATIO, min(threshold, round(new_ratio_unbounded, 2)))

def adjust_thresholds_for_market_conditions(base_price, asset_type, fiat, is_buy):
    """Dynamically adjust thresholds based on reference prices"""
    global BUY_PRICE_THRESHOLD, SELL_PRICE_THRESHOLD
    
    ask = reference_prices.get("lowest_ask")
    bid = reference_prices.get("highest_bid")
    
    if ask is None or bid is None or asset_type != 'USDT' or fiat == 'USD':
        return
    
    min_diff = 0.0005
    previous_sell_threshold = SELL_PRICE_THRESHOLD
    previous_buy_threshold = BUY_PRICE_THRESHOLD
    
    # Calculate new thresholds
    if base_price < bid:
        new_sell_threshold = max(0.9960, round((bid * 0.9935) / base_price, 4))
    else:
        new_sell_threshold = round((bid * 0.9935) / base_price, 4)
    
    if base_price > ask:
        new_buy_threshold = 1.0110
    else:
        price_diff = round(ask / base_price, 4)
        new_buy_threshold = price_diff if price_diff > 1.010 else 1.0110
    
    # Apply changes if significant
    if is_buy and abs(new_buy_threshold - previous_buy_threshold) > min_diff:
        BUY_PRICE_THRESHOLD = new_buy_threshold
    elif not is_buy and abs(new_sell_threshold - previous_sell_threshold) > min_diff:
        SELL_PRICE_THRESHOLD = new_sell_threshold

async def is_ad_online(binance_api, KEY, SECRET, advNo):
    """Check if an ad is currently online"""
    try:
        response = await binance_api.get_ad_detail(KEY, SECRET, advNo)
        if response and response.get('code') == '000000' and 'data' in response:
            return response['data'].get('advStatus') == 1
        return False
    except Exception as e:
        logger.error(f"Error checking ad status for {advNo}: {e}")
        return False

async def retry_fetch_ads(binance_api, KEY, SECRET, ad, is_buy, max_pages=10):
    """Retry fetching ads across multiple pages if not found initially"""
    advNo = ad.get('advNo')
    
    for page in range(1, max_pages + 1):
        transAmount = ensure_numeric(ad['transAmount'])
        
        ads_data = await binance_api.fetch_ads_search(
            KEY, SECRET, 
            'BUY' if is_buy else 'SELL',
            ad['asset_type'], 
            ad['fiat'],
            transAmount, 
            ad['payTypes'], 
            page
        )
        
        if (ads_data and ads_data.get('code') == '000000' and 
            'data' in ads_data and ads_data['data']):
            
            # Check if our ad is on this page
            if any(item['adv']['advNo'] == advNo for item in ads_data['data']):
                return ads_data['data']
    
    return []

async def analyze_and_update_ads(ad, binance_api, KEY, SECRET, ads_data, all_ads, is_buy, batch_updates, shared_data_updates):
    """Analyze competitor positioning and update ad pricing if needed"""
    if not ad:
        return

    advNo = ad.get('advNo')
    target_spot = ensure_integer(ad.get('target_spot', 0))
    asset_type = ad.get('asset_type')
    current_ratio = ensure_numeric(ad.get('floating_ratio', 0))
    fiat = ad.get('fiat')
    transAmount = ensure_numeric(ad.get('transAmount', 0))
    minTransAmount = ensure_numeric(ad.get('minTransAmount', 0))

    try:
        # Get our current ad data
        our_ad_data = next((item for item in ads_data if item['adv']['advNo'] == advNo), None)
        
        if not our_ad_data:
            if not await is_ad_online(binance_api, KEY, SECRET, advNo):
                return
                
            # Retrieve ad details if not in current data
            our_ad_detail = await binance_api.get_ad_detail(KEY, SECRET, advNo)
            if (our_ad_detail.get('code') == '000000' and 
                'data' in our_ad_detail and 
                our_ad_detail['data']['advNo'] == advNo):
                our_current_price = float(our_ad_detail['data']['price'])
            else:
                return
        else:
            our_current_price = float(our_ad_data['adv']['price'])

        base_price = compute_base_price(our_current_price, current_ratio)
        
        # Adjust thresholds based on market conditions
        adjust_thresholds_for_market_conditions(base_price, asset_type, fiat, is_buy)
        
        # Get appropriate threshold for payment method
        price_threshold = determine_price_threshold(ad['payTypes'], is_buy)
        
        # Filter competitor ads
        filtered_ads = filter_ads(ads_data, base_price, all_ads, transAmount, price_threshold, minTransAmount, is_buy)
        
        # Retry if no competitors found
        if not filtered_ads:
            ads_data = await retry_fetch_ads(binance_api, KEY, SECRET, ad, is_buy)
            if ads_data:
                filtered_ads = filter_ads(ads_data, base_price, all_ads, transAmount, price_threshold, minTransAmount, is_buy)
            
            if not filtered_ads:
                return

        # Analyze competitive position
        available_spots = min(len(filtered_ads), target_spot)
        competitor_ad = filtered_ads[available_spots - 1]
        competitor_price = float(competitor_ad['adv']['price'])
        competitor_ratio = round((competitor_price / base_price) * 100, 2)

        # Determine if update is needed
        should_update = False
        if (our_current_price >= competitor_price and is_buy) or (our_current_price <= competitor_price and not is_buy):
            new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT if is_buy else competitor_ratio + RATIO_ADJUSTMENT
            should_update = True
        else:
            diff_ratio = competitor_ratio - current_ratio if is_buy else current_ratio - competitor_ratio
            if diff_ratio > DIFF_THRESHOLD:
                new_ratio_unbounded = competitor_ratio - RATIO_ADJUSTMENT if is_buy else competitor_ratio + RATIO_ADJUSTMENT
                should_update = True

        if should_update:
            new_ratio = adjust_ratio(new_ratio_unbounded, is_buy)
            
            if abs(new_ratio - current_ratio) >= 0.001:
                await binance_api.update_ad(KEY, SECRET, advNo, new_ratio)
                
                # Queue database updates
                update_data = {
                    'target_spot': target_spot,
                    'advNo': advNo,
                    'asset_type': asset_type,
                    'floating_ratio': new_ratio,
                    'price': our_current_price,
                    'surplusAmount': ensure_numeric(ad.get('surplused_amount', 0)),
                    'account': ad['account'],
                    'fiat': fiat,
                    'transAmount': transAmount,
                    'minTransAmount': minTransAmount
                }
                batch_updates.append(update_data)
                
                # Queue shared data updates
                shared_update_data = update_data.copy()
                shared_update_data.update({
                    'surplused_amount': ensure_numeric(ad.get('surplused_amount', 0)),
                    'payTypes': ad.get('payTypes'),
                    'Group': ad.get('Group'),
                    'trade_type': ad.get('trade_type')
                })
                shared_data_updates.append(shared_update_data)

    except Exception as e:
        logger.error(f"Error analyzing ad {advNo}: {e}")
        traceback.print_exc()

async def process_ads_group(ads_group, binance_api, all_ads, is_buy, batch_updates, shared_data_updates):
    """Process a group of ads with the same trading parameters"""
    if not ads_group:
        return

    tasks = []
    for ad in ads_group:
        account = ad['account']
        KEY = credentials_dict[account]['KEY']
        SECRET = credentials_dict[account]['SECRET']
        payTypes_list = ad['payTypes'] if ad['payTypes'] is not None else []
        transAmount = ensure_numeric(ad['transAmount'])
        
        # Fetch current market data
        ads_data = await binance_api.fetch_ads_search(
            KEY, SECRET,
            'BUY' if is_buy else 'SELL',
            ad['asset_type'], 
            ad['fiat'],
            transAmount, 
            payTypes_list, 
            page=1
        )
        
        # Validate response
        if (isinstance(ads_data, str) or 
            not ads_data or 
            ads_data.get('code') != '000000' or 
            'data' not in ads_data or
            not isinstance(ads_data['data'], list)):
            continue

        tasks.append(analyze_and_update_ads(
            ad, binance_api, KEY, SECRET, ads_data['data'], 
            all_ads, is_buy, batch_updates, shared_data_updates
        ))
    
    if tasks:
        await asyncio.gather(*tasks)

async def main_loop(binance_api, is_buy, batch_updates, shared_data_updates):
    """Main processing loop for buy or sell ads"""
    trade_type = 'BUY' if is_buy else 'SELL'
    all_ads = await SharedData.fetch_all_ads(trade_type)
    
    if not all_ads:
        return
    
    # Group ads by common parameters for efficient processing
    grouped_ads = {}
    for ad in all_ads:
        group_key = ad['Group']
        grouped_ads.setdefault(group_key, []).append(ad)
    
    # Process each group concurrently
    tasks = [
        process_ads_group(ads_group, binance_api, all_ads, is_buy, batch_updates, shared_data_updates)
        for ads_group in grouped_ads.values()
    ]
    
    if tasks:
        await asyncio.gather(*tasks)

async def batch_update(updates, update_function):
    """Execute batch updates with error handling"""
    if not updates:
        return
    
    try:
        for update in updates:
            await update_function(**update)
    except Exception as e:
        logger.error(f"Batch update error: {e}")
        traceback.print_exc()

async def update_ads_main(binance_api):
    """Main update cycle - processes both buy and sell ads"""
    while True:
        batch_updates = []
        shared_data_updates = []
        
        # Process both buy and sell ads concurrently
        tasks = [
            asyncio.create_task(main_loop(binance_api, True, batch_updates, shared_data_updates)),
            asyncio.create_task(main_loop(binance_api, False, batch_updates, shared_data_updates))
        ]
        await asyncio.gather(*tasks)
        
        # Execute batch updates
        await batch_update(batch_updates, update_ad_in_database)
        await batch_update(shared_data_updates, SharedData.update_ad)
        
        await asyncio.sleep(1)

async def main():
    """Application entry point"""
    try:
        binance_api = await BinanceAPI.get_instance()
        await populate_ads_with_details(binance_api)
        
        # Start both market data feed and ad update system
        tasks = [
            asyncio.create_task(start_bitso_order_book()),
            asyncio.create_task(update_ads_main(binance_api))
        ]
        await asyncio.gather(*tasks)
        
    except Exception as e:
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"Application error: {tb_str}")
    finally:
        await binance_api.close_session()
        await SharedSession.close_session()

if __name__ == "__main__":
    asyncio.run(main())