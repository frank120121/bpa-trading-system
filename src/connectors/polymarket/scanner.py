## polymarket/scanner.py

"""
Polymarket Scanner Module
Focuses purely on scanning markets and identifying trading opportunities.
"""

import asyncio
import aiohttp
import json
import re
from datetime import datetime, timezone as _tz
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)

# Helper functions
def _safe_json_list(x):
    """Decode a JSON-encoded list if it's a string; otherwise return as-is if list/tuple."""
    if isinstance(x, str):
        try:
            v = json.loads(x)
            if isinstance(v, (list, tuple)):
                return list(v)
        except Exception:
            return None
    elif isinstance(x, (list, tuple)):
        return list(x)
    return None


def _find_no_index(outcomes_list):
    """Return index of 'No' outcome in a list of outcomes; None if not found."""
    if not outcomes_list:
        return None
    for i, o in enumerate(outcomes_list):
        if str(o).strip().lower() in ("no", "n"):
            return i
    return None


def _parse_end_iso(end_iso: str) -> datetime:
    """
    Parse Gamma endDateIso / endDate into a timezone-aware UTC datetime.
    Accepts forms like '2025-10-01' or '2025-10-01T00:00:00Z'.
    """
    if not end_iso:
        raise ValueError("empty end_iso")
    s = end_iso.strip()
    if s.endswith('Z'):
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    if 'T' not in s:
        s = s + 'T00:00:00+00:00'
        return datetime.fromisoformat(s)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_tz.utc)
    return dt


class GammaClient:
    """Read-only Gamma Markets API for filtering markets by tags."""
    
    BASE = "https://gamma-api.polymarket.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def list_markets(self, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Fetch all crypto markets from Gamma API with pagination support."""
        if self.session is None:
            raise RuntimeError("GammaClient session not started.")
        
        url = f"{self.BASE}/markets"
        all_markets = []
        page = 1
        
        while True:
            params = {
                "tag_id": "102134",
                "limit": 100,
                "offset": (page - 1) * 100
            }
            
            page_success = False
            
            for attempt in range(max_retries):
                try:
                    async with self.session.get(url, params=params) as resp:
                        text = await resp.text()
                        if resp.status != 200:
                            logger.error(f"Gamma /markets error {resp.status}: {text[:200]}")
                            return all_markets
                        
                        try:
                            data = json.loads(text)
                            markets = data if isinstance(data, list) else data.get("data", [])
                            
                            if not markets:
                                return all_markets
                            
                            all_markets.extend(markets)
                            
                            if len(markets) < 100:
                                return all_markets
                            
                            page_success = True
                            break
                            
                        except Exception as e:
                            logger.error(f"Gamma /markets JSON parse failed: {e}")
                            return all_markets
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Gamma API timeout (attempt {attempt + 1}/{max_retries}) on page {page}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        logger.error(f"Gamma API timeout after all retries on page {page}")
                        return all_markets
                        
                except Exception as e:
                    logger.error(f"Gamma API error (attempt {attempt + 1}/{max_retries}) on page {page}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        return all_markets
            
            if not page_success:
                logger.error(f"Failed to get data from page {page} after all retries, stopping pagination")
                break
                
            page += 1
        
        assets_found = set()
        for market in all_markets:
            question = market.get("question", "").lower()
            if "bitcoin" in question or "btc" in question:
                assets_found.add("BTC")
            elif "ethereum" in question or "eth" in question:
                assets_found.add("ETH")
            elif "solana" in question or "sol" in question:
                assets_found.add("SOL")
            elif "xrp" in question or "ripple" in question:
                assets_found.add("XRP")
        
        return all_markets


class PolymarketPriceClient:
    """Lightweight client for fetching Polymarket prices only."""
    
    def __init__(self):
        self.host = "https://clob.polymarket.com"

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


class PolymarketScanner:
    """Scans Polymarket for opportunities across multiple assets using Gamma markets API."""

    def __init__(self, binance_client, gamma_client: GammaClient):
        self.binance = binance_client
        self.gamma = gamma_client
        self.price_client = PolymarketPriceClient()

    @staticmethod
    def _extract_strike(question: str) -> Optional[Decimal]:
        """Extract strike price from market question text."""
        m = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})+|\d+\.\d+|\d+)(\s*[kK])?', question or "")
        if not m:
            return None
        raw = m.group(1).replace(',', '')
        strike = Decimal(raw)
        if m.group(2):
            strike *= Decimal(1000)
        return strike

    def _matches_asset(self, question: str, keywords: List[str]) -> bool:
        """Check if question contains any of the asset keywords."""
        if not question:
            return False
        ql = question.lower()
        return any(k in ql for k in keywords)

    async def _resolve_no_token_and_price(self, m: Dict[str, Any]) -> Tuple[Optional[str], Optional[Decimal]]:
        """Try Gamma-provided fields first; fallback to CLOB /price."""
        clob_ids = _safe_json_list(m.get("clobTokenIds"))
        outcomes = _safe_json_list(m.get("outcomes") or m.get("shortOutcomes"))
        if not clob_ids or not outcomes or len(clob_ids) != len(outcomes):
            return None, None

        idx_no = _find_no_index(outcomes)
        if idx_no is None or idx_no >= len(clob_ids):
            return None, None

        no_token_id = str(clob_ids[idx_no]).strip()

        prices = _safe_json_list(m.get("outcomePrices"))
        if prices and len(prices) == len(outcomes):
            try:
                no_price = Decimal(str(prices[idx_no]))
                if no_price > 0:
                    return no_token_id, no_price
            except Exception:
                pass

        no_price = await self.price_client.get_price(no_token_id, side="BUY")
        return no_token_id, (no_price if (no_price and no_price > 0) else None)

    async def _gamma_no_token_fallback(self, m: Dict[str, Any]) -> Optional[str]:
        """Fallback method to find 'No' token ID from market data."""
        clob_ids_raw = m.get("clobTokenIds")
        outcomes_raw = m.get("outcomes") or m.get("shortOutcomes")
        if not clob_ids_raw or not outcomes_raw:
            return None
        
        try:
            clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        except Exception:
            clob_ids = clob_ids_raw
        try:
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except Exception:
            outcomes = outcomes_raw
            
        if not isinstance(clob_ids, (list, tuple)) or not isinstance(outcomes, (list, tuple)):
            return None
        if len(clob_ids) != len(outcomes) or len(clob_ids) == 0:
            return None
            
        idx_no = None
        for i, o in enumerate(outcomes):
            if str(o).strip().lower() in ("no", "n"):
                idx_no = i
                break
                
        if idx_no is None or not (0 <= idx_no < len(clob_ids)):
            return None
            
        candidate = str(clob_ids[idx_no]).strip()
        if not candidate:
            return None
            
        price = await self.price_client.get_price(candidate, side="BUY")
        return candidate if price is not None else None

    async def scan_all_assets(self, *, assets_config: List[Dict[str, Any]], 
                             days_min: int, days_max: int = None) -> List[Dict[str, Any]]:
        """
        Scan Polymarket for trading opportunities across all configured assets.
        Now adds opportunities to shared resource instead of returning them for immediate execution.
        
        Args:
            assets_config: List of asset configurations with keywords, symbols, etc.
            days_min: Minimum days to expiry for valid opportunities
            days_max: Maximum days to expiry (optional)
            
        Returns:
            List of opportunity dictionaries that were newly added to shared resource
        """
        from opportunities import shared_opportunities
        
        logger.info("Scanning Polymarket for opportunities across all assets...")

        gamma_markets = await self.gamma.list_markets()
        if not gamma_markets:
            logger.warning("Gamma returned 0 markets - API may be unavailable. Skipping this scan cycle.")
            return []

        tradable = self._filter_tradable_markets(gamma_markets)
        relevant_markets = self._match_markets_to_assets(tradable, assets_config)
        spot_prices = await self._get_spot_prices(assets_config)
        opportunities = await self._process_markets_to_opportunities(relevant_markets, spot_prices, days_min)

        newly_added = []
        for opp in opportunities:
            was_added = shared_opportunities.add_opportunity(opp)
            if was_added:
                newly_added.append(opp)

        if newly_added:
            logger.info(f"Added {len(newly_added)} new opportunities to shared resource")
        else:
            logger.info("No new opportunities found or all opportunities already exist")
        
        return newly_added

    def _filter_tradable_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter markets to only include those that are active and tradable."""
        tradable = []
        for m in markets:
            is_active = m.get("active") is True
            is_open = m.get("closed") is False  
            has_orderbook = m.get("enableOrderBook") is True
            accepts_orders = m.get("acceptingOrders") is True
            
            if is_active and is_open and has_orderbook and accepts_orders:
                tradable.append(m)
        
        return tradable

    def _match_markets_to_assets(self, markets: List[Dict[str, Any]], 
                                assets_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match markets to configured assets based on keywords."""
        keyword_to_asset = {}
        for asset_config in assets_config:
            for keyword in asset_config['keywords']:
                keyword_to_asset[keyword.lower()] = asset_config

        relevant_markets = []
        for market in markets:
            question = market.get("question", "") or ""
            
            matching_asset = None
            for keyword, asset_config in keyword_to_asset.items():
                if self._matches_asset(question, [keyword]):
                    matching_asset = asset_config
                    break
            
            if matching_asset:
                market['_asset_config'] = matching_asset
                relevant_markets.append(market)
        
        return relevant_markets

    async def _get_spot_prices(self, assets_config: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Get current spot prices for all configured assets."""
        spot_prices = {}
        for asset_config in assets_config:
            symbol = asset_config['binance_symbol']
            spot = self.binance.get_cached_price(symbol)
            if spot == 0:
                spot = await self.binance.get_current_price(symbol)
            spot_prices[symbol] = spot
            if spot == 0:
                logger.warning(f"Cannot get spot price for {symbol}")
        return spot_prices

    async def _process_markets_to_opportunities(self, 
                                              markets: List[Dict[str, Any]], 
                                              spot_prices: Dict[str, Decimal],
                                              days_min: int) -> List[Dict[str, Any]]:
        """Process filtered markets into valid trading opportunities."""
        opportunities = []

        for m in markets:
            asset_config = m['_asset_config']
            symbol = asset_config['binance_symbol']
            max_no_price = asset_config['max_no_price']
            spot = spot_prices.get(symbol, Decimal('0'))
            
            if spot == 0:
                logger.info(f"Exclude (no spot price): {m.get('question', '')}")
                continue

            q = m.get("question", "") or ""
            try:
                # Date validation - check multiple possible locations
                end_iso = m.get("endDateIso") or m.get("endDate")
                
                # If not found directly, check in events array
                if not end_iso:
                    events = m.get("events", [])
                    if events and isinstance(events, list) and len(events) > 0:
                        end_iso = events[0].get("endDate")
                
                if not end_iso:
                    logger.info(f"Exclude (no end date): {q}")
                    continue
                    
                expiry = _parse_end_iso(end_iso)
                days_to_expiry = (expiry - datetime.now(_tz.utc)).days
                
                if days_to_expiry >= 130:  
                    continue
                if days_to_expiry < days_min:
                    continue
                strike = self._extract_strike(q)
                if not strike:
                    continue

                no_token_id, best_price = await self._resolve_no_token_and_price(m)
                if not no_token_id:
                    no_token_id = await self._gamma_no_token_fallback(m)
                    if not no_token_id:
                        logger.info(f"Exclude (couldn't map NO token): {q}")
                        continue
                    best_price = await self.price_client.get_price(no_token_id, side="BUY")
                    if not best_price or best_price <= 0:
                        logger.info(f"Exclude (no valid NO buy price): {q}")
                        continue

                if best_price > max_no_price:
                    continue

                opportunities.append({
                    "market_question": q,
                    "conditionId": m.get("conditionId"),
                    "strike_price": strike,
                    "no_price": best_price,
                    "no_token_id": no_token_id,
                    "expiry": expiry,
                    "days_to_expiry": days_to_expiry,
                    "binance_symbol": symbol,
                    "_trade_amount": asset_config['trade_amount']
                })
                logger.info(f"Viable: {q} | strike ${strike} | NO ${best_price} | {days_to_expiry}d | token={no_token_id}")
                
            except Exception as e:
                logger.info(f"Skip market due to parse/validate error: {q} -> {e}")

        return opportunities

    def get_market_summary(self, opportunity: Dict[str, Any]) -> str:
        """Get a formatted summary of a market opportunity for logger."""
        return (
            f"Market: {opportunity['market_question'][:100]}... | "
            f"Strike: ${opportunity['strike_price']} | "
            f"NO Price: ${opportunity['no_price']} | "
            f"Days: {opportunity['days_to_expiry']} | "
            f"Symbol: {opportunity['binance_symbol']}"
        )