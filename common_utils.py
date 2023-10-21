import hashlib
import hmac
import aiohttp
import time
import asyncio
from binance_endpoints import TIME_ENDPOINT_V1, TIME_ENDPOINT_V3
import logging
from logging_config import setup_logging
setup_logging(log_filename='websocket_handler.log')
logger = logging.getLogger(__name__)
class RateLimiter:
    def __init__(self, limit_period=3):
        self.limit_period = limit_period
        self.last_message_times = {}
    
    def is_limited(self, user_id):
        current_time = time.time()
        last_time = self.last_message_times.get(user_id, 0)
        if current_time - last_time < self.limit_period:
            return True
        self.last_message_times[user_id] = current_time
        return False
async def retry_request(func, *args, max_retries=3, delay=5, **kwargs):
    for i in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except aiohttp.client_exceptions.ClientConnectorError as e:
            if i < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                raise e

def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
async def get_server_timestamp():
    endpoints = [TIME_ENDPOINT_V3, TIME_ENDPOINT_V1]

    for endpoint in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['serverTime']
        except Exception as e:
            logger.error(f"An error occurred while fetching server time from {endpoint}: {e}")

    logger.error("Failed to fetch server time from all endpoints.")
    return None