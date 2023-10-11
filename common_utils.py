import hashlib
import hmac
import aiohttp
import time
import asyncio
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
async def get_server_time():
    async with aiohttp.ClientSession() as session:
        response = await retry_request(session.get, "https://api.binance.com/api/v3/time")
        response_data = await response.json()
        return response_data['serverTime']
def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()