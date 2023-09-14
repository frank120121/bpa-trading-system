import json
import logging
from message_handlers import handle_text_message, handle_system_notifications, handle_image_message
from database import create_connection, insert_or_update_order, get_order_details, order_exists, update_status_from_system_type, reset_reply_count
from utils import fetch_order_details

logging.basicConfig(level=logging.DEBUG)

def on_message(ws, message, KEY, SECRET):
    try:
        msg_json = json.loads(message)
        msg_type = msg_json.get('type', '')
        is_self = msg_json.get('self', False)
        order_no = msg_json.get('orderNo', '')

        if is_self:
            logging.debug("Message is from self, ignoring.")
            return

        conn = create_connection("crypto_bot.db")
        if conn:
            logging.info("Database connection successful.")
            if not order_exists(conn, order_no):
                logging.info(f"Order {order_no} does not exist in the database. Fetching details from API.")
                order_details = fetch_order_details(order_no, KEY, SECRET)
                
                if order_details:
                    insert_or_update_order(conn, order_details)
                    conn.commit()
                    logging.info(f"Order {order_no} successfully inserted.")
                else:
                    logging.warning("Failed to fetch order details.")
            else:
                order_details = get_order_details(conn, order_no)
                logging.info(f"Order {order_no} exists in the database. Fetched details from db.")
                
            if msg_type == 'system':
                content = json.loads(msg_json.get('content', '{}'))
                system_type = content.get('type', '')
                
                update_status_from_system_type(conn, order_no, system_type)
                reset_reply_count(conn, order_no)
                
                order_details = get_order_details(conn, order_no)
                
                handle_system_notifications(ws, msg_json, order_no, order_details, conn)

            elif msg_type == 'text':
                IGNORE_REPLIES = {'okay', 'ok', 'sure', 'claro', 'got it', 'entendido', 'gracias', 'Enterado', 'okay', 'muy bien', 'si', 'perfecto', 'como diga', 'yes', 'ya entendi', 'Hola ya quedo gracias', 'Le agradezco', 'Lista la transferencia', 'Ok, un momento', 'un momento' }
                
                msg_content = msg_json.get('content', '').lower()

                if msg_content in IGNORE_REPLIES:
                    logging.debug(f"Ignoring message: {msg_content}")
                    return
                else:
                    logging.info(f"Handling 'text' message for order {order_no}.")
                    handle_text_message(ws, msg_json, order_no, order_details, conn)
            
            elif msg_type == 'image':
                logging.info(f"Handling 'image' message for order {order_no}.")
                handle_image_message(ws, msg_json, order_no, order_details)
            
            conn.close()
        else:
            logging.error("Failed to connect to the database.")
    except Exception as e:
        logging.exception(f"An exception occurred: {e}")

def on_close(ws, close_status_code, close_msg, KEY, SECRET):
    logging.info(f"### closed ### ")

