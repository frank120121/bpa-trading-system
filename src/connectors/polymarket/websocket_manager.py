"""
Polymarket WebSocket Manager
Manages WebSocket connections to Polymarket for real-time price updates.
Uses the websocket-client library like the official Polymarket examples.
"""

import asyncio
import json
import threading
import time
from decimal import Decimal
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone

from websocket import WebSocketApp
from src.connectors.polymarket.opportunities import shared_opportunities, OpportunityData
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class PolymarketWebSocketManager:
    """
    Manages WebSocket connections to Polymarket for real-time price monitoring.
    Based on the official Polymarket WebSocket example using websocket-client.
    """
    
    def __init__(self, api_creds: Dict[str, str]):
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com"
        self.api_creds = api_creds
        self.ws: Optional[WebSocketApp] = None
        self.is_running = False
        self.subscribed_tokens: Set[str] = set()
        self.ping_thread: Optional[threading.Thread] = None
        
        # Price thresholds for unsubscribing
        self.min_price_threshold = Decimal('0')
        self.max_price_threshold = Decimal('0.3')
        
        # Channel types
        self.MARKET_CHANNEL = "market"
        self.USER_CHANNEL = "user"
        
    async def start(self):
        """Start the WebSocket manager."""
        if self.is_running:
            logger.warning("WebSocket manager already running")
            return
            
        self.is_running = True
        logger.info("Starting Polymarket WebSocket manager...")
        
        # Start in a separate thread since websocket-client is synchronous
        ws_thread = threading.Thread(target=self._run_websocket)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Start subscription management task
        subscription_task = asyncio.create_task(self._manage_subscriptions())
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_task())
        
        # Wait for tasks to complete
        try:
            await asyncio.gather(subscription_task, cleanup_task)
        except asyncio.CancelledError:
            logger.info("WebSocket manager tasks cancelled")
        finally:
            self.is_running = False

    def _run_websocket(self):
        """Run WebSocket connection in a separate thread."""
        while self.is_running:
            try:
                # Get asset IDs that need to be subscribed
                opportunities = shared_opportunities.get_unsubscribed_opportunities()
                asset_ids = [opp.no_token_id for opp in opportunities]
                
                if not asset_ids:
                    # No assets to subscribe to yet, wait and retry
                    time.sleep(5)
                    continue
                
                logger.info(f"Starting WebSocket connection for {len(asset_ids)} assets")
                
                # Create WebSocket connection
                furl = f"{self.ws_url}/ws/{self.MARKET_CHANNEL}"
                self.ws = WebSocketApp(
                    furl,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                
                # Store asset IDs for the connection
                self.current_asset_ids = asset_ids
                
                # Run the WebSocket (this blocks until connection closes)
                self.ws.run_forever()
                
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
                if self.is_running:
                    logger.info("Reconnecting in 5 seconds...")
                    time.sleep(5)

    def _on_open(self, ws):
        """Called when WebSocket connection opens."""
        try:
            # Subscribe to market channel with asset IDs
            subscribe_msg = {
                "assets_ids": self.current_asset_ids,  # Note: Polymarket uses "assets_ids" not "asset_ids"
                "type": self.MARKET_CHANNEL
            }
            
            ws.send(json.dumps(subscribe_msg))
            
            # Mark all assets as subscribed
            for asset_id in self.current_asset_ids:
                self.subscribed_tokens.add(asset_id)
                opp = shared_opportunities.get_opportunity_by_token(asset_id)
                if opp:
                    shared_opportunities.mark_subscribed(opp.condition_id)
            
            logger.info(f"WebSocket opened and subscribed to {len(self.current_asset_ids)} assets")
            
            # Start ping thread
            self.ping_thread = threading.Thread(target=self._ping_worker, args=(ws,))
            self.ping_thread.daemon = True
            self.ping_thread.start()
            
        except Exception as e:
            logger.error(f"Error in WebSocket on_open: {e}")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            if message == "PONG":
                return  # Ignore pong responses
            
            # Log the raw message for debugging
            logger.info(f"WebSocket message received: {message}")
            
            data = json.loads(message)
            
            # Polymarket sends an array of market updates
            if isinstance(data, list):
                for market_update in data:
                    if isinstance(market_update, dict):
                        asset_id = market_update.get("asset_id")
                        if asset_id and asset_id in self.subscribed_tokens:
                            # Extract price from orderbook data
                            price = self._extract_price_from_polymarket_message(market_update)
                            if price is not None:
                                # Since we're in a separate thread, we need to handle the async call differently
                                self._handle_price_update(asset_id, price)
            
        except json.JSONDecodeError:
            logger.debug(f"Non-JSON message received: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def _handle_price_update(self, token_id: str, new_price: Decimal):
        """Handle price update in a thread-safe way."""
        try:
            # Update price in shared resource (this is thread-safe)
            updated = shared_opportunities.update_price(token_id, new_price)
            
            if updated:
                logger.debug(f"Updated price for {token_id}: ${new_price}")
                
                # Check if we should unsubscribe due to price thresholds
                if (new_price <= self.min_price_threshold or 
                    new_price >= self.max_price_threshold):
                    
                    logger.info(f"Price threshold hit for {token_id}: ${new_price}. Will unsubscribe on next connection cycle...")
                    
                    # Remove from shared opportunities
                    opp = shared_opportunities.get_opportunity_by_token(token_id)
                    if opp:
                        shared_opportunities.remove_opportunity(opp.condition_id)
        except Exception as e:
            logger.error(f"Error handling price update: {e}")

    def _extract_price_from_polymarket_message(self, market_data: Dict[str, Any]) -> Optional[Decimal]:
        """
        Extract the appropriate price for buying NO shares from Polymarket WebSocket message.
        
        For buying NO shares, we want to use bid + 0.001 to get filled quickly at the best price.
        """
        try:
            # Handle both message types: "book" and "price_change"
            event_type = market_data.get("event_type", "")
            
            if event_type == "price_change":
                # New price_change format - find our subscribed asset
                price_changes = market_data.get("price_changes", [])
                for change in price_changes:
                    asset_id = change.get("asset_id")
                    if asset_id and asset_id in self.subscribed_tokens:
                        best_bid = change.get("best_bid")
                        best_ask = change.get("best_ask")
                        
                        if best_bid:
                            try:
                                bid_price = Decimal(str(best_bid))
                                
                                # Use bid + 0.001 for competitive pricing that should fill quickly
                                competitive_price = bid_price + Decimal('0.001')
                                
                                # Ensure we don't exceed the ask price
                                if best_ask:
                                    ask_price = Decimal(str(best_ask))
                                    competitive_price = min(competitive_price, ask_price)
                                
                                logger.debug(f"Asset {asset_id}: bid={bid_price}, competitive_price={competitive_price}")
                                return competitive_price
                                
                            except (ValueError, TypeError):
                                continue
            
            elif event_type == "book":
                # Original book format - use bids to calculate competitive price
                bids = market_data.get("bids", [])
                if not bids:
                    logger.debug(f"No bids found in market data for asset {market_data.get('asset_id')}")
                    return None
                
                # Find the best (highest) bid price
                best_bid = None
                for bid in bids:
                    if isinstance(bid, dict) and "price" in bid:
                        try:
                            price = Decimal(str(bid["price"]))
                            if best_bid is None or price > best_bid:
                                best_bid = price
                        except (ValueError, TypeError):
                            continue
                
                if best_bid:
                    # Return bid + 0.001
                    return best_bid + Decimal('0.001')
            
            logger.debug(f"No valid price found in message: {market_data}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price from Polymarket message: {e}")
            return None

    def _handle_price_update(self, token_id: str, new_price: Decimal):
        """Handle price update in a thread-safe way."""
        try:
            # Update price in shared resource (this is thread-safe)
            updated = shared_opportunities.update_price(token_id, new_price)
            
            if updated:
                logger.debug(f"Updated price for {token_id}: ${new_price}")
                
                # Check if we should unsubscribe due to price thresholds
                if (new_price <= self.min_price_threshold or 
                    new_price >= self.max_price_threshold):
                    
                    logger.info(f"Price threshold hit for {token_id}: ${new_price}. Will unsubscribe on next connection cycle...")
                    
                    # Remove from shared opportunities
                    opp = shared_opportunities.get_opportunity_by_token(token_id)
                    if opp:
                        shared_opportunities.remove_opportunity(opp.condition_id)
        except Exception as e:
            logger.error(f"Error handling price update: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Mark all tokens as unsubscribed
        for token_id in list(self.subscribed_tokens):
            self.subscribed_tokens.discard(token_id)
            opp = shared_opportunities.get_opportunity_by_token(token_id)
            if opp:
                shared_opportunities.mark_unsubscribed(opp.condition_id)

    def _ping_worker(self, ws):
        """Send periodic pings to keep connection alive."""
        while self.is_running and ws.sock and ws.sock.connected:
            try:
                ws.send("PING")
                time.sleep(10)
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break

    async def _manage_subscriptions(self):
        """Periodically check for new opportunities that need WebSocket connections."""
        while self.is_running:
            try:
                # Check if we need to restart connection with new assets
                unsubscribed = shared_opportunities.get_unsubscribed_opportunities()
                
                if unsubscribed and (not self.ws or not self.ws.sock or not self.ws.sock.connected):
                    logger.info(f"Found {len(unsubscribed)} unsubscribed opportunities, connection will restart")
                
                # Check for opportunities that should be removed
                to_remove = shared_opportunities.get_opportunities_to_unsubscribe()
                for opp in to_remove:
                    shared_opportunities.remove_opportunity(opp.condition_id)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in subscription management: {e}")
                await asyncio.sleep(10)

    async def _cleanup_task(self):
        """Periodic cleanup of expired opportunities."""
        while self.is_running:
            try:
                # Clean up expired opportunities
                shared_opportunities.cleanup_expired()
                
                # Log status periodically
                shared_opportunities.log_status()
                
                # Log WebSocket stats
                is_connected = self.ws and self.ws.sock and self.ws.sock.connected
                logger.info(
                    f"WebSocket Status: Connected={is_connected}, "
                    f"Subscriptions={len(self.subscribed_tokens)}"
                )
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the WebSocket manager and close connections."""
        logger.info("Stopping Polymarket WebSocket manager...")
        self.is_running = False
        
        # Close WebSocket connection
        if self.ws:
            self.ws.close()
        
        # Clear subscriptions
        self.subscribed_tokens.clear()

    def get_subscribed_tokens(self) -> Set[str]:
        """Get set of currently subscribed token IDs."""
        return self.subscribed_tokens.copy()

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.ws is not None and self.ws.sock is not None and self.ws.sock.connected

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            'is_connected': self.is_connected(),
            'subscribed_tokens_count': len(self.subscribed_tokens),
            'subscribed_tokens': list(self.subscribed_tokens),
            'is_running': self.is_running
        }