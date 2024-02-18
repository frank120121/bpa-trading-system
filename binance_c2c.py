import asyncio
import hashlib
import hmac
import aiohttp
from urllib.parse import urlencode
import websockets
from common_utils import get_server_timestamp, hashing
from binance_endpoints import GET_CHAT_CREDENTIALS 
from credentials import credentials_dict
from websocket_handlers import on_message
import logging
logger = logging.getLogger(__name__)

async def send_signed_request(http_method, url_path, KEY, SECRET, payload={}, dataLoad={}):
    query_string = urlencode(payload)
    query_string = f"{query_string}&timestamp={await get_server_timestamp()}"
    url = f"{url_path}?{query_string}&signature={hashing(query_string, SECRET)}"
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB"
    }
    async with aiohttp.ClientSession() as session:
        async with session.request(http_method, url, params={}, data=dataLoad, headers=headers) as response:
            response_data = await response.json()
            if 'data' not in response_data:
                logger.error("API Response does not contain 'data' field")
                return {'success': False}
            if response.status != 200:
                logger.error(f"Received status code {response.status}: {response_data}")
                return {'success': False}
            return {'success': True, 'data': response_data}
async def run_websocket(KEY, SECRET):
    uri_path = GET_CHAT_CREDENTIALS
    backoff = 1
    max_backoff = 10  # Maximum backoff time set to 10 seconds
    retry_count = 0
    max_retries = 200  # Maximum of 200 retry attempts

    while retry_count < max_retries:
        try:
            response = await send_signed_request("GET", uri_path, KEY, SECRET)
            wss_url = ''
            if 'data' in response and 'data' in response['data'] and 'chatWssUrl' in response['data']['data']:
                wss_url = f"{response['data']['data']['chatWssUrl']}/{response['data']['data']['listenKey']}?token={response['data']['data']['listenToken']}&clientType=web"
            else:
                logger.error(f"Key 'chatWssUrl' not found in API response. Full response: {response}")
                retry_count += 1
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2)
                continue

            logger.debug(f"Attempting to connect to WebSocket with URL: {wss_url}")
            async with websockets.connect(wss_url) as ws:
                async for message in ws:
                    await on_message(ws, message, KEY, SECRET)
            logger.info("WebSocket connection closed gracefully.")
            backoff = 1
            retry_count = 0

        except Exception as e:
            logger.exception("An unexpected error occurred:")
            await asyncio.sleep(backoff)
            backoff = min(max_backoff, backoff * 2)
            retry_count += 1

    logger.error(f"Reached maximum retry limit of {max_retries}. Exiting.")

async def main_binance_c2c():
    credentials = list(credentials_dict.values())
    tasks = []
    for cred in credentials:
        task = asyncio.create_task(
            run_websocket(cred['KEY'], cred['SECRET'])
        )
        tasks.append(task)
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.debug("KeyboardInterrupt received. Exiting.")
# if __name__ == "__main__":
#     setup_logging()
#     logger = logging.getLogger(__name__)
#     merchant_account = MerchantAccount()
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())
