from binance_messages import send_text_message, present_menu_based_on_status, handle_menu_response
from lang_utils import get_message_by_language, determine_language, get_invalid_choice_reply, get_default_reply
from common_vars import ANTI_FRAUD_CHECKS
from binance_orders import binance_buy_order
from common_utils import RateLimiter
from database import update_total_spent, get_kyc_status, get_anti_fraud_stage, is_menu_presented, update_ignore_count
from binance_anti_fraud import AntiFraud
from verify_client_ip import fetch_ip
import logging
from logging_config import setup_logging
setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)
rate_limiter = RateLimiter(limit_period=10)

async def check_order_details(order_details):
    if order_details is None:
        logger.warning("order_details is None.")
        return False
    return True
async def generic_reply(ws, order_no, order_details, status_code):
    buyer_name = order_details.get('buyer_name')
    current_language = determine_language(order_details)
    messages_to_send = await get_message_by_language(current_language, status_code, buyer_name)
    if messages_to_send is None:
        logger.warning(f"No messages found for language: {current_language} and status_code: {status_code}")
        return
    for msg in messages_to_send:
        await send_text_message(ws, msg, order_no)

async def handle_system_notifications(ws, order_no, order_details, conn, order_status):
    if not await check_order_details(order_details):
        return
    logger.debug(f'Order status: {order_status}')
    if order_status == 4:
        logger.debug("Inside if 4 order status")
        asset_type = order_details.get('asset')
        logger.debug(asset_type)
        if asset_type == 'BTC':
            await binance_buy_order(asset_type)
        await update_total_spent(conn, order_no)
        await generic_reply(ws, order_no, order_details, order_status)

    # last_four_digits = order_no[-4:]
    # country = await fetch_ip(last_four_digits)
    # if country and country != "MX":
    #     logger.info("Not from valid country")
    #     return



    elif order_status == 10:
        buyer_name = order_details.get('buyer_name')
        kyc_status = await get_kyc_status(conn, buyer_name)
        if kyc_status != 0:
            seller_name = order_details.get('seller_name')
            anti_fraud_instance = AntiFraud(buyer_name, seller_name, "Your Bank Name", "Your Account Number", conn)
            ANTI_FRAUD_CHECKS[order_no] = anti_fraud_instance
            initial_msg = "Initiating AntiFraud checks. Please answer the following questions..."
            await send_text_message(ws, initial_msg, order_no)
        else:
            await generic_reply(ws, order_no, order_details, order_status)
    else:
        await generic_reply(ws, order_no, order_details, order_status)
        response = await get_default_reply(order_details)
        await send_text_message(ws, response, order_no)

async def handle_antifraud_process(ws, content, order_no, order_details, conn, buyer_name):
    logger.debug(f"Handling TEXT: {content}")
    anti_fraud_instance = ANTI_FRAUD_CHECKS.get(order_no)

    if not anti_fraud_instance:
        # Create AntiFraud instance
        seller_name = order_details.get('seller_name')
        anti_fraud_stage = await get_anti_fraud_stage(conn, buyer_name)
        anti_fraud_instance = AntiFraud(buyer_name, seller_name, "Your Bank Name", "Your Account Number", conn, anti_fraud_stage)
        ANTI_FRAUD_CHECKS[order_no] = anti_fraud_instance

    # Handle the fraud check response
    response = anti_fraud_instance.handle_response(content)
    await send_text_message(ws, response, order_no)
    if "Los detalles para el pago son" in response:  # Last message of AntiFraud
        del ANTI_FRAUD_CHECKS[order_no]  # Remove instance since AntiFraud process is over

async def handle_text_message(ws, content, order_no, order_details, conn):
    if rate_limiter.is_limited(order_no):
        logger.warning(f"Rate limit triggered for order: {order_no}")
        return
    if not await check_order_details(order_details):
        print("check_order_details returned False. Exiting function.")
        return 
    order_status = order_details.get('order_status')
    if order_status not in [1, 2]:
        logger.debug("Order not in 1 or 2")
        return
    buyer_name = order_details.get('buyer_name')
    kyc_status = await get_kyc_status(conn, buyer_name)
    
    if order_status == 10 and kyc_status != 0:
        await handle_antifraud_process(ws, content, order_no, order_details, conn, buyer_name)
    else:
        
        logger.debug(f"Handling TEXT: {content}")
        if not await is_menu_presented(conn, order_no):
            if content in ['ayuda', 'help']:
                await present_menu_based_on_status(ws, order_details, order_no)
        if content.isdigit():
            await handle_menu_response(ws, int(content), order_details, order_no)

async def handle_image_message(ws, order_no, order_details):
    if not await check_order_details(order_details):
        return
    logger.debug("Handling IMAGE")
    order_status = 100
    await generic_reply(ws, order_no, order_details, order_status)
