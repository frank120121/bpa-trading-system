from binance_messages import send_text_message, present_menu_based_on_status, handle_menu_response
from lang_utils import get_message_by_language, determine_language
import json
from binance_orders import binance_buy_order
import logging
from logging_config import setup_logging
from common_utils import RateLimiter
setup_logging()
logger = logging.getLogger(__name__)
rate_limiter = RateLimiter(limit_period=10)
async def check_order_details(order_details):
    if order_details is None:
        logger.warning("order_details is None.")
        return False
    return True
async def generic_reply(ws, uuid, order_no, order_details, conn, status_code):
    buyer_name = order_details.get('buyer_name')
    current_language = determine_language(order_details)
    messages_to_send = await get_message_by_language(current_language, status_code, buyer_name)
    if messages_to_send is None:
        logger.warning(f"No messages found for language: {current_language} and status_code: {status_code}")
        return
    for msg in messages_to_send:
        await send_text_message(ws, msg, uuid, order_no)

SYSTEM_REPLY_FUNCTIONS = {
    1: 'new_order',
    2: 'request_proof',
    3: 'we_are_buying',
    4: 'completed_order',
    5: 'customer_appealed',
    6: 'seller_cancelled',
    7: 'canceled_by_system',
    8: 'we_payed',
    9: 'we_apealed'
}

async def handle_system_notifications(ws, msg_json, order_no, order_details, conn):
    content = msg_json.get('content', '')
    content_dict = json.loads(content)
    system_type = content_dict.get('type', '')
    if system_type == "seller_completed":
        asset_type = content_dict.get('symbol', '')
        if asset_type == 'BTC':
            await binance_buy_order(asset_type)
    if system_type == "buyer_merchant_trading":
        return
    if not await check_order_details(order_details):
        return

    msg_type = order_details.get('order_status')
    if msg_type:
        uuid = msg_json.get('UUID', '')
        func_name = SYSTEM_REPLY_FUNCTIONS.get(msg_type)
        func = REPLY_FUNCTIONS.get(func_name)
        if func:
            await func(ws, uuid, order_no, order_details, conn)
        else:
            logger.warning(f"Unhandled system notification type: {msg_type}")
    else:
        logger.warning("Empty or missing order_status in order_details.")

async def send_request_proof(ws, uuid, order_no, order_details, conn):
    language = determine_language(order_details)
    if language == 'es':
        message = "Por favor enviar comprobante de pago(requerido). Si necesita ayuda teclee la palabra ayuda"
    else:
        message = "Please send proof of payment(required)."
    await send_text_message(ws, message, uuid, order_no)

REPLY_FUNCTIONS = {
    'request_proof': send_request_proof,
    'new_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 1),
    'sell_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 2),
    'completed_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 4),
    'customer_appealed':  lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 5),
    'seller_cancelled': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 6),
    'canceled_by_system': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 7),
    'we_apealed':  lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 9),
}
async def handle_text_message(ws, msg_json, order_no, order_details, conn):
    if rate_limiter.is_limited(order_no):
        logger.warning(f"Rate limit triggered for order: {order_no}")
        return
    uuid = msg_json.get('uuid')
    if not await check_order_details(order_details):
        print("check_order_details returned False. Exiting function.")
        return
    msg_content = msg_json.get('content', '').lower()
    if msg_content in ['ayuda', 'help']:
        await present_menu_based_on_status(ws, order_details, uuid, order_no)
    elif msg_content.isdigit():
        await handle_menu_response(ws, int(msg_content), order_details, uuid, order_no)

async def handle_image_message(ws, msg_json, order_no, order_details, conn):
    uuid = msg_json.get('uuid')
    if not await check_order_details(order_details):
        return
    current_language = determine_language(order_details)
    response_message = await get_message_by_language(current_language, 100)
    if response_message:
        await send_text_message(ws, response_message[0], uuid, order_no)
    else:
        await send_text_message(ws, "One moment, I'll verify.", uuid, order_no)
