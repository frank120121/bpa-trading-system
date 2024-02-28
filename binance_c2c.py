
import asyncio
import aiohttp
from urllib.parse import urlencode
import websockets
from websockets.exceptions import ConnectionClosedError
import logging
import json
from common_utils import get_server_timestamp, hashing
from binance_endpoints import GET_CHAT_CREDENTIALS
from credentials import credentials_dict
from binance_ws_c2c import on_message

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, uri, api_key, secret_key):
        self.uri = uri
        self.api_key = api_key
        self.secret_key = secret_key
        self.ws = None
        self.is_connected = False


    async def connect(self):
        # Ensure any existing connection is closed before establishing a new one
        try:
            if self.ws:
                await self.ws.close()
            self.ws = await websockets.connect(self.uri, open_timeout=10)
            self.is_connected = True
            logger.info("connect() successful.")
        
        except ConnectionClosedError as e:
            logger.error(f"connect closed error: {e}.")
            self.is_connected = False
        except asyncio.TimeoutError as e:
            logger.error(f"connect() timeout error: {e}.")
            self.is_connected = False
        except Exception as e:
            logger.exception(f"Generic exception: {e}.")
            self.is_connected = False
        

    async def listen(self, on_message_callback):
        try:
            await self.connect()
            async for message in self.ws:
                await on_message_callback(self, message, self.api_key, self.secret_key)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed unexpectedly: {e}.")
            self.is_connected = False
        except asyncio.TimeoutError as e:
            logger.error(f"WebSocket connection attempt timed out: {e}.")
            self.is_connected = False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during WebSocket communication: {e}.")
            self.is_connected = False
        finally:
            logger.info("Attempting to re-establish WebSocket connection...")
            await self.reconnect()

    async def reconnect(self):
        while not self.is_connected:
            try:
                await asyncio.sleep(1)  # Wait before attempting to reconnect
                await self.connect()  # Attempt to establish a new connection
            except Exception as e:
                logger.exception(f"An error occurred while trying to reconnect: {e}")


    async def send_text_message(self, text, order_no):
        # Preparing the message payload outside of the try block to avoid
        # including JSON serialization errors in the reconnection logic
        message = {
            'type': 'text',
            'uuid': f"self_{await get_server_timestamp()}",
            'orderNo': order_no,
            'content': text,
            'self': False,
            'clientType': 'web',
            'createTime': await get_server_timestamp(),
            'sendStatus': 4
        }
        message_json = json.dumps(message)

        try:
            if not self.is_connected:
                logger.info("WebSocket is not connected, attempting to reconnect before sending.")
                await self.reconnect()

            if self.is_connected:
                await self.ws.send(message_json)  # Attempt to send the message
                logger.debug(f"Message sent successfully: {text}")
            else:
                # If the connection is still not established after an attempt to reconnect,
                # it's critical to inform that the message won't be sent.
                logger.error("Failed to reconnect; message not sent.")
                # Optionally, you could implement a mechanism to queue the message for later delivery.

        except Exception as e:
            logger.error(f"Failed to send message due to an exception: {e}")

async def establish_websocket_connection(account_name, api_key, secret_key):
    logger.info(f"Starting WebSocket connection for: {account_name}")  
    try:
        wss_url = await get_websocket_url(api_key, secret_key)
        if wss_url:
            connection_manager = ConnectionManager(wss_url, api_key, secret_key)
            await connection_manager.listen(on_message)
            logger.info(f"WebSocket connection established successfully for: {account_name}") 
        else:
            logger.error(f"Failed to get WebSocket URL for {account_name}.")
    except Exception as e:
        logger.exception(f"An error occurred during WebSocket connection for {account_name}: {e}")

async def send_http_request(method, url, api_key, secret_key, params=None, body=None):
    try:
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
    except Exception as e:
        logger.exception(f"An error occurred in send_http_request: {e}")
        return None


async def get_websocket_url(api_key, secret_key):
    response_data = await send_http_request("GET", GET_CHAT_CREDENTIALS, api_key, secret_key)
    if response_data and 'chatWssUrl' in response_data and 'listenKey' in response_data:
        return f"{response_data['chatWssUrl']}/{response_data['listenKey']}?token={response_data['listenToken']}&clientType=web"
    return None
        
async def main_binance_c2c():
    logger.info("Starting WebSocket connections for Binance C2C.")
    tasks = [establish_websocket_connection(account_name, cred['KEY'], cred['SECRET']) for account_name, cred in credentials_dict.items()]
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("An unexpected error occurred: ", exc_info=e)
    finally:
        logger.info("Finished all WebSocket connections.")