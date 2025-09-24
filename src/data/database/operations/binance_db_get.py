# bpa/binance_db_get.py
from datetime import datetime
import aiosqlite
from typing import Optional

from src.utils.common_vars import BBVA_BANKS
from src.data.database.connection import DB_FILE
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)


# Helper functions for existence checks
async def user_exists(conn, user_name):
    """Check if a user exists in the database"""
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT name FROM users WHERE name = ?", (user_name,))
        row = await cursor.fetchone()
        return bool(row)

async def order_exists(conn, orderNumber):
    """Check if an order exists in the database"""
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT orderNumber FROM orders WHERE orderNumber = ?", (orderNumber,))
        row = await cursor.fetchone()
        return bool(row)

async def get_order_details(conn, orderNumber):
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM orders WHERE orderNumber=?", (orderNumber,))
            row = await cursor.fetchone()
            if row:
                column_names = [desc[0] for desc in cursor.description]
                return {column_names[i]: row[i] for i in range(len(row))}
            else:
                return None
    except Exception as e:
        logger.error(f"An error occurred in get_order_details: {e}")
        return None

async def fetch_merchant_credentials(merchant_id):
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            async with conn.execute("SELECT api_key, api_secret FROM merchants WHERE id = ?", (merchant_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'KEY': row[0],
                        'SECRET': row[1]
                    }
                else:
                    logger.warning(f"Merchant with ID {merchant_id} not found")
                    return None
    except Exception as e:
        logger.error(f"Error fetching merchant credentials for ID {merchant_id}: {e}")
        return None

async def calculate_crypto_sold_30d(conn, buyerName):
    try:
        if not await user_exists(conn, buyerName):
            logger.warning(f"User {buyerName} does not exist")
            return 0
            
        sql = """
            SELECT SUM(amount)
            FROM orders
            WHERE buyerName = ? 
                AND orderStatus = 4
                AND order_date >= datetime('now', '-30 day')
        """
        params = (buyerName,)
        total_crypto_sold_30d = await execute_and_fetchone(conn, sql, params)
        return total_crypto_sold_30d[0] if total_crypto_sold_30d and total_crypto_sold_30d[0] else 0
    except Exception as e:
        logger.error(f"Error calculating crypto sold in the last 30 days for {buyerName}: {e}")
        return 0

async def get_kyc_status(conn, name):
    try:
        if not await user_exists(conn, name):
            logger.warning(f"User {name} does not exist when checking KYC status")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT kyc_status FROM users WHERE name=?", (name,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting KYC status for user {name}: {e}")
        return None

async def get_anti_fraud_stage(conn, name):
    try:
        if not await user_exists(conn, name):
            logger.warning(f"User {name} does not exist when checking anti-fraud stage")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT anti_fraud_stage FROM users WHERE name=?", (name,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting anti-fraud stage for user {name}: {e}")
        return None

async def get_returning_customer_stage(conn, orderNumber):
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when getting returning customer stage")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT returning_customer_stage FROM orders WHERE orderNumber=?", (orderNumber,))
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
    except Exception as e:
        logger.error(f"Error getting returning customer stage for order {orderNumber}: {e}")
        return None

async def is_menu_presented(conn, orderNumber):
    """
    Checks if the menu has been presented for a specific order.

    Args:
    - conn (sqlite3.Connection): SQLite database connection.
    - orderNumber (str): The order number to check.

    Returns:
    - bool: True if the menu has been presented, False otherwise.
    - None: If order doesn't exist
    """
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when checking menu_presented")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT menu_presented
                FROM orders
                WHERE orderNumber = ?;
            """, (orderNumber,))
        
            result = await cursor.fetchone()
            return result[0] == 1 if result else False
    except Exception as e:
        logger.error(f"Error checking if menu presented for order {orderNumber}: {e}")
        return None

async def execute_and_fetchone(conn, sql, params=None):
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            return await cursor.fetchone()
    except Exception as e:
        logger.error(f"Error executing query: {sql} with params {params}: {e}")
        return None

async def get_buyer_bank(conn, buyerName):
    try:
        if not await user_exists(conn, buyerName):
            logger.warning(f"User {buyerName} does not exist when getting buyer bank")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT user_bank FROM users WHERE name=?", (buyerName,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting buyer bank for user {buyerName}: {e}")
        return None

async def get_account_number(conn, orderNumber):
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when getting account number")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT account_number FROM orders WHERE orderNumber=?", (orderNumber,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting account number for order {orderNumber}: {e}")
        return None

async def get_order_amount(conn, orderNumber):
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when getting order amount")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT totalPrice FROM orders WHERE orderNumber=?", (orderNumber,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting order amount for order {orderNumber}: {e}")
        return None

async def get_buyer_name(conn, orderNumber):
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when getting buyer name")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT buyerName FROM orders WHERE orderNumber=?", (orderNumber,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting buyer name for order {orderNumber}: {e}")
        return None

async def has_specific_pay_type(conn, orderNumber: str, payment_types: list[str]) -> bool:
    """
    Check if an order's payment type matches any of the specified types.
    
    Args:
        conn: Database connection
        orderNumber: Order number to check
        payment_types: List of payment types to check against
        
    Returns:
        True if the order's payType is in the payment_types list, False otherwise
        None if order doesn't exist
    """
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when checking payment type")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT payType FROM orders WHERE orderNumber = ?",
                (orderNumber,)
            )
            result = await cursor.fetchone()
            
            if not result or not result[0]:
                logger.debug(f"No payment type found for order {orderNumber}")
                return False
            
            payType = result[0]
            is_match = payType in payment_types
            
            logger.debug(
                f"Order {orderNumber} payment type: '{payType}' "
                f"(checking for {payment_types}) - Match: {is_match}"
            )
            
            return is_match
            
    except Exception as e:
        logger.error(f"Error checking payment type for order {orderNumber}: {e}")
        return None

async def get_user_language_preference(conn, buyerName: str) -> Optional[str]:
    """Get user's language preference from database."""
    try:
        if not await user_exists(conn, buyerName):
            logger.warning(f"User {buyerName} does not exist when getting language preference")
            return None
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT language_preference FROM users WHERE name = ?", (buyerName,))
            result = await cursor.fetchone()
            return result[0] if result and result[0] else None
        
    except Exception as e:
        logger.error(f"Error getting language preference for {buyerName}: {str(e)}")
        return None

async def get_language_selection_stage(conn, buyerName: str) -> Optional[int]:
    """Get user's language selection stage from database."""
    try:
        if not await user_exists(conn, buyerName):
            logger.warning(f"User {buyerName} does not exist when getting language selection stage")
            return 0  # Default stage for non-existent users
            
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT language_selection_stage FROM users WHERE name = ?", (buyerName,))
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        
    except Exception as e:
        logger.error(f"Error getting language selection stage for {buyerName}: {str(e)}")
        return 0

async def get_order_pay_type(conn, orderNumber: str) -> str:
    """Get payment method for an order."""
    try:
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Order {orderNumber} does not exist when getting payment type")
            return ""
            
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT payType FROM orders WHERE orderNumber = ?", 
                (orderNumber,)
            )
            result = await cursor.fetchone()
            return result[0] if result and result[0] else ""
    except Exception as e:
        logger.error(f"Error fetching payment method for order {orderNumber}: {e}")
        return ""

async def get_test_orders_from_db():
    """
    Fetch orders from database without depending on screenshot flags
    """
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            async with conn.cursor() as cursor:
                bbva_variations = ', '.join(f"'{bank}'" for bank in BBVA_BANKS)
                
                query = f"""
                SELECT 
                    o.orderNumber,
                    o.order_date,
                    o.totalPrice,
                    o.account_number,
                    o.payment_image_url,
                    o.clave_de_rastreo,
                    u.user_bank
                FROM orders o
                JOIN users u ON o.buyerName = u.name
                WHERE o.sellerName = 'GUERRERO LOPEZ MARTHA'
                AND LOWER(u.user_bank) IN ({bbva_variations})
                AND o.orderStatus = 4
                AND o.order_date <= '2024-10-25'
                ORDER BY o.order_date DESC
                LIMIT 10  -- Start with 10 most recent orders
                """
                
                await cursor.execute(query)
                rows = await cursor.fetchall()
                
                order_details = {}
                skipped_count = 0
                existing_clave_count = 0
                for row in rows:
                    orderNumber, order_date, amount, account_number, payment_image_url, existing_clave, user_bank = row
                    
                    # Skip if we already have a clave
                    if existing_clave:
                        existing_clave_count += 1
                        continue
                        
                    # Convert order_date string to datetime object
                    if isinstance(order_date, str):
                        try:
                            date_obj = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            logger.error(f"Invalid date format for order {orderNumber}: {order_date}")
                            continue
                    else:
                        date_obj = order_date
                    
                    order_details[orderNumber] = {
                        'fecha': date_obj.date(),
                        'emisor': '40012',  # BBVA MEXICO
                        'receptor': '90710',  # NVIO
                        'cuenta': account_number,
                        'monto': float(amount),
                        'bank': 'BBVA',
                        'payment_image_url': payment_image_url,
                        'existing_clave': existing_clave,
                        'user_bank': user_bank
                    }
                
                logger.info(f"Database Query Summary:")
                logger.info(f"  Total rows found: {len(rows)}")
                logger.info(f"  Orders with existing claves (skipped): {existing_clave_count}")
                logger.info(f"  Orders to process: {len(order_details)}")
                
                if order_details:
                    logger.info("\nOrders to be processed:")
                    for orderNumber, details in order_details.items():
                        logger.info(
                            f"Order: {orderNumber}\n"
                            f"  Date: {details['fecha']}\n"
                            f"  Amount: {details['monto']}\n"
                            f"  Account: {details['cuenta']}\n"
                            f"  User Bank: {details['user_bank']}"
                        )
                return order_details
                
    except Exception as e:
        logger.error(f"Database error in get_test_orders_from_db: {e}")
        return {}