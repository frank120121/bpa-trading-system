#bpa/binance_c2c.py
import asyncio
import json
import websockets

from src.customer_service.merchant_handler import MerchantAccount
from src.utils.common_utils import get_server_timestamp
from src.data.database.connection import create_connection, DB_FILE
from src.connectors.credentials import credentials_dict
from src.data.cache.share_data import SharedSession
from src.data.database.deposits.binance_bank_deposit import PaymentManager
from src.connectors.binance.api import BinanceAPI
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)


RETRY_DELAY = 0.1
MAX_RETRY_DELAY = 1
MAX_RETRIES = 3
class ConnectionManager:
    def __init__(self, payment_manager, binance_api, credentials_dict):
        self.connections = {}
        self.payment_manager = payment_manager
        self.binance_api = binance_api
        self.credentials_dict = credentials_dict

    def _should_process_message(self, msg_json):
        """Filter out messages that shouldn't be processed by merchant handler."""
        
        # Skip statistics messages
        if msg_json.get('type') in ['statistics', 'risk_alert']:
            logger.info(f"Skipping message: {msg_json.get('subType', 'unknown')}")
            return False
        
        # Skip self messages and auto replies
        if msg_json.get('self') or msg_json.get('type') == 'auto_reply':
            logger.info("Skipping self message or auto reply")
            return False
        
        return True

    async def create_connection(self, account):
        try:
            api_key, api_secret = self._get_credentials(account)
            wss_url = await self._get_wss_url(api_key, api_secret)

            ws = await websockets.connect(wss_url)
            self.connections[account] = {
                'ws': ws,
                'is_connected': True,
                'api_key': api_key,
                'api_secret': api_secret
            }
            logger.info(f"WebSocket connection established for account {account}")
        except Exception as e:
            logger.error(f"Failed to create connection for account {account}: {e}")
            self._set_failed_connection(account, api_key, api_secret)

    async def ensure_connection(self, account):
        if not self._is_connected(account):
            await self.create_connection(account)
        return self._is_connected(account)

    async def close_connection(self, account):
        if self._is_connected(account):
            ws = self.connections[account]['ws']
            await ws.close()
            self.connections[account]['is_connected'] = False
            logger.info(f"Connection closed for account {account}")

    async def send_text_message(self, account, text, order_no):
        for attempt in range(MAX_RETRIES):
            if await self.ensure_connection(account):
                if await self._send_message(account, text, order_no):
                    return
            logger.error(f"Attempt {attempt + 1}: Failed to send message for account {account}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)

        logger.error(f"Failed to send message after {MAX_RETRIES} attempts: No active connection for account {account}")

    async def get_session(self):
        return await SharedSession.get_session()

    async def run_websocket(self, account, merchant_account):
        while True:
            await self.ensure_connection(account)
            while self._is_connected(account):
                try:
                    message = await self.connections[account]['ws'].recv()
                    await self.on_message(merchant_account, account, message)
                except websockets.exceptions.ConnectionClosed as e:
                    logger.info(f"WebSocket connection closed for account {account} with code {e.code} and reason {e.reason}. Reconnecting...")
                    break
                except Exception as e:
                    logger.exception(f"Unexpected error for account {account}: {e}")
                    break
            await self.close_connection(account)
            await asyncio.sleep(5)

    async def on_message(self, merchant_account, account, message):
        try:
            msg_json = json.loads(message)
            
            # Filter messages before processing
            if not self._should_process_message(msg_json):
                return
            logger.info(f"Received message for account {account}: {msg_json}")
            await self._handle_message(merchant_account, account, msg_json, msg_json.get('type', ''))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message for account {account}: {e}")
        except Exception as e:
            logger.exception(f"An error occurred while processing the message for account {account}: {e}")

    async def check_connections(self):
        while True:
            failed_accounts = [account for account, conn in self.connections.items() if not conn['is_connected']]
            if failed_accounts:
                logger.warning(f"Detected {len(failed_accounts)} failed connections: {failed_accounts}")
                for account in failed_accounts:
                    await self.ensure_connection(account)
            await asyncio.sleep(300)

    def _get_credentials(self, account):
        return self.credentials_dict[account]['KEY'], self.credentials_dict[account]['SECRET']

    async def _get_wss_url(self, api_key, api_secret):
        response = await self.binance_api.retrieve_chat_credential(api_key, api_secret)
        if response and 'data' in response:
            data = response['data']
            if all(key in data for key in ['chatWssUrl', 'listenKey', 'listenToken']):
                return f"{data['chatWssUrl']}/{data['listenKey']}?token={data['listenToken']}&clientType=web"
        raise ValueError("Missing expected keys in API response data.")

    def _set_failed_connection(self, account, api_key, api_secret):
        self.connections[account] = {
            'ws': None,
            'is_connected': False,
            'api_key': api_key,
            'api_secret': api_secret
        }

    def _is_connected(self, account):
        return self.connections.get(account, {}).get('is_connected', False)

    async def _send_message(self, account, text, order_no):
        # Validate order_no before sending
        if not order_no or not str(order_no).strip():
            logger.error(f"Cannot send message: invalid order_no '{order_no}' for account {account}")
            return False
            
        message = {
            'type': 'text',
            'uuid': f"self_{await get_server_timestamp()}",
            'orderNo': str(order_no).strip(),
            'content': text,
            'self': True,
            'clientType': 'web',
            'createTime': await get_server_timestamp(),
            'sendStatus': 0
        }
        message_json = json.dumps(message)

        try:
            await asyncio.sleep(3)
            await self.connections[account]['ws'].send(message_json)
            logger.info(f"Message sent successfully for account {account}, order {order_no}")
            return True
        except Exception as e:
            logger.error(f"Message sending failed for account {account}: {e}")
            self.connections[account]['is_connected'] = False
            return False

    async def _handle_message(self, merchant_account, account, msg_json, msg_type):
        conn = await create_connection(DB_FILE)
        if conn:
            try:
                await merchant_account.handle_message_by_type(
                    self, account, 
                    self.connections[account]['api_key'], 
                    self.connections[account]['api_secret'], 
                    msg_json, conn
                )
                await conn.commit()
                logger.debug(f"Successfully processed message for account {account}")
            except Exception as e:
                await conn.rollback()
                logger.exception("Database operation failed, rolled back: %s", e)
            finally:
                await conn.close()
        else:
            logger.error("Failed to connect to the database.")

async def main_binance_c2c(payment_manager, binance_api):
    connection_manager = ConnectionManager(payment_manager, binance_api, credentials_dict)
    merchant_account = MerchantAccount(payment_manager, binance_api)
    
    # Initialize the validator with the connection_manager
    merchant_account.initialize_validator(connection_manager)
    
    # Start the validation processor
    validation_processor_task = await merchant_account.start_validation_processor()
    
    tasks = [
        asyncio.create_task(connection_manager.run_websocket(account, merchant_account))
        for account in credentials_dict.keys()
    ]
    tasks.append(asyncio.create_task(connection_manager.check_connections()))
    
    # Add the validation processor task to the list of tasks
    tasks.append(validation_processor_task)
    
    logger.info(f"Starting C2C service with {len(credentials_dict)} accounts")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    payment_manager = PaymentManager()
    binance_api = BinanceAPI()
    try:
        asyncio.run(main_binance_c2c(payment_manager, binance_api))
    except (KeyboardInterrupt, SystemExit):
        logger.info("C2C service shutting down...")
        pass