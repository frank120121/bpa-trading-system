# bpa/binance_client.py
"""
Binance Client Module
Handles all Binance exchange operations including price feeds, order management, and WebSocket connections.
"""

import asyncio
import aiohttp
import websockets
import json
import hmac
import hashlib
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List

from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class BinanceClient:
    """Handles Binance REST + WebSocket (spot) for multiple assets."""

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_prices: Dict[str, Decimal] = {}  # symbol -> last trade price
        self._ws_tasks: Dict[str, asyncio.Task] = {}  # symbol -> task

    async def start_session(self):
        """Initialize the HTTP session with API key header."""
        self.session = aiohttp.ClientSession(headers={'X-MBX-APIKEY': self.api_key})

    async def close_session(self):
        """Clean shutdown of all WebSocket connections and HTTP session."""
        for t in list(self._ws_tasks.values()):
            t.cancel()
        self._ws_tasks.clear()
        if self.session:
            await self.session.close()
            self.session = None

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for signed requests."""
        query_string = '&'.join([f"{k}={v}" for k, v in data.items()])
        return hmac.new(
            self.api_secret.encode('utf-8'), 
            query_string.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    async def _request_signed(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Signed request for private endpoints."""
        if not self.session:
            raise RuntimeError("Client session not started.")
        
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._generate_signature(params)
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, params=params) as response:
                text = await response.text()
                if 200 <= response.status < 300:
                    return json.loads(text)
                logger.error(f"Binance API Error {response.status} on {endpoint}: {text}")
                raise aiohttp.ClientResponseError(
                    response.request_info, response.history, status=response.status, message=text
                )
        except aiohttp.ClientError as e:
            logger.error(f"Network error communicating with Binance: {e}")
            raise

    async def _request_public(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Unsigned request for public endpoints."""
        if not self.session:
            raise RuntimeError("Client session not started.")
        
        params = params or {}
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, params=params) as response:
                text = await response.text()
                if 200 <= response.status < 300:
                    return json.loads(text)
                logger.error(f"Binance PUBLIC API Error {response.status} on {endpoint}: {text}")
                raise aiohttp.ClientResponseError(
                    response.request_info, response.history, status=response.status, message=text
                )
        except aiohttp.ClientError as e:
            logger.error(f"Network error communicating with Binance: {e}")
            raise

    async def get_current_price(self, symbol: str) -> Decimal:
        """Get current ticker price for a symbol."""
        try:
            res = await self._request_public('GET', "/api/v3/ticker/price", {'symbol': symbol})
            px = Decimal(res['price'])
            self.last_prices[symbol] = px
            return px
        except Exception:
            logger.error(f"Could not fetch current price from Binance REST API for {symbol}.")
            return self.last_prices.get(symbol, Decimal('0'))

    async def place_market_order(self, symbol: str, quantity: Decimal, side: str) -> Dict[str, Any]:
        """Place a market order (BUY or SELL)."""
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol, 
            "side": side.upper(), 
            "type": "MARKET", 
            "quantity": f"{quantity:.8f}"
        }
        logger.info(f"Placing Binance market {side.upper()}: {quantity} {symbol}")
        return await self._request_signed('POST', endpoint, params)

    async def place_stop_limit_sell(self, symbol: str, quantity: Decimal, strike_price: Decimal) -> Dict[str, Any]:
        """Place a STOP_LOSS_LIMIT protective order at/near strike price."""
        endpoint = "/api/v3/order"
        stop_price = strike_price * Decimal('0.999')
        limit_price = strike_price * Decimal('0.998')
        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "STOP_LOSS_LIMIT",
            "quantity": f"{quantity:.8f}",
            "stopPrice": f"{stop_price:.6f}",
            "price": f"{limit_price:.6f}",
            "timeInForce": "GTC"
        }
        logger.info(f"Placing Binance STOP-LIMIT SELL: qty={quantity} {symbol} stop={stop_price} limit={limit_price}")
        return await self._request_signed('POST', endpoint, params)

    async def check_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Check the status of an existing order."""
        endpoint = "/api/v3/order"
        params = {"symbol": symbol, "orderId": order_id}
        return await self._request_signed('GET', endpoint, params)

    async def get_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """Get candlestick data for technical analysis."""
        endpoint = "/api/v3/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        try:
            async with self.session.get(f"{self.base_url}{endpoint}", params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"Failed to get klines: {resp.status}")
                return []
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching klines: {e}")
            return []

    async def _ws_price_task(self, symbol: str):
        """Maintains last trade price via websocket for a single symbol."""
        ws_symbol = symbol.lower()
        url = f"wss://stream.binance.com:9443/ws/{ws_symbol}@trade"
        
        while True:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to Binance WebSocket for {symbol}.")
                    async for message in ws:
                        data = json.loads(message)
                        self.last_prices[symbol] = Decimal(data['p'])
            except (websockets.ConnectionClosed, asyncio.TimeoutError) as e:
                logger.warning(f"Binance WebSocket disconnected for {symbol}: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected Binance WS error for {symbol}: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def ensure_ws(self, symbol: str):
        """Start websocket price stream for a symbol if not running."""
        if symbol not in self._ws_tasks or self._ws_tasks[symbol].done():
            self._ws_tasks[symbol] = asyncio.create_task(self._ws_price_task(symbol))

    def get_cached_price(self, symbol: str) -> Decimal:
        """Get the last cached price for a symbol."""
        return self.last_prices.get(symbol, Decimal('0'))

    def is_ws_connected(self, symbol: str) -> bool:
        """Check if WebSocket is active for a symbol."""
        return symbol in self._ws_tasks and not self._ws_tasks[symbol].done()