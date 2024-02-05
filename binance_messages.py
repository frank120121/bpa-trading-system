from common_utils import get_server_timestamp
from lang_utils import get_response_for_menu_choice, is_valid_choice, get_invalid_choice_reply, determine_language, get_menu_for_order
from database import set_menu_presented
import json
import logging
logger = logging.getLogger(__name__)

async def send_text_message(ws, text, order_no):

    try:
        logger.debug(f"Sending a message: {text}")
        timestamp = await get_server_timestamp()
        uuid_prefix = "self_"
        message = {
            'type': 'text',
            'uuid': f"{uuid_prefix}{timestamp}",
            'orderNo': order_no,
            'content': text,
            'self': False,
            'clientType': 'web',
            'createTime': timestamp,
            'sendStatus': 4
        }
        await ws.send(json.dumps(message))

    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def present_menu_based_on_status(ws, order_details, order_no, conn):

    menu = await get_menu_for_order(order_details)
    msg = '\n'.join(menu)
    await send_text_message(ws, msg, order_no)
    await set_menu_presented(conn, order_no, True)

async def handle_menu_response(ws, choice, order_details, order_no):
    language = determine_language(order_details)
    order_status = order_details.get('order_status')
    buyer_name = order_details.get('buyer_name')
    if await is_valid_choice(language, order_status, choice):
        response = await get_response_for_menu_choice(language, order_status, choice, buyer_name)
    else:
        response = await get_invalid_choice_reply(order_details)

    await send_text_message(ws, response, order_no)
