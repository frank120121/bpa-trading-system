# bpa/polymarket/polymarket.py
"""
Main Polymarket-Binance Hedged Betting System
Refactored main file that orchestrates the three main components.
"""

import asyncio
import sys
import os
import configparser
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

# Add project root to Python path - need 4 dirname() calls to get from main.py to bpa/
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.connectors.binance.client import BinanceClient
from risk_hedge import HedgeCalculator, RiskAnalyzer
from scanner import GammaClient, PolymarketScanner
from client import PolymarketClient
from websocket_manager import PolymarketWebSocketManager
from opportunities import shared_opportunities


# --- Configuration and Logging ---

from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

def load_config(filename="config.ini"):
    """Loads configuration from an INI file."""
    if not os.path.exists(filename):
        logger.critical(f"CRITICAL: Configuration file '{filename}' not found. Exiting.")
        raise SystemExit(1)

    config = configparser.ConfigParser()
    config.read(filename)
    return config


# --- Position Management ---

class Position:
    """Holds info about an active hedge position."""

    def __init__(self, opportunity, hedge_details, base_order, stop_order):
        self.id = f"pos_{base_order.get('orderId', int(time.time()))}"
        self.market_question = opportunity['market_question']
        self.strike_price = opportunity['strike_price']
        self.breakeven_price = hedge_details['breakeven_price']
        self.base_amount = Decimal(str(base_order.get('executedQty', '0')))
        self.base_entry_price = self._calculate_avg_price(base_order)
        self.no_shares_amount = hedge_details['no_shares_needed']
        self.no_shares_cost = hedge_details['total_cost_usd']
        self.binance_symbol = base_order['symbol']
        self.binance_stop_order_id = stop_order.get('orderId') if isinstance(stop_order, dict) else None
        self.creation_time = datetime.now()
        self.active = True

    def _calculate_avg_price(self, order_data):
        """Calculate average fill price from order data."""
        fills = order_data.get('fills', [])
        if not fills:
            return Decimal('0')
        total_value = sum(Decimal(f['price']) * Decimal(f['qty']) for f in fills)
        total_qty = sum(Decimal(f['qty']) for f in fills)
        return total_value / total_qty if total_qty > 0 else Decimal('0')

    def __repr__(self):
        return (f"Position(id={self.id}, market='{self.market_question}', strike=${self.strike_price}, "
                f"breakeven=${self.breakeven_price:.6f}, stop_id={self.binance_stop_order_id})")


# --- Main Bot Class ---

class PolymarketBinanceHedgingBot:
    """Main bot orchestrator that coordinates all components."""

    def __init__(self, config, binance_creds, polymarket_creds):
        self.config = config
        self.is_running = False
        
        # Initialize clients
        self.binance = BinanceClient(
            api_key=binance_creds['KEY'],
            api_secret=binance_creds['SECRET'],
            base_url=config.get('binance', 'base_url')
        )
        self.polymarket = PolymarketClient(
            private_key=polymarket_creds['private_key'],
            api_creds=polymarket_creds['clob_api']
        )
        self.gamma = GammaClient()
        self.polymarket_ws = PolymarketWebSocketManager(polymarket_creds['clob_api'])
        
        # Initialize analyzers and scanners
        self.scanner = PolymarketScanner(self.binance, self.gamma)
        self.risk_analyzer = RiskAnalyzer(self.binance, self.config)
        
        # Position management
        self.active_positions: Dict[str, Position] = {}
        self.max_positions = int(config.get('risk_management', 'max_concurrent_positions', fallback='1'))

        # Asset configuration
        self.assets = self._load_asset_configurations()
        self.days_min = int(config.get('trading_parameters', 'min_days_to_expiry', fallback='7'))
        self.days_max = int(config.get('trading_parameters', 'max_days_to_expiry', fallback='130'))

    def _load_asset_configurations(self) -> List[Dict[str, Any]]:
        """Load asset configurations from config file with fallback defaults."""
        def _dec(section, key, fallback):
            try:
                return Decimal(self.config.get(section, key, fallback=str(fallback)))
            except Exception:
                return Decimal(str(fallback))

        return [
            {
                "name": "BTC",
                "keywords": ["btc", "bitcoin"],
                "binance_symbol": "BTCUSDT",
                "trade_amount": _dec('trading_parameters', 'btc_trade_amount', '0.01'),
                "max_no_price": _dec('trading_parameters', 'btc_max_no_price', '0.20'),
            },
            {
                "name": "ETH",
                "keywords": ["eth", "ethereum"],
                "binance_symbol": "ETHUSDT",
                "trade_amount": _dec('trading_parameters', 'eth_trade_amount', '0.10'),
                "max_no_price": _dec('trading_parameters', 'eth_max_no_price', '0.20'),
            },
            {
                "name": "SOL",
                "keywords": ["sol", "solana"],
                "binance_symbol": "SOLUSDT",
                "trade_amount": _dec('trading_parameters', 'sol_trade_amount', '5'),
                "max_no_price": _dec('trading_parameters', 'sol_max_no_price', '0.20'),
            },
            {
                "name": "XRP",
                "keywords": ["xrp", "ripple"],
                "binance_symbol": "XRPUSDT",
                "trade_amount": _dec('trading_parameters', 'xrp_trade_amount', '500'),
                "max_no_price": _dec('trading_parameters', 'xrp_max_no_price', '0.20'),
            },
        ]

    async def execute_hedge(self, opportunity_data):
        """Execute a complete hedge strategy for an opportunity from shared resource."""
        symbol = opportunity_data.binance_symbol
        base_amount = opportunity_data.trade_amount

        # Get current spot price
        spot = self.binance.get_cached_price(symbol)
        if spot == 0:
            spot = await self.binance.get_current_price(symbol)
        if spot == 0:
            logger.error(f"Cannot execute hedge, spot unknown for {symbol}.")
            return None

        # Use real-time NO price from WebSocket if available
        current_no_price = opportunity_data.current_no_price
        if current_no_price <= 0:
            # Fallback to getting price via REST API
            current_no_price = await self.polymarket.get_price(opportunity_data.no_token_id, side="BUY")
            if not current_no_price or current_no_price <= 0:
                logger.error(f"Cannot get valid NO price for {opportunity_data.no_token_id}")
                return None

        # Calculate hedge parameters using real-time price
        hedge_details = HedgeCalculator.calculate_hedge(
            spot, opportunity_data.strike_price, current_no_price, base_amount
        )
        if not hedge_details:
            logger.warning(f"Could not calculate hedge for {opportunity_data.market_question}")
            return None

        logger.info(
            f"Hedge: {symbol} Breakeven=${hedge_details['breakeven_price']:.6f}, "
            f"Cost=${hedge_details['total_cost_usd']:.2f}, "
            f"RR={hedge_details['risk_reward_ratio']:.3f}, "
            f"Real-time NO price=${current_no_price:.3f}"
        )

        # Risk validation
        risk_ok = await self.risk_analyzer.validate_opportunity(hedge_details['breakeven_price'], symbol)
        if not risk_ok:
            return None

        poly_order, base_order, stop_order = None, None, None

        try:
            # 1) Buy No shares on Polymarket (FOK) using real-time price
            poly_order = await self.polymarket.place_fok_order(
                opportunity_data.no_token_id,
                hedge_details['no_shares_needed'],
                current_no_price
            )
            if not poly_order or poly_order.get('status') != 'success':
                raise RuntimeError(f"Polymarket order failed: {poly_order.get('message', 'No details')}")

            logger.info("Polymarket 'No' shares order placed successfully.")

            # 2) Buy base asset on Binance
            base_order = await self.binance.place_market_order(symbol, base_amount, 'BUY')
            if base_order.get('status') not in ('FILLED', 'PARTIALLY_FILLED'):
                raise RuntimeError("Binance BUY did not fill.")

            logger.info(f"Binance {symbol} market buy executed.")

            # 3) Protective STOP-LIMIT near strike
            stop_order = await self.binance.place_stop_limit_sell(
                symbol, Decimal(str(base_order['executedQty'])), opportunity_data.strike_price
            )
            logger.info("Binance STOP-LIMIT sell order placed.")

            # 4) Track position - convert OpportunityData to dict format for Position class
            opportunity_dict = {
                'market_question': opportunity_data.market_question,
                'strike_price': opportunity_data.strike_price,
                'no_price': current_no_price,  # Use the actual executed price
                'no_token_id': opportunity_data.no_token_id,
                'expiry': opportunity_data.expiry,
                'days_to_expiry': opportunity_data.days_to_expiry,
                'binance_symbol': opportunity_data.binance_symbol
            }
            position = Position(opportunity_dict, hedge_details, base_order, stop_order)
            self.active_positions[position.id] = position
            
            # Remove from shared opportunities since we executed it
            shared_opportunities.remove_opportunity(opportunity_data.condition_id)
            
            logger.info(f"SUCCESS: New position created: {position}")

        except Exception as e:
            logger.error(f"Hedge execution failed for {symbol}: {e}. Unwinding...")
            try:
                if base_order and base_order.get('status') in ('FILLED', 'PARTIALLY_FILLED'):
                    qty = Decimal(str(base_order['executedQty']))
                    if qty > 0:
                        logger.critical("CRITICAL: Attempting immediate MARKET SELL to unwind.")
                        await self.binance.place_market_order(symbol, qty, 'SELL')
            except Exception as unwind_e:
                logger.critical(f"CRITICAL FAILURE TO UNWIND {symbol}: {unwind_e}")

            if poly_order and poly_order.get('status') == 'success':
                logger.warning("Polymarket leg filled but hedge failed later. MANUAL UNWIND MAY BE REQUIRED.")

    async def monitor_positions(self):
        """Monitor active positions and handle closures."""
        while self.is_running:
            await asyncio.sleep(30)
            if not self.active_positions:
                continue
                
            for pos_id, pos in list(self.active_positions.items()):
                try:
                    status_response = await self.binance.check_order_status(
                        pos.binance_symbol, pos.binance_stop_order_id
                    )
                    status = status_response.get('status')
                    
                    if status in ['FILLED', 'CANCELED', 'EXPIRED', 'REJECTED']:
                        logger.info(f"Position '{pos.market_question}' closed. Stop status: {status}.")
                        del self.active_positions[pos_id]
                except Exception as e:
                    logger.error(f"Could not check status for position {pos_id}: {e}")

    async def initialize_price_feeds(self):
        """Initialize price feeds for all configured assets."""
        logger.info("Hedging Bot running. Waiting for initial prices...")
        
        for asset in self.assets:
            symbol = asset['binance_symbol']
            self.binance.ensure_ws(symbol)
            
            # Wait for initial price
            tries = 0
            while self.binance.get_cached_price(symbol) == 0 and tries < 20:
                await asyncio.sleep(0.5)
                tries += 1
                
            if self.binance.get_cached_price(symbol) == 0:
                # Attempt REST if WebSocket hasn't ticked yet
                await self.binance.get_current_price(symbol)
                
            current_price = self.binance.get_cached_price(symbol)
            logger.info(f"Initial {symbol} Price: ${current_price:.6f}")

    async def run_main_loop(self):
        """Main trading loop that scans for opportunities and executes trades."""
        while self.is_running:
            try:
                # 1) Scan for new opportunities and add to shared resource
                if len(self.active_positions) < self.max_positions:
                    newly_discovered = await self.scanner.scan_all_assets(
                        assets_config=self.assets,
                        days_min=self.days_min,
                        days_max=self.days_max
                    )
                    
                    if newly_discovered:
                        logger.info(f"Scanner discovered {len(newly_discovered)} new opportunities")

                # 2) Check if we should execute a trade from shared opportunities
                if len(self.active_positions) < self.max_positions:
                    best_opportunity = shared_opportunities.get_best_opportunity()
                    
                    if best_opportunity:
                        logger.info(
                            "Selected opportunity from shared resource: %s | conditionId %s | symbol %s | "
                            "strike $%s | current NO $%s | %sd | token=%s",
                            best_opportunity.market_question,
                            best_opportunity.condition_id,
                            best_opportunity.binance_symbol,
                            best_opportunity.strike_price,
                            best_opportunity.current_no_price,
                            best_opportunity.days_to_expiry,
                            best_opportunity.no_token_id,
                        )
                        
                        await self.execute_hedge(best_opportunity)
                    else:
                        logger.debug("No suitable opportunities available for execution")
                
                await asyncio.sleep(15)  # 15 seconds between scans
                
            except asyncio.CancelledError:
                logger.info("Main loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(15)

    async def run(self):
        """Main entry point - start all components and run the bot."""
        self.is_running = True
        
        try:
            # Start all client sessions
            await self.binance.start_session()
            await self.gamma.start()

            # Initialize price feeds
            await self.initialize_price_feeds()

            # Start WebSocket manager for Polymarket real-time prices
            ws_task = asyncio.create_task(self.polymarket_ws.start())

            # Start position monitoring task
            monitor_task = asyncio.create_task(self.monitor_positions())

            # Run main trading loop
            main_loop_task = asyncio.create_task(self.run_main_loop())

            # Wait for tasks to complete
            await asyncio.gather(ws_task, monitor_task, main_loop_task, return_exceptions=True)
            
        except asyncio.CancelledError:
            logger.info("Bot shutting down.")
        finally:
            self.is_running = False
            
            # Stop WebSocket manager
            await self.polymarket_ws.stop()
            
            # Cancel monitoring task
            if 'monitor_task' in locals():
                monitor_task.cancel()
                await asyncio.gather(monitor_task, return_exceptions=True)
            
            # Close all sessions
            await self.gamma.close()
            await self.binance.close_session()
            logger.info("Sessions closed.")


# --- Main Execution ---

def main():
    """Main entry point with credential loading and bot initialization."""
    setup_logging()
    
    # Load configuration
    CONFIG = load_config()
    
    # Import credentials (you'll need to create this file)
    try:
        from src.connectors.credentials import credentials_dict, polymarket_credentials
        binance_account = 'account_1'
    except ImportError:
        logger.critical("CRITICAL: credentials.py file not found. Please create it with your API credentials.")
        raise SystemExit(1)

    # Allow environment variables to override CLOB credentials
    clob_creds_env = {k: os.getenv(k) for k in ['CLOB_API_KEY', 'CLOB_SECRET', 'CLOB_PASS_PHRASE']}
    if all(clob_creds_env.values()):
        polymarket_credentials['clob_api'] = clob_creds_env

    # Validate Polymarket credentials
    try:
        _priv = polymarket_credentials['private_key']
        _clob = polymarket_credentials['clob_api']
        if not _priv or not all(_clob.get(k) for k in ['CLOB_API_KEY', 'CLOB_SECRET', 'CLOB_PASS_PHRASE']):
            raise KeyError
    except Exception:
        logger.critical(
            "CRITICAL: Missing Polymarket credentials. Set POLYMARKET_PRIVATE_KEY, "
            "CLOB_API_KEY, CLOB_SECRET, CLOB_PASS_PHRASE in env or credentials.py."
        )
        raise SystemExit(1)

    # Initialize and run bot
    bot = PolymarketBinanceHedgingBot(
        config=CONFIG,
        binance_creds=credentials_dict[binance_account],
        polymarket_creds=polymarket_credentials
    )
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")


if __name__ == "__main__":
    main()