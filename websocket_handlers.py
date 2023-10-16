import json
from database import create_connection
from merchant_account import MerchantAccount
from common_vars import status_map
import logging
from logging_config import setup_logging
setup_logging(log_filename='websocket_handler.log')
logger = logging.getLogger(__name__)

async def on_message(ws, message, KEY, SECRET, merchant_account: MerchantAccount):
    try:
        msg_json = json.loads(message)
        is_self = msg_json.get('self', False)
        if is_self:
            logger.info("message was from self")
            return
        msg_type = msg_json.get('type', '')
        if msg_type == 'system':
                try:

                    content = msg_json.get('content', '')
                    content_dict = json.loads(content)
                    system_type = content_dict.get('type', '')
                    if system_type not in status_map:
                        logger.info("System type not in status_map")
                        return
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from content: {content}")
                    return
        conn = await create_connection("C:/Users/p7016/Documents/bpa/orders_data.db")
        if conn:
            try:
                await merchant_account.handle_message_by_type(ws, KEY, SECRET, msg_json, conn, msg_type)
                await conn.commit()               
            except Exception as e:
                await conn.rollback()
                logger.exception("Database operation failed, rolled back: %s", e)
            finally:
                await conn.close()
        else:
            logger.error("Failed to connect to the database.")
    except Exception as e:
        logger.exception("An exception occurred: %s", e)
async def on_close(ws, close_status_code, close_msg, KEY, SECRET):
    logger.debug(f"### closed ###")