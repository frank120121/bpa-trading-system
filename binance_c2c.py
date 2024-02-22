import asyncio
import aiohttp
from urllib.parse import urlencode
import websockets
import logging
from common_utils import get_server_timestamp, hashing
from binance_endpoints import GET_CHAT_CREDENTIALS
from credentials import credentials_dict
from binance_ws_c2c import on_message


# #Websocket Streams
# A single connection to stream.binance.com is only valid for 24 hours; expect to be disconnected at the 24 hour mark
# Websocket server will send a ping frame every 3 minutes.
# If the websocket server does not receive a pong frame back from the connection within a 10 minute period, the connection will be disconnected.
# When you receive a ping, you must send a pong with a copy of ping's payload as soon as possible.
# Unsolicited pong frames are allowed, but will not prevent disconnection. It is recommended that the payload for these pong frames are empty.
# WebSocket connections have a limit of 5 incoming messages per second. A message is considered:
# A PING frame
# A PONG frame
# A JSON control message (e.g. subscribe, unsubscribe)


logger = logging.getLogger(__name__)

async def send_http_request(method, url, api_key, secret_key, params=None, body=None):
    params = params or {}
    params['timestamp'] = await get_server_timestamp()
    query_string = urlencode(params)
    signature = hashing(query_string, secret_key)
    final_url = f"{url}?{query_string}&signature={signature}"
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": api_key,
        "clientType": "WEB"
    }

    async with aiohttp.ClientSession() as session:
        async with session.request(method, final_url, json=body, headers=headers) as response:
            response_data = await response.json()
            if response.status != 200 or 'data' not in response_data:
                logger.error(f"Error {response.status} from API: {response_data}")
                return None
            return response_data['data']

async def get_websocket_url(api_key, secret_key):
    response_data = await send_http_request("GET", GET_CHAT_CREDENTIALS, api_key, secret_key)
    if response_data and 'chatWssUrl' in response_data and 'listenKey' in response_data:
        return f"{response_data['chatWssUrl']}/{response_data['listenKey']}?token={response_data['listenToken']}&clientType=web"
    return None

async def websocket_listener(uri, api_key, secret_key):
    async with websockets.connect(uri, ping_interval=None) as ws:  # Disable automatic ping
        message_count = 0
        start_time = asyncio.get_event_loop().time()
        try:
            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10 * 60)  # 10 minutes timeout
                    if isinstance(message, (bytes, bytearray)):
                        await ws.pong(message)  # Respond to pings with pongs
                    else:
                        await on_message(ws, message, api_key, secret_key)

                        # Rate limit handling
                        message_count += 1
                        if message_count >= 5:
                            elapsed_time = asyncio.get_event_loop().time() - start_time
                            if elapsed_time < 1:
                                await asyncio.sleep(1 - elapsed_time)
                            message_count = 0
                            start_time = asyncio.get_event_loop().time()

                except asyncio.TimeoutError:
                    logger.error("Timeout. Sending ping to keep connection alive.")
                    await ws.ping()

        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed normally, attempting to reconnect.")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed with error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in WebSocket listener: {e}")

async def establish_websocket_connection(account_name, api_key, secret_key, retries=200, backoff=1, max_backoff=10):
    logger.info(f"Starting WebSocket connection for: {account_name}")  # Log the account for which the connection is starting
    for attempt in range(retries):
        try:
            wss_url = await get_websocket_url(api_key, secret_key)
            if wss_url:
                await websocket_listener(wss_url, api_key, secret_key)
                logger.info(f"WebSocket connection established successfully for: {account_name}")
                return  # Successfully connected and processed messages
            else:
                logger.error(f"Failed to get WebSocket URL for {account_name}.")
        except Exception as e:
            logger.exception(f"An error occurred during WebSocket connection for {account_name}:", exc_info=e)
        await asyncio.sleep(backoff)
        backoff = min(max_backoff, backoff * 2)
    logger.error(f"Reached maximum retry limit for {account_name}. Exiting.")

async def main_binance_c2c():
    logger.info("Starting WebSocket connections for Binance C2C.")
    tasks = [establish_websocket_connection(account_name, cred['KEY'], cred['SECRET']) for account_name, cred in credentials_dict.items()]
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("An unexpected error occurred: ", exc_info=e)
    finally:
        logger.info("Finished all WebSocket connections.")
