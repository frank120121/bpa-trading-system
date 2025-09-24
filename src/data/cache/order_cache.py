# bpa/binance_order_cache.py
import asyncio
from typing import Dict, Any, Optional

from src.data.cache.async_dict import AsyncSafeDict
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class OrderCache:
    _orders_dict = AsyncSafeDict()
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_order(cls, orderNumber: str) -> Optional[Dict[str, Any]]:
        """Get order from cache."""
        async with cls._lock:
            order = await cls._orders_dict.get(orderNumber)
            if order:
                logger.debug(f"Order {orderNumber} retrieved from cache")
            else:
                logger.debug(f"Order {orderNumber} not found in cache")
            return order
    
    @classmethod
    async def set_order(cls, orderNumber: str, order_data: Dict[str, Any]) -> bool:
        """Add or update order in cache."""
        try:
            async with cls._lock:
                await cls._orders_dict.put(orderNumber, order_data)
                logger.debug(f"Order {orderNumber} cached with data: {order_data}")
            return True
        except Exception as e:
            logger.error(f"Error caching order {orderNumber}: {e}")
            return False
    
    @classmethod
    async def update_fields(cls, orderNumber: str, fields: Dict[str, Any]) -> bool:
        """Update specific fields of cached order."""
        async with cls._lock:
            order_data = await cls._orders_dict.get(orderNumber)
            if order_data is not None:
                order_data.update(fields)
                await cls._orders_dict.put(orderNumber, order_data)
                logger.debug(f"Updated order {orderNumber} with fields: {fields}")
                return True
            else:
                logger.warning(f"Order {orderNumber} not found in cache for update")
                return False
    
    @classmethod
    async def sync_to_db(cls, conn, orderNumber: str) -> bool:
        """Sync all cached order changes to database."""
        async with cls._lock:
            order_data = await cls._orders_dict.get(orderNumber)
            if not order_data:
                logger.warning(f"Order {orderNumber} not found in cache for sync")
                return False
            
            try:
                # Import all necessary update functions
                from data.database.operations.binance_db_set import (
                    update_anti_fraud_stage, 
                    update_buyer_bank,
                    update_kyc_status,
                    update_order_details,
                    update_order_status
                )
                
                # Handle anti-fraud stage updates using new field names
                if 'anti_fraud_stage' in order_data:
                    buyerName = order_data.get('buyerName')
                    if buyerName:
                        await update_anti_fraud_stage(
                            conn, 
                            buyerName, 
                            order_data.get('anti_fraud_stage')
                        )
                
                # Handle buyer bank updates using new field names
                if 'buyer_bank' in order_data:
                    buyerName = order_data.get('buyerName')
                    if buyerName:
                        await update_buyer_bank(
                            conn,
                            buyerName,
                            order_data.get('buyer_bank')
                        )
                
                # Handle KYC status updates using new field names
                if 'kyc_status' in order_data:
                    buyerName = order_data.get('buyerName')
                    if buyerName:
                        await update_kyc_status(
                            conn,
                            buyerName,
                            order_data.get('kyc_status')
                        )
                
                # Handle order status updates using new field names
                if 'orderStatus' in order_data:
                    await update_order_status(
                        conn,
                        orderNumber,
                        order_data.get('orderStatus')
                    )
                
                # Handle order details updates using new field names
                if 'account_number' in order_data and 'seller_bank' in order_data:
                    await update_order_details(
                        conn,
                        orderNumber,
                        order_data.get('account_number'),
                        order_data.get('seller_bank')
                    )
                
                logger.debug(f"Synced order {orderNumber} to database")
                return True
                
            except Exception as e:
                logger.error(f"Error syncing order {orderNumber} to database: {e}")
                return False
    
    @classmethod
    async def remove_order(cls, orderNumber: str) -> None:
        """Remove order from cache (e.g., when order is completed)."""
        async with cls._lock:
            order_data = await cls._orders_dict.get(orderNumber)
            if order_data:
                # Create a new dict without the order
                all_items = await cls._orders_dict.items()
                new_dict = {k: v for k, v in all_items if k != orderNumber}
                cls._orders_dict._dict = new_dict
                logger.debug(f"Removed order {orderNumber} from cache")
    
    @classmethod
    async def clear_old_orders(cls, max_age_minutes: int = 60) -> None:
        """Clear orders older than specified age (implement if needed)."""
        pass