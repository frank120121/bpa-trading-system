import hashlib
import hmac
import aiohttp
import time
import asyncio
from binance_endpoints import TIME_ENDPOINT_V1, TIME_ENDPOINT_V3
import logging
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

class ServerTimestampCache:
    last_timestamp = None
    last_fetch_time = None
    rec_window = 3  # seconds

    @classmethod
    async def get_server_timestamp(cls):
        current_time = time.time()

        # Check if the last fetched timestamp is still valid
        if cls.last_timestamp is not None and (current_time - cls.last_fetch_time) < cls.rec_window:
            return cls.last_timestamp

        async with aiohttp.ClientSession() as session:
            for endpoint in [TIME_ENDPOINT_V3, TIME_ENDPOINT_V1]:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            cls.last_timestamp = data['serverTime']
                            cls.last_fetch_time = current_time
                            return cls.last_timestamp
                except Exception as e:
                    logger.error(f"An error occurred while fetching server time from {endpoint}: {e}")

        logger.error("Failed to fetch server time from all endpoints.")
        return None

# Replace the existing get_server_timestamp function with this
async def get_server_timestamp():
    return await ServerTimestampCache.get_server_timestamp()