from message_handlers import handle_text_message, handle_system_notifications, handle_image_message
from database import insert_or_update_order, get_order_details, update_status_from_system_type
from TESTorder_details import fetch_order_details
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

class MerchantAccount:
    async def handle_message_by_type(self, ws,  KEY, SECRET, msg_json, order_no, conn, msg_type):
        order_details = await fetch_order_details(KEY, SECRET, order_no)
        if order_details:
            await insert_or_update_order(conn, order_details)
            order_details = await get_order_details(conn, order_no)
        else:
            logging.warning("Failed to fetch order details from the external source.")
            return
        if msg_type == 'system':
            await update_status_from_system_type(conn, msg_json, order_no)
            await handle_system_notifications(ws, msg_json, order_no, order_details, conn)
        msg_status = msg_json.get('status')
        if msg_status == 'read':
            return
        elif msg_type == 'text':
            await handle_text_message(ws, msg_json, order_no, order_details, conn)
        elif msg_type == 'image':
            await handle_image_message(ws, msg_json, order_no, order_details, conn)
