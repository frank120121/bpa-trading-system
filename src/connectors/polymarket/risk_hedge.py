## polymarket/risk_hedge.py

"""
Risk Analysis and Hedge Calculation Module
Contains both risk validation and hedge calculation logic.
"""

import pandas as pd
import pandas_ta as ta
from decimal import Decimal
from typing import Dict, Any
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)

class HedgeCalculator:
    """Stateless hedge math calculations."""
    
    TAKER_FEE_BPS = 25  # 0.25%

    @staticmethod
    def calculate_hedge(
        current_price: Decimal, 
        strike_price: Decimal, 
        no_share_price: Decimal, 
        base_amount: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate hedge parameters for a given opportunity.
        
        Args:
            current_price: Current spot price of the asset
            strike_price: Target strike price from the prediction market
            no_share_price: Price of 'No' shares on Polymarket
            base_amount: Amount of base asset to hedge
            
        Returns:
            Dictionary with hedge calculation results or empty dict if invalid
        """
        # Require the strike to be above current price (we're hedging "reach $X")
        if no_share_price <= 0 or current_price >= strike_price:
            logger.info(
                f"Invalid hedge calc params: current_price={current_price}, "
                f"strike_price={strike_price}, no_share_price={no_share_price}"
            ) 
            return {}

        upside_usd = (strike_price - current_price) * base_amount
        if upside_usd <= 0:
            logger.info(
                f"No upside to hedge: current_price={current_price}, "
                f"strike_price={strike_price}, base_amount={base_amount}"
            )
            return {}

        no_shares_needed = upside_usd / no_share_price
        cost_of_shares = no_shares_needed * no_share_price
        fee = cost_of_shares * (Decimal(HedgeCalculator.TAKER_FEE_BPS) / Decimal('10000'))
        total_cost = cost_of_shares + fee
        profit_if_no_hit = no_shares_needed - total_cost
        drop_allowance = profit_if_no_hit / base_amount if base_amount > 0 else Decimal('0')
        breakeven_price = current_price - drop_allowance
        risk_reward_ratio = profit_if_no_hit / total_cost if total_cost > 0 else Decimal('0')

        return {
            "no_shares_needed": no_shares_needed,
            "total_cost_usd": total_cost,
            "profit_if_no_hit": profit_if_no_hit,
            "breakeven_price": breakeven_price,
            "risk_reward_ratio": risk_reward_ratio
        }


class RiskAnalyzer:
    """
    Multi-timeframe risk analysis for hedge validation.
    
    Uses technical analysis across multiple timeframes:
      - Daily: EMA20, EMA50, BB Lower(20,2)
      - Weekly: EMA21
      - Monthly: Pivot S1 (from previous month)
      - ATR(30d) cushion on Daily

    Pass rule:
      breakeven must be below at least `min_support_hits` of the computed supports
      AND breakeven < (spot - ATR(30) * atr_mult)
    """

    def __init__(self, binance_client, config):
        self.binance = binance_client
        self.config = config

    async def _get_klines_df(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """Convert Binance klines to pandas DataFrame with proper column types."""
        kl = await self.binance.get_klines(symbol, interval=interval, limit=limit)
        if not kl:
            return pd.DataFrame()
        
        df = pd.DataFrame(kl, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        for c in ('open', 'high', 'low', 'close', 'volume'):
            df[c] = pd.to_numeric(df[c])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        
        return df

    async def get_supports_and_atr(self, symbol: str) -> Dict[str, Decimal]:
        """
        Calculate support levels and ATR for risk analysis.
        
        Returns:
          {
            'EMA20_D': Decimal,
            'EMA50_D': Decimal,
            'BBL20_D': Decimal,
            'EMA21_W': Decimal,
            'M_pivot_S1': Decimal,
            'ATR30_D': Decimal
          }
        """
        # Fetch data for different timeframes
        d = await self._get_klines_df(symbol, '1d', 200)
        w = await self._get_klines_df(symbol, '1w', 120)
        m = await self._get_klines_df(symbol, '1M', 36)

        out: Dict[str, Decimal] = {}

        # Daily indicators
        if not d.empty:
            d.ta.ema(length=20, append=True)
            d.ta.ema(length=50, append=True)
            d.ta.bbands(length=20, append=True)
            d.ta.atr(length=30, append=True)

            last = d.iloc[-1]
            
            # Extract indicator values
            if pd.notna(last.get('EMA_20')):
                out['EMA20_D'] = Decimal(str(last['EMA_20']))
            if pd.notna(last.get('EMA_50')):
                out['EMA50_D'] = Decimal(str(last['EMA_50']))
            if pd.notna(last.get('BBL_20_2.0')):
                out['BBL20_D'] = Decimal(str(last['BBL_20_2.0']))

            # Robust ATR30 column detection (supports pandas_ta variants)
            atr_col = next(
                (c for c in d.columns if c.upper().startswith('ATR') and c.endswith('_30')), 
                None
            )
            if atr_col and pd.notna(last.get(atr_col)):
                out['ATR30_D'] = Decimal(str(last[atr_col]))

        # Weekly indicators
        if not w.empty:
            w.ta.ema(length=21, append=True)
            lastw = w.iloc[-1]
            if pd.notna(lastw.get('EMA_21')):
                out['EMA21_W'] = Decimal(str(lastw['EMA_21']))

        # Monthly pivot points
        if not m.empty and len(m) >= 2:
            prev = m.iloc[-2]  # Previous month's data
            if all(pd.notna(prev.get(col)) for col in ['high', 'low', 'close']):
                H = Decimal(str(prev['high']))
                L = Decimal(str(prev['low']))
                C = Decimal(str(prev['close']))
                pp = (H + L + C) / Decimal('3')
                s1 = (Decimal('2') * pp) - H
                out['M_pivot_S1'] = s1

        return out

    async def validate_opportunity(self, breakeven_price: Decimal, symbol: str) -> bool:
        """
        Validate whether an opportunity passes risk analysis.
        
        Args:
            breakeven_price: Calculated breakeven price for the hedge
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            True if opportunity passes risk validation, False otherwise
        """
        supports = await self.get_supports_and_atr(symbol)
        if not supports:
            logger.warning("RiskAnalyzer: no TA data available; skipping validation.")
            return False

        # Proximal support basket (5 items)
        candidate_keys = ['EMA20_D', 'EMA50_D', 'BBL20_D', 'EMA21_W', 'M_pivot_S1']
        levels = [
            (k, supports[k]) for k in candidate_keys 
            if k in supports and supports[k] > 0
        ]
        
        if not levels:
            logger.warning("RiskAnalyzer: no valid support levels; skipping validation.")
            return False

        # PASS if breakeven is BELOW the support level
        hits = [(k, float(breakeven_price) < float(v)) for k, v in levels]
        hits_count = sum(1 for _, ok in hits if ok)

        # Get configuration parameters
        try:
            min_hits = int(self.config.get('risk_management', 'min_support_hits', fallback='3'))
        except Exception:
            min_hits = 3

        # ATR-based validation
        atr = supports.get('ATR30_D', Decimal('0'))
        try:
            atr_mult = Decimal(self.config.get('risk_management', 'atr_multiplier', fallback='1.0'))
        except Exception:
            atr_mult = Decimal('1.0')

        spot = self.binance.get_cached_price(symbol)
        if spot == 0:
            spot = await self.binance.get_current_price(symbol)

        atr_barrier = spot - atr * atr_mult if atr > 0 else None
        atr_ok = (atr_barrier is None) or (breakeven_price < atr_barrier)

        # Log detailed analysis
        details = ", ".join(
            f"{k}:{'PASS' if ok else 'FAIL'}(lvl={float(dict(levels)[k]):.6f})" 
            for k, ok in hits
        )
        
        logger.info(
            "Risk Analysis (majority rule): breakeven=%.6f | hits=%d/%d (need %d) | "
            "ATR30=%.6f mult=%s barrier=%s -> atr_ok=%s | Details: %s",
            float(breakeven_price), hits_count, len(levels), min_hits,
            float(atr or 0), str(atr_mult),
            f"{float(atr_barrier):.6f}" if atr_barrier is not None else "N/A",
            atr_ok, details
        )

        # Final validation
        if hits_count >= min_hits and atr_ok:
            logger.info("Validation PASSED (majority supports + ATR).")
            return True

        logger.warning(
            "Validation FAILED: supports hits %d/%d (need %d), atr_ok=%s",
            hits_count, len(levels), min_hits, atr_ok
        )
        return False

    def get_support_summary(self, supports: Dict[str, Decimal]) -> str:
        """Get a formatted summary of support levels for logger."""
        if not supports:
            return "No support data available"
        
        summary_parts = []
        for key, value in supports.items():
            summary_parts.append(f"{key}: ${float(value):.6f}")
        
        return " | ".join(summary_parts)