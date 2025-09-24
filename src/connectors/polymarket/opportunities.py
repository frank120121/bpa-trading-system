# polymarket/opportunities.py

"""
Shared Opportunities Resource
Thread-safe storage for market opportunities that can be accessed by multiple components.
"""

import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Set
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class OpportunityData:
    """Represents a single market opportunity with metadata."""
    
    def __init__(self, market_question: str, condition_id: str, no_token_id: str, 
                 strike_price: Decimal, binance_symbol: str, days_to_expiry: int,
                 trade_amount: Decimal, expiry: datetime):
        self.market_question = market_question
        self.condition_id = condition_id
        self.no_token_id = no_token_id
        self.strike_price = strike_price
        self.binance_symbol = binance_symbol
        self.days_to_expiry = days_to_expiry
        self.trade_amount = trade_amount
        self.expiry = expiry
        self.added_at = datetime.now(timezone.utc)
        
        # Price tracking
        self.current_no_price = Decimal('0')
        self.last_price_update = None
        self.is_subscribed = False
        
        # Status tracking
        self.active = True
            
    def update_price(self, no_token_id: str, new_price: Decimal) -> bool:
        """Update the current price for a NO token."""
        with self._lock:
            logger.info(f"DEBUG: Attempting to update price for token {no_token_id}: ${new_price}")
            opp = self.get_opportunity_by_token(no_token_id)
            if opp:
                logger.info(f"DEBUG: Found opportunity for token, updating price from {opp.current_no_price} to {new_price}")
                opp.update_price(new_price)
                logger.info(f"DEBUG: Updated price for {no_token_id}: ${new_price}")
                return True
            else:
                logger.warning(f"DEBUG: No opportunity found for token {no_token_id}")
                return False
        
    def should_unsubscribe(self) -> bool:
        """Check if this opportunity should be unsubscribed based on price thresholds."""
        return (self.current_no_price <= Decimal('0') or 
                self.current_no_price >= Decimal('0.3'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            'market_question': self.market_question,
            'condition_id': self.condition_id,
            'no_token_id': self.no_token_id,
            'strike_price': float(self.strike_price),
            'binance_symbol': self.binance_symbol,
            'days_to_expiry': self.days_to_expiry,
            'trade_amount': float(self.trade_amount),
            'current_no_price': float(self.current_no_price),
            'is_subscribed': self.is_subscribed,
            'active': self.active,
            'added_at': self.added_at.isoformat(),
            'last_price_update': self.last_price_update.isoformat() if self.last_price_update else None
        }


class SharedOpportunities:
    """
    Thread-safe container for managing market opportunities across components.
    
    This class serves as a shared resource between:
    - Scanner: Adds new opportunities
    - WebSocket Manager: Subscribes to price feeds
    - Risk/Hedge Analysis: Reads current prices
    - Main Bot: Selects opportunities for execution
    """
    
    def __init__(self):
        self._opportunities: Dict[str, OpportunityData] = {}  # condition_id -> OpportunityData
        self._token_to_condition: Dict[str, str] = {}  # no_token_id -> condition_id
        self._lock = threading.RLock()
        self._subscribers: Set[str] = set()  # Track which condition_ids are subscribed
        
    def add_opportunity(self, opportunity_dict: Dict[str, Any]) -> bool:
        """
        Add a new opportunity to the shared resource.
        
        Args:
            opportunity_dict: Dictionary from scanner with market details
            
        Returns:
            True if added (new), False if already exists
        """
        condition_id = opportunity_dict.get('conditionId')
        if not condition_id:
            logger.warning("Cannot add opportunity without conditionId")
            return False
            
        with self._lock:
            if condition_id in self._opportunities:
                # Update existing opportunity with latest scan data
                existing = self._opportunities[condition_id]
                existing.days_to_expiry = opportunity_dict['days_to_expiry']
                existing.active = True  # Refresh active status
                logger.debug(f"Updated existing opportunity: {condition_id}")
                return False
            
            # Create new opportunity
            try:
                opp_data = OpportunityData(
                    market_question=opportunity_dict['market_question'],
                    condition_id=condition_id,
                    no_token_id=opportunity_dict['no_token_id'],
                    strike_price=opportunity_dict['strike_price'],
                    binance_symbol=opportunity_dict['binance_symbol'],
                    days_to_expiry=opportunity_dict['days_to_expiry'],
                    trade_amount=opportunity_dict['_trade_amount'],
                    expiry=opportunity_dict['expiry']
                )
                
                self._opportunities[condition_id] = opp_data
                self._token_to_condition[opportunity_dict['no_token_id']] = condition_id
                
                logger.info(f"Added new opportunity: {condition_id} | {opportunity_dict['market_question'][:100]}...")
                return True
                
            except KeyError as e:
                logger.error(f"Missing required field in opportunity_dict: {e}")
                return False
    
    def remove_opportunity(self, condition_id: str) -> bool:
        """Remove an opportunity from the shared resource."""
        with self._lock:
            if condition_id not in self._opportunities:
                return False
                
            opp = self._opportunities[condition_id]
            
            # Clean up mappings
            if opp.no_token_id in self._token_to_condition:
                del self._token_to_condition[opp.no_token_id]
            
            del self._opportunities[condition_id]
            
            # Remove from subscribers
            self._subscribers.discard(condition_id)
            
            logger.info(f"Removed opportunity: {condition_id} | {opp.market_question[:100]}...")
            return True
    
    def get_opportunity(self, condition_id: str) -> Optional[OpportunityData]:
        """Get a specific opportunity by condition ID."""
        with self._lock:
            return self._opportunities.get(condition_id)
    
    def get_opportunity_by_token(self, no_token_id: str) -> Optional[OpportunityData]:
        """Get opportunity by NO token ID."""
        with self._lock:
            condition_id = self._token_to_condition.get(no_token_id)
            if condition_id:
                return self._opportunities.get(condition_id)
            return None
    
    def get_all_opportunities(self) -> List[OpportunityData]:
        """Get all active opportunities."""
        with self._lock:
            return [opp for opp in self._opportunities.values() if opp.active]
    
    def get_unsubscribed_opportunities(self) -> List[OpportunityData]:
        """Get opportunities that need WebSocket subscription."""
        with self._lock:
            return [
                opp for opp in self._opportunities.values() 
                if opp.active and not opp.is_subscribed
            ]
    
    def mark_subscribed(self, condition_id: str) -> bool:
        """Mark an opportunity as having an active WebSocket subscription."""
        with self._lock:
            if condition_id in self._opportunities:
                self._opportunities[condition_id].is_subscribed = True
                self._subscribers.add(condition_id)
                return True
            return False
    
    def mark_unsubscribed(self, condition_id: str) -> bool:
        """Mark an opportunity as no longer having a WebSocket subscription."""
        with self._lock:
            if condition_id in self._opportunities:
                self._opportunities[condition_id].is_subscribed = False
                self._subscribers.discard(condition_id)
                return True
            return False
    
    def update_price(self, no_token_id: str, new_price: Decimal) -> bool:
        """
        Update the current price for a NO token.
        
        Returns True if price was updated, False if token not found.
        """
        with self._lock:
            opp = self.get_opportunity_by_token(no_token_id)
            if opp:
                opp.update_price(new_price)
                logger.debug(f"Updated price for {no_token_id}: ${new_price}")
                return True
            return False
    
    def get_current_price(self, no_token_id: str) -> Optional[Decimal]:
        """Get the current cached price for a NO token."""
        with self._lock:
            opp = self.get_opportunity_by_token(no_token_id)
            return opp.current_no_price if opp else None
    
    def get_opportunities_to_unsubscribe(self) -> List[OpportunityData]:
        """Get opportunities that should be unsubscribed based on price thresholds."""
        with self._lock:
            return [
                opp for opp in self._opportunities.values()
                if opp.is_subscribed and opp.should_unsubscribe()
            ]
    
    def cleanup_expired(self) -> int:
        """Remove opportunities that have expired. Returns count of removed items."""
        current_time = datetime.now(timezone.utc)
        expired_conditions = []
        
        with self._lock:
            for condition_id, opp in self._opportunities.items():
                if opp.expiry <= current_time:
                    expired_conditions.append(condition_id)
        
        # Remove expired opportunities
        for condition_id in expired_conditions:
            self.remove_opportunity(condition_id)
        
        if expired_conditions:
            logger.info(f"Cleaned up {len(expired_conditions)} expired opportunities")
        
        return len(expired_conditions)
    
    def get_best_opportunity(self) -> Optional[OpportunityData]:
        """
        Get the best opportunity based on current prices and criteria.
        
        Selection criteria:
        1. Must have a current price from WebSocket
        2. Price must be within valid range (> 0 and < 0.3)
        3. Prefer cheapest NO price
        4. Tie-breaker: closest strike above spot (requires binance client)
        """
        with self._lock:
            viable_opportunities = [
                opp for opp in self._opportunities.values()
                if (opp.active and 
                    opp.current_no_price > Decimal('0') and 
                    opp.current_no_price < Decimal('0.3') and
                    opp.last_price_update is not None)
            ]
            
            if not viable_opportunities:
                return None
            
            # Sort by NO price (cheapest first)
            viable_opportunities.sort(key=lambda x: x.current_no_price)
            
            return viable_opportunities[0]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the shared opportunities resource."""
        with self._lock:
            total = len(self._opportunities)
            active = sum(1 for opp in self._opportunities.values() if opp.active)
            subscribed = sum(1 for opp in self._opportunities.values() if opp.is_subscribed)
            with_prices = sum(1 for opp in self._opportunities.values() 
                            if opp.current_no_price > Decimal('0'))
            
            return {
                'total_opportunities': total,
                'active_opportunities': active,
                'subscribed_opportunities': subscribed,
                'opportunities_with_prices': with_prices,
                'unique_tokens': len(self._token_to_condition),
                'subscriber_count': len(self._subscribers)
            }
    
    def log_status(self):
        """Log current status of the shared opportunities resource."""
        stats = self.get_statistics()
        logger.info(
            f"Shared Opportunities Status: "
            f"Total={stats['total_opportunities']}, "
            f"Active={stats['active_opportunities']}, "
            f"Subscribed={stats['subscribed_opportunities']}, "
            f"WithPrices={stats['opportunities_with_prices']}"
        )


# Global shared instance
shared_opportunities = SharedOpportunities()