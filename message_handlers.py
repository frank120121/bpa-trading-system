from common_utils import get_adjusted_timestamp
from lang_utils import get_message_by_language
import json
import logging
from database import update_reply_count, get_reply_count

logging.basicConfig(level=logging.INFO)

def check_order_details(order_details):
    if order_details is None:
        logging.warning("order_details is None.")
        return False
    return True

def determine_language(order_details):
    fiat_unit = order_details.get('fiat_unit', 'Unknown currency')
    logging.debug(f"Determining language based on fiat_unit: {fiat_unit}")
    lang_mappings = {'MXN': 'es', 'USD': 'en'}
    return lang_mappings.get(fiat_unit, 'en')

def generic_reply(ws, uuid, order_no, order_details, conn, status_code):
    logging.info(f"Replying for order status {status_code}")

    current_reply_count = get_reply_count(conn, order_no)

    if current_reply_count < 2:
        buyer_name = order_details.get('buyer_name', 'Unknown buyer')
        current_language = determine_language(order_details)
        messages_to_send = get_message_by_language(current_language, status_code, buyer_name)
        
        if messages_to_send is None:
            logging.error(f"No messages found for language: {current_language} and status_code: {status_code}")
            return
        
        for msg in messages_to_send:
            send_text_message(ws, msg, uuid, order_no)

        update_reply_count(conn, order_no)
    else:
        logging.info(f"Bot has already replied {current_reply_count} times to order {order_no} for this status. Ignoring.")


def send_text_message(ws, text, uuid, order_no):
    try:
        logging.info(f"Sending a message: {text}")
        timestamp = get_adjusted_timestamp()
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
        ws.send(json.dumps(message))
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def handle_system_notifications(ws, msg_json, order_no, order_details, conn):
    try:
        if not check_order_details(order_details):
            return

        msg_type = order_details.get('order_status', "")
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
        logging.info(f"Function name obtained: {func_name}")

        func = REPLY_FUNCTIONS.get(func_name)

        if func:
            logging.info(f"Handling system notification of type: {msg_type}")
            func(ws, uuid, order_no, order_details, conn)
        else:
            logging.warning(f"Unhandled system notification type: {msg_type}")

    except Exception as e:
        logging.error(f"Exception occurred: {e}")

# Map function names to reply functions, the "conn" argument is passed implicitly
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


def handle_text_message(ws, msg_json, order_no, order_details, conn):
    uuid = msg_json.get('uuid')
    if not check_order_details(order_details):
        return
    
    msg_content = msg_json.get('content', '').lower()
    
    # Check if order_details is available
    if order_details:
        status = order_details.get('order_status')
        generic_reply(ws, uuid, order_no, order_details, conn, status)
        return  # Exit the function after potentially sending the auto-reply

    # Continue with existing logic if orderStatus is not in STATUS_MESSAGES
    func = REPLY_FUNCTIONS.get(msg_content)
    if func:
        func(ws, msg_json, uuid, order_no, order_details, conn)

def handle_image_message(ws, msg_json, order_no, order_details):
    uuid = msg_json.get('uuid')
    if not check_order_details(order_details):
        return

    current_language = determine_language(order_details)
    
    if current_language == 'es':
        send_text_message(ws, "Enseguida Verifico.", uuid, order_no)
    elif current_language == 'en':
        send_text_message(ws, "One moment, I'll verify.", uuid, order_no)
    else:
        send_text_message(ws, "One moment, I'll verify.", uuid, order_no)  # Default to English
