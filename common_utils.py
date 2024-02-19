import hashlib
import hmac
import time
import aiohttp
import asyncio
from binance_endpoints import TIME_ENDPOINT_V1, TIME_ENDPOINT_V3
import logging
logger = logging.getLogger(__name__)

def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

class ServerTimestampCache:
    last_timestamp = None
    sync_interval = 1800  # Sync every 30 minutes
    offset = None

    @classmethod
    async def fetch_server_time(cls):
        async with aiohttp.ClientSession() as session:
            for endpoint in [TIME_ENDPOINT_V3, TIME_ENDPOINT_V1]:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            server_time = data['serverTime']
                            cls.offset = server_time - int(time.time() * 1000)
                            logger.info(f"Updated server timestamp: {server_time}")
                            return
                except Exception as e:
                    logger.error(f"Failed to fetch server time from {endpoint}: {e}")
        
        logger.error("Failed to update server timestamp from all endpoints.")

    @classmethod
    async def maintain_timestamp(cls):
        while True:
            await cls.fetch_server_time()
            await asyncio.sleep(cls.sync_interval)

    @classmethod
    def get_server_timestamp(cls):
        if cls.offset is None:
            logger.error("Server timestamp offset is not initialized.")
            return None
        return int(time.time() * 1000) + cls.offset

# Initialize and start the timestamp update task when your application starts
async def start_timestamp_maintenance():
    asyncio.create_task(ServerTimestampCache.maintain_timestamp())


def get_server_timestamp():
    return ServerTimestampCache.get_server_timestamp()