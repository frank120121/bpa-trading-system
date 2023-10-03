import json
from database import create_connection
from merchant_account import MerchantAccount
from common_utils import RateLimiter
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)
rate_limiter = RateLimiter(limit_period=3)

def should_ignore_message(msg_json):
    msg_type = msg_json.get('type', '')
    content = msg_json.get('content')
    inner_type = ''
    if content:
        try:
            content_json = json.loads(content)
            if isinstance(content_json, dict):
                inner_type = content_json.get('type', '')
        except json.JSONDecodeError:
            pass
    is_self = msg_json.get('self', False)
    if (is_self or 
        msg_type in ['auto_reply', 'system'] and inner_type == 'nlp_third_party'):
        return True
    return False

async def on_message(ws, message, KEY, SECRET, merchant_account: MerchantAccount):
    try:
        msg_json = json.loads(message)
        if should_ignore_message(msg_json):
            logger.info("Ignoring message of type: %s", msg_json.get('type', ''))
            return
        order_no = msg_json.get('orderNo', '')
        if rate_limiter.is_limited(order_no):
            logger.warning(f"Rate limit triggered for order: {order_no}")
            return

        msg_type = msg_json.get('type', '')
        conn = await create_connection("crypto_bot.db")
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