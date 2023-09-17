import json
import logging
from database import create_connection
from merchant_account import MerchantAccount
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)
async def on_message(ws, message, KEY, SECRET, merchant_account: MerchantAccount):
    try:
        msg_json = json.loads(message)
        msg_type = msg_json.get('type', '')
        is_self = msg_json.get('self', False)
        order_no = msg_json.get('orderNo', '')
        if is_self == True or msg_type == 'auto_reply':
            return
        conn = await create_connection("crypto_bot.db")
        logger.info("Received message: %s", message)
        if conn:
            try:
                await merchant_account.handle_message_by_type(ws, KEY, SECRET, msg_json, order_no, conn, msg_type)
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
    logger.info(f"### closed ###")