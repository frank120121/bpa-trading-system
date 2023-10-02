from binance_messages import send_text_message, present_menu_based_on_status, handle_menu_response
from lang_utils import get_message_by_language, determine_language, get_default_reply
import json
from database import update_reply_count, get_reply_count, reset_reply_count
from binance_orders import binance_buy_order
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)
async def check_order_details(order_details):
    if order_details is None:
        logger.warning("order_details is None.")
        return False
    return True
async def generic_reply(ws, uuid, order_no, order_details, conn, status_code):
    logger.info("Inside generic_reply function.")
    current_reply_count = await get_reply_count(conn, order_no)
    logger.info(f"Current reply count: {current_reply_count}")
    if current_reply_count < 2:
        buyer_name = order_details.get('buyer_name')
        current_language = determine_language(order_details)
        logger.info(f"Buyer Name: {buyer_name}, Current Language: {current_language}")
        messages_to_send = await get_message_by_language(current_language, status_code, buyer_name)
        logger.info(f"Messages to send: {messages_to_send}")
        if messages_to_send is None:
            logger.warning(f"No messages found for language: {current_language} and status_code: {status_code}")
            return
        for msg in messages_to_send:
            await send_text_message(ws, msg, uuid, order_no)
            logger.info(f"Sent message: {msg}")
        await update_reply_count(conn, order_no)
        logger.info("Updated reply count.")
    else:
        logger.info("Reply count is 2 or more. Exiting function.")
        return

async def handle_system_notifications(ws, msg_json, order_no, order_details, conn):
    content = msg_json.get('content', '')
    content_dict = json.loads(content)
    system_type = content_dict.get('type', '')

    if system_type == "seller_completed":
        asset_type =  content_dict.get('symbol', '')
        if asset_type == 'BTC':
            await binance_buy_order(asset_type)

    logger.debug("handling notification")
    await reset_reply_count(conn, order_no)
    try:
        if not await check_order_details(order_details):
            return
        msg_type = order_details.get('order_status')
        if msg_type is not None:
            uuid = msg_json.get('UUID', '')
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
            func_name = SYSTEM_REPLY_FUNCTIONS.get(msg_type)
            func = REPLY_FUNCTIONS.get(func_name)
            if func:
                await func(ws, uuid, order_no, order_details, conn)
            else:
                logger.warning(f"Unhandled system notification type: {msg_type}")
        else:
            logger.warning("Empty or missing order_status in order_details.")
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
REPLY_FUNCTIONS = {
    'hello': lambda ws, uuid, order_no, order_details, conn: send_text_message(ws, "Hello! How can I assist you?", uuid, order_no),
    'wait': lambda ws, uuid, order_no, order_details, conn: send_text_message(ws, "Sure, I'll wait bruh.", uuid, order_no),
    'request_proof': lambda ws, uuid, order_no, order_details, conn: (
        send_text_message(
            ws,
            "Por favor enviar comprobante de pago(requerido)." if determine_language(order_details) == 'es' else "Please send proof of payment(required).",
            uuid,
            order_no
        )
    ),
    'new_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 1),
    'sell_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 2),
    'completed_order': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 4),
    'customer_appealed':  lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 5),
    'seller_cancelled': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 6),
    'canceled_by_system': lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 7),
    'we_apealed':  lambda ws, uuid, order_no, order_details, conn: generic_reply(ws, uuid, order_no, order_details, conn, 9),
}
async def handle_text_message(ws, msg_json, order_no, order_details, conn):
    uuid = msg_json.get('uuid')
    logger.info(f"UUID obtained from msg_json: {uuid}")
    if not await check_order_details(order_details):
        print("check_order_details returned False. Exiting function.")
        return
    msg_content = msg_json.get('content', '').lower()
    logger.info(f"Message content obtained from msg_json: {msg_content}")
    if msg_content in ['ayuda', 'help']:
        await present_menu_based_on_status(ws, order_details, uuid, order_no)
    elif msg_content.isdigit():
        await handle_menu_response(ws, int(msg_content), order_details, uuid, order_no)
    else:
        default_reply = get_default_reply(order_details)
        await send_text_message(ws, default_reply, uuid, order_no)

async def handle_image_message(ws, msg_json, order_no, order_details, conn):
    uuid = msg_json.get('uuid')
    if not await check_order_details(order_details):
        return
    current_language = determine_language(order_details)
    if current_language == 'es':
        await send_text_message(ws, "Enseguida Verifico.", uuid, order_no)
    elif current_language == 'en':
        await send_text_message(ws, "One moment, I'll verify.", uuid, order_no)
    else:
        await send_text_message(ws, "One moment, I'll verify.", uuid, order_no)
