"""
Polymarket Client Module
Handles order execution and position management on Polymarket using the CLOB client.
"""

import asyncio
import aiohttp
from decimal import Decimal
from typing import Dict, Any, Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class PolymarketClient:
    """Official Polymarket CLOB client wrapper for order execution and position management."""

    def __init__(self, private_key: str, api_creds: dict):
        self.host = "https://clob.polymarket.com"
        self.chain_id = 137  # Polygon Mainnet

        # Initialize official client
        self.clob_client = ClobClient(self.host, key=private_key, chain_id=self.chain_id)

        # API creds for authenticated actions
        creds = ApiCreds(
            api_key=api_creds['CLOB_API_KEY'],
            api_secret=api_creds['CLOB_SECRET'],
            api_passphrase=api_creds['CLOB_PASS_PHRASE'],
        )
        self.clob_client.set_api_creds(creds)

        self.trader_address = self.clob_client.get_address()
        logger.info(f"Polymarket client initialized for address: {self.trader_address}")

    async def get_price(self, token_id: str, side: str = "BUY") -> Optional[Decimal]:
        """GET /price?token_id=...&side=BUY -> Decimal or None."""
        url = f"{self.host}/price"
        params = {"token_id": token_id, "side": side}
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    p = data.get("price")
                    return Decimal(str(p)) if p is not None else None
        except Exception:
            return None

    async def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """Fetch orderbook. Return dict with 'asks'/'bids' lists of {price,size}."""
        try:
            ob = await asyncio.to_thread(self.clob_client.get_order_book, token_id)
            if ob is None:
                return {}
            
            def _side_to_list(side):
                out = []
                for x in (side or []):
                    price = getattr(x, "price", None)
                    size = getattr(x, "size", None)
                    if price is None and isinstance(x, (list, tuple)) and len(x) >= 2:
                        price, size = x[0], x[1]
                    out.append({"price": price, "size": size})
                return out
            
            asks_src = getattr(ob, "asks", None) or (ob.get("asks", []) if isinstance(ob, dict) else [])
            bids_src = getattr(ob, "bids", None) or (ob.get("bids", []) if isinstance(ob, dict) else [])
            return {"asks": _side_to_list(asks_src), "bids": _side_to_list(bids_src)}
        except Exception as e:
            logger.error(f"Error fetching order book for token {token_id}: {e}")
            return {}

    async def place_fok_order(self, token_id: str, num_shares: Decimal, price: Decimal) -> Dict[str, Any]:
        """Place Fill-or-Kill BUY order (for 'No' shares) at given price."""
        logger.info(f"Placing Polymarket FOK: buy {num_shares:.2f} @ ${price:.3f} token={token_id}")
        try:
            order_args = OrderArgs(
                price=float(price),
                size=float(num_shares),
                side=BUY,
                token_id=token_id,
            )
            signed_order = await asyncio.to_thread(self.clob_client.create_order, order_args)
            response = await asyncio.to_thread(self.clob_client.post_order, signed_order, OrderType.FOK)

            if isinstance(response, dict):
                status_code = response.get("status_code", 200)
                if 200 <= int(status_code) < 300:
                    return {"status": "success", "data": response}
                return {"status": "error", "message": response}
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to place Polymarket FOK order: {e}")
            return {"status": "error", "message": str(e)}

    async def place_market_order(self, token_id: str, num_shares: Decimal, side: str = "BUY") -> Dict[str, Any]:
        """Place a market order (immediate or cancel)."""
        logger.info(f"Placing Polymarket market {side}: {num_shares:.2f} shares token={token_id}")
        try:
            # Get current best price for the side
            current_price = await self.get_price(token_id, side=side)
            if not current_price:
                return {"status": "error", "message": "Could not get current price"}

            # Add some slippage for market orders
            if side.upper() == "BUY":
                order_price = current_price * Decimal('1.02')  # 2% above current price
            else:
                order_price = current_price * Decimal('0.98')  # 2% below current price

            order_args = OrderArgs(
                price=float(order_price),
                size=float(num_shares),
                side=BUY if side.upper() == "BUY" else SELL,
                token_id=token_id,
            )
            signed_order = await asyncio.to_thread(self.clob_client.create_order, order_args)
            response = await asyncio.to_thread(self.clob_client.post_order, signed_order, OrderType.IOC)

            if isinstance(response, dict):
                status_code = response.get("status_code", 200)
                if 200 <= int(status_code) < 300:
                    return {"status": "success", "data": response}
                return {"status": "error", "message": response}
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to place Polymarket market order: {e}")
            return {"status": "error", "message": str(e)}

    async def place_limit_order(self, token_id: str, num_shares: Decimal, price: Decimal, 
                               side: str = "BUY", order_type: str = "GTC") -> Dict[str, Any]:
        """Place a limit order."""
        logger.info(f"Placing Polymarket limit {side}: {num_shares:.2f} @ ${price:.3f} token={token_id}")
        try:
            order_args = OrderArgs(
                price=float(price),
                size=float(num_shares),
                side=BUY if side.upper() == "BUY" else SELL,
                token_id=token_id,
            )
            signed_order = await asyncio.to_thread(self.clob_client.create_order, order_args)
            
            # Map order type string to OrderType enum
            ot_map = {
                "GTC": OrderType.GTC,
                "FOK": OrderType.FOK,
                "IOC": OrderType.IOC
            }
            order_type_enum = ot_map.get(order_type.upper(), OrderType.GTC)
            
            response = await asyncio.to_thread(self.clob_client.post_order, signed_order, order_type_enum)

            if isinstance(response, dict):
                status_code = response.get("status_code", 200)
                if 200 <= int(status_code) < 300:
                    return {"status": "success", "data": response}
                return {"status": "error", "message": response}
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to place Polymarket limit order: {e}")
            return {"status": "error", "message": str(e)}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        logger.info(f"Cancelling Polymarket order: {order_id}")
        try:
            response = await asyncio.to_thread(self.clob_client.cancel, order_id)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to cancel Polymarket order {order_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of an order."""
        try:
            response = await asyncio.to_thread(self.clob_client.get_order, order_id)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def get_positions(self) -> Dict[str, Any]:
        """Get current positions/balances."""
        try:
            response = await asyncio.to_thread(self.clob_client.get_positions)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {"status": "error", "message": str(e)}

    async def get_orders(self, status: str = "open") -> Dict[str, Any]:
        """Get orders by status (open, closed, all)."""
        try:
            # Note: Adjust this based on the actual CLOB client API
            # The py_clob_client might have different method names
            response = await asyncio.to_thread(self.clob_client.get_orders)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return {"status": "error", "message": str(e)}

    async def get_market_info(self, condition_id: str) -> Dict[str, Any]:
        """Get market information for a given condition ID."""
        try:
            # This might need adjustment based on the actual CLOB client API
            response = await asyncio.to_thread(self.clob_client.get_market, condition_id)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get market info for {condition_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_trader_address(self) -> str:
        """Get the trader's wallet address."""
        return self.trader_address

    async def get_balance(self, token_id: Optional[str] = None) -> Dict[str, Any]:
        """Get balance for a specific token or all tokens."""
        try:
            if token_id:
                # Get balance for specific token
                response = await asyncio.to_thread(self.clob_client.get_balance, token_id)
            else:
                # Get all balances
                response = await asyncio.to_thread(self.clob_client.get_balances)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {"status": "error", "message": str(e)}

    async def get_trades(self, market: Optional[str] = None) -> Dict[str, Any]:
        """Get trade history."""
        try:
            if market:
                response = await asyncio.to_thread(self.clob_client.get_trades, market)
            else:
                response = await asyncio.to_thread(self.clob_client.get_trades)
            return {"status": "success", "data": response}
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return {"status": "error", "message": str(e)}

    def validate_order_params(self, token_id: str, num_shares: Decimal, price: Decimal) -> bool:
        """Validate order parameters before submission."""
        if not token_id or not token_id.strip():
            logger.error("Invalid token_id: empty or None")
            return False
        
        if num_shares <= 0:
            logger.error(f"Invalid num_shares: {num_shares} (must be positive)")
            return False
        
        if price <= 0 or price > 1:
            logger.error(f"Invalid price: {price} (must be between 0 and 1)")
            return False
        
        return True

    async def get_market_depth(self, token_id: str, depth: int = 10) -> Dict[str, Any]:
        """Get market depth (top N levels of orderbook)."""
        try:
            orderbook = await self.get_orderbook(token_id)
            if not orderbook:
                return {"status": "error", "message": "Could not fetch orderbook"}
            
            asks = orderbook.get("asks", [])[:depth]
            bids = orderbook.get("bids", [])[:depth]
            
            return {
                "status": "success",
                "data": {
                    "token_id": token_id,
                    "asks": asks,
                    "bids": bids,
                    "spread": self._calculate_spread(asks, bids)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get market depth for {token_id}: {e}")
            return {"status": "error", "message": str(e)}

    def _calculate_spread(self, asks: list, bids: list) -> Optional[float]:
        """Calculate bid-ask spread."""
        try:
            if not asks or not bids:
                return None
            
            best_ask = min(float(ask["price"]) for ask in asks if ask.get("price"))
            best_bid = max(float(bid["price"]) for bid in bids if bid.get("price"))
            
            return best_ask - best_bid if best_ask > best_bid else None
        except Exception:
            return None

    async def estimate_order_cost(self, token_id: str, num_shares: Decimal, side: str = "BUY") -> Dict[str, Any]:
        """Estimate the cost of an order including fees."""
        try:
            current_price = await self.get_price(token_id, side=side)
            if not current_price:
                return {"status": "error", "message": "Could not get current price"}
            
            gross_cost = num_shares * current_price
            # Assuming 0.25% taker fee (this should match your HedgeCalculator.TAKER_FEE_BPS)
            fee = gross_cost * Decimal('0.0025')
            total_cost = gross_cost + fee
            
            return {
                "status": "success",
                "data": {
                    "num_shares": float(num_shares),
                    "price_per_share": float(current_price),
                    "gross_cost": float(gross_cost),
                    "estimated_fee": float(fee),
                    "total_estimated_cost": float(total_cost)
                }
            }
        except Exception as e:
            logger.error(f"Failed to estimate order cost: {e}")
            return {"status": "error", "message": str(e)}