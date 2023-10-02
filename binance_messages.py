from common_utils import get_server_time
from lang_utils import get_response_for_menu_choice, is_valid_choice, get_invalid_choice_reply, determine_language, get_menu_for_order
import json
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

async def send_text_message(ws, text, uuid, order_no):
    try:
        logger.info(f"Sending a message: {text}")
        timestamp = await get_server_time()
        message = {
            'type': 'text',
            'uuid': uuid,
            'orderNo': order_no,
            'content': text,
            'self': True,
            'clientType': 'web',
            'createTime': timestamp,
            'sendStatus': 0
        }
        await ws.send(json.dumps(message))
    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def present_menu_based_on_status(ws, order_details, uuid, order_no):
    menu = get_menu_for_order(order_details)
    msg = '\n'.join(menu)
    await send_text_message(ws, msg, uuid, order_no)

async def handle_menu_response(ws, choice, order_details, uuid, order_no):
    language = determine_language(order_details)
    order_status = order_details.get('order_status')
    buyer_name = order_details.get('buyer_name')
    if is_valid_choice(language, order_status, choice):
        response = get_response_for_menu_choice(language, order_status, choice, buyer_name)
    else:
        response = get_invalid_choice_reply(order_details)
    await send_text_message(ws, response, uuid, order_no)
