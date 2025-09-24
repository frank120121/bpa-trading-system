# bpa/populate_database.py
import sys
import asyncio

from src.data.database.operations.ads_database import fetch_all_ads_from_database, update_ad_in_database
from src.utils.common_vars import ads_dict
from src.connectors.credentials import credentials_dict
from src.connectors.binance.api import BinanceAPI
from data.cache.share_data import SharedData, SharedSession
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Create lookup dictionaries with proper data type handling
advNo_to_target_spot = {ad['advNo']: ad['target_spot'] for _, ads in ads_dict.items() for ad in ads}
advNo_to_fiat = {ad['advNo']: ad['fiat'] for _, ads in ads_dict.items() for ad in ads}
advNo_to_transAmount = {ad['advNo']: ad['transAmount'] for _, ads in ads_dict.items() for ad in ads}
advNo_to_minTransAmount = {ad['advNo']: ad['minTransAmount'] for _, ads in ads_dict.items() for ad in ads}

def ensure_numeric(value, default=0):
    """Ensure value is numeric (for C2C API compatibility)"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            # Try to convert string to number
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

async def populate_ads_with_details(binance_api):
    try:
        ads_info = await fetch_all_ads_from_database()

        tasks = []
        for ad_info in ads_info:
            account = ad_info['account']
            KEY = credentials_dict[account]['KEY']
            SECRET = credentials_dict[account]['SECRET']
            tasks.append(update_ad_detail(account, binance_api, KEY, SECRET, ad_info))
        
        await asyncio.gather(*tasks)
        
        updated_ads_info = await fetch_all_ads_from_database()

        await populate_shared_data(updated_ads_info)
    finally:
        logger.info("All ads processed successfully.")

async def update_ad_detail(account, binance_api, KEY, SECRET, ad_info):
    try:
        advNo = ad_info['advNo']
        ad_details_response = await binance_api.get_ad_detail(KEY, SECRET, advNo)

        if ad_details_response and ad_details_response.get('data'):
            ad_details = ad_details_response['data']
            
            # Get values from lookup dictionaries and ensure proper data types
            target_spot = ensure_integer(advNo_to_target_spot.get(advNo, ad_info.get('target_spot', 0)))
            fiat = advNo_to_fiat.get(advNo, ad_info.get('fiat', 'MXN'))
            transAmount = ensure_numeric(advNo_to_transAmount.get(advNo, ad_info.get('transAmount', 0)))
            minTransAmount = ensure_numeric(advNo_to_minTransAmount.get(advNo, ad_info.get('minTransAmount', 0)))
            
            # Extract and validate data from Binance API response
            floating_ratio = ensure_numeric(ad_details.get('priceFloatingRatio'))
            price = ensure_numeric(ad_details.get('price'))
            surplus_amount = ensure_numeric(ad_details.get('surplused_amount', 0))

            if 'priceFloatingRatio' in ad_details and 'price' in ad_details:
                await update_ad_in_database(
                    target_spot=target_spot,              # integer
                    advNo=advNo,                          # string
                    asset_type=ad_info['asset_type'],     # string
                    floating_ratio=floating_ratio,        # float
                    price=price,                          # float
                    surplusAmount=surplus_amount,         # float
                    account=ad_info['account'],           # string
                    fiat=fiat,                           # string
                    transAmount=transAmount,             # float/int 
                    minTransAmount=minTransAmount        # float/int 
                )
                
                logger.debug(f"Successfully updated ad {advNo} with target_spot={target_spot}, transAmount={transAmount}, minTransAmount={minTransAmount}")
            else:
                logger.error(f"Missing required fields in ad details for advNo {advNo}: {ad_details}")
        else:
            logger.error(f"Failed to fetch ad details or missing 'data' for advNo {advNo}.")
    except Exception as e:
        logger.error(f"Error updating ad details for advNo {ad_info['advNo']}: {e}")
        # Log the full traceback for debugging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

async def populate_shared_data(ads_info):
    successful_additions = 0
    try:
        for ad_info in ads_info:
            advNo = ad_info['advNo']
            
            # Ensure data types are correct before adding to SharedData
            processed_ad_info = {
                'advNo': ad_info['advNo'],                                          # string
                'target_spot': ensure_integer(ad_info.get('target_spot', 0)),       # integer
                'asset_type': ad_info.get('asset_type', ''),                       # string
                'price': ensure_numeric(ad_info.get('price')),                     # float
                'floating_ratio': ensure_numeric(ad_info.get('floating_ratio')),   # float
                'last_updated': ad_info.get('last_updated'),                       # timestamp
                'account': ad_info.get('account', ''),                             # string
                'surplused_amount': ensure_numeric(ad_info.get('surplused_amount', 0)), # float
                'fiat': ad_info.get('fiat', 'MXN'),                               # string
                'transAmount': ensure_numeric(ad_info.get('transAmount', 0)),      # float/int (numeric)
                'payTypes': ad_info.get('payTypes'),                              # list or None
                'Group': ad_info.get('Group', ''),                                # string
                'trade_type': ad_info.get('trade_type', ''),                      # string
                'minTransAmount': ensure_numeric(ad_info.get('minTransAmount', 0)) # float/int (numeric)
            }
            
            success = await SharedData.set_ad(advNo, processed_ad_info)
            if success:
                successful_additions += 1
            else:
                logger.warning(f"Failed to set ad {advNo} in SharedData.")
        
        logger.info(f"Successfully added {successful_additions} ads to SharedData")
        
    except Exception as e:
        logger.error(f"Error in populate_shared_data: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    finally:
        logger.debug("Exiting populate_shared_data.")

async def validate_ads_data():
    """Validate that all ads data is in correct format for C2C API"""
    try:
        ads_info = await fetch_all_ads_from_database()
        validation_errors = []
        
        for ad_info in ads_info:
            advNo = ad_info['advNo']
            
            # Check data types
            if not isinstance(ad_info.get('target_spot'), (int, type(None))):
                validation_errors.append(f"Ad {advNo}: target_spot should be integer, got {type(ad_info.get('target_spot'))}")
            
            if not isinstance(ad_info.get('transAmount'), (int, float, type(None))):
                validation_errors.append(f"Ad {advNo}: transAmount should be numeric, got {type(ad_info.get('transAmount'))}")
            
            if not isinstance(ad_info.get('minTransAmount'), (int, float, type(None))):
                validation_errors.append(f"Ad {advNo}: minTransAmount should be numeric, got {type(ad_info.get('minTransAmount'))}")
        
        if validation_errors:
            logger.warning("Data validation errors found:")
            for error in validation_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("All ads data validated successfully for C2C API compatibility")
            
    except Exception as e:
        logger.error(f"Error during data validation: {e}")