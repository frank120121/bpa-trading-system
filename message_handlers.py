from lang_utils import get_message_by_language, determine_language, transaction_denied, get_default_reply, payment_concept, payment_warning
from common_utils import RateLimiter
from database import update_total_spent, get_kyc_status, get_anti_fraud_stage, is_menu_presented
from binance_bank_deposit import get_payment_details, log_deposit
from binance_messages import send_text_message, present_menu_based_on_status, handle_menu_response
from binance_orders import binance_buy_order
from binance_anti_fraud import handle_anti_fraud
from binance_blacklist import add_to_blacklist
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
        bank_account_number = order_details.get('account_number')
        amount_deposited = order_details.get('total_price')
        await log_deposit(conn, bank_account_number, amount_deposited)

    elif order_status == 1:
        seller_name = order_details.get('seller_name')
        buyer_name = order_details.get('buyer_name')
        last_four_digits = order_no[-4:]
        logger.info(f"Seller Name: {seller_name}.")
        logger.info(f"Last four: {last_four_digits}.")
        country = await fetch_ip(last_four_digits, seller_name)
        
        if country and country != "MX":
            logger.info("Transaction cannot take place. Seller is not from Mexico.")
            await send_text_message(ws, transaction_denied, order_no)
            await add_to_blacklist(conn, buyer_name)
            return 
        
        kyc_status = await get_kyc_status(conn, buyer_name)

        if kyc_status == 0:
            anti_fraud_stage = await get_anti_fraud_stage(conn, buyer_name)
            await handle_anti_fraud(buyer_name, seller_name, conn, anti_fraud_stage, "start_pro", order_no, ws)
        else:
            payment_details = await get_payment_details(conn, order_no)
            await send_text_message(ws, payment_warning, order_no)
            await send_text_message(ws, payment_details, order_no)
            await send_text_message(ws, payment_concept, order_no)
    else:
        await generic_reply(ws, order_no, order_details, order_status)
        response = await get_default_reply(order_details)
        await send_text_message(ws, response, order_no)

async def handle_text_message(ws, content, order_no, order_details, conn):
    if not await check_order_details(order_details):
        print("check_order_details returned False. Exiting function.")
        return

    order_status = order_details.get('order_status')

    if order_status not in [1, 2]:
        logger.debug("Order not in 1 or 2")
        return

    buyer_name = order_details.get('buyer_name')
    kyc_status = await get_kyc_status(conn, buyer_name)
    anti_fraud_stage = await get_anti_fraud_stage(conn, buyer_name)

    if kyc_status == 0 or anti_fraud_stage < 3:
        await handle_anti_fraud(buyer_name, order_details.get('seller_name'), conn, anti_fraud_stage, content, order_no, ws)
    else:
        logger.debug(f"Handling TEXT: {content}")

        if not await is_menu_presented(conn, order_no):
            if content in ['ayuda', 'help']:
                await present_menu_based_on_status(ws, order_details, order_no, conn)

        if content.isdigit():
            await handle_menu_response(ws, int(content), order_details, order_no)

async def handle_image_message(ws, order_no, order_details):
    if not await check_order_details(order_details):
        return
    logger.debug("Handling IMAGE")
    order_status = 100
    await generic_reply(ws, order_no, order_details, order_status)
