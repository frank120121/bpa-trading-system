# bpa/binance_db_set.py
import aiosqlite
from typing import Any, Dict, Union

from src.data.cache.share_data import SharedData
from src.data.database.connection import execute_and_commit
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)


# Helper functions for existence checks and upserts
async def order_exists(conn, orderNumber):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM orders WHERE orderNumber = ?", (orderNumber,))
        row = await cursor.fetchone()
        return bool(row)

async def user_exists(conn, user_name):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT name FROM users WHERE name = ?", (user_name,))
        row = await cursor.fetchone()
        return bool(row)

async def find_or_insert_buyer(conn, buyerName):
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT OR IGNORE INTO users 
            (name, kyc_status, total_crypto_sold_lifetime, anti_fraud_stage,
             usd_verification_stage, language_preference, language_selection_stage) 
            VALUES (?, 0, 0.0, 0, 0, NULL, 0)
            """, 
            (buyerName,)
        )
        await cursor.execute(
            "SELECT rowid FROM users WHERE name = ?", 
            (buyerName,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def find_or_insert_order(conn, orderNumber, buyerName=None, sellerName=None):
    """Ensure an order exists, creating a minimal record if it doesn't"""
    if await order_exists(conn, orderNumber):
        return True
    
    if not buyerName or not sellerName:
        logger.warning(f"Cannot create order {orderNumber} without buyerName and sellerName")
        return False
    
    # Ensure buyer exists
    await find_or_insert_buyer(conn, buyerName)
    
    # Create minimal order record
    try:
        sql = """
            INSERT INTO orders (
                orderNumber, buyerName, sellerName, tradeType, orderStatus, 
                totalPrice, fiatUnit, asset, amount, order_date
            ) VALUES (
                ?, ?, ?, 'BUY', 0, 0.0, 'MXN', 'USDT', 0.0, datetime('now', 'localtime')
            )
        """
        await execute_and_commit(conn, sql, (orderNumber, buyerName, sellerName))
        return True
    except Exception as e:
        logger.error(f"Error creating minimal order {orderNumber}: {e}")
        return False

async def insert_or_update_order(conn, order_details):
    try:
        data = order_details.get('data', {})

        # Extract all fields from API response with exact field names
        orderNumber = data.get('orderNumber', '')
        advOrderNumber = data.get('advOrderNumber', '')
        buyerName = data.get('buyerName', '')
        buyerNickname = data.get('buyerNickname', '')
        buyerMobilePhone = data.get('buyerMobilePhone', '')
        sellerName = data.get('sellerName', '')
        sellerNickname = data.get('sellerNickname', '')
        sellerMobilePhone = data.get('sellerMobilePhone', '')
        tradeType = data.get('tradeType', '')
        orderStatus = data.get('orderStatus', None)
        totalPrice = float(data.get('totalPrice', 0)) if data.get('totalPrice') else 0.0
        price = float(data.get('price', 0)) if data.get('price') else 0.0
        fiatUnit = data.get('fiatUnit', '')
        fiatSymbol = data.get('fiatSymbol', '')
        asset = data.get('asset', '')
        amount = float(data.get('amount', 0)) if data.get('amount') else 0.0
        payType = data.get('payType', '')
        selectedPayId = data.get('selectedPayId', None)
        currencyRate = float(data.get('currencyRate', 0)) if data.get('currencyRate') else 0.0
        createTime = data.get('createTime', None)
        notifyPayTime = data.get('notifyPayTime', None)
        confirmPayTime = data.get('confirmPayTime', None)
        notifyPayEndTime = data.get('notifyPayEndTime', None)
        confirmPayEndTime = data.get('confirmPayEndTime', None)
        remark = data.get('remark', '')
        merchantNo = data.get('merchantNo', '')
        takerUserNo = data.get('takerUserNo', '')
        commission = float(data.get('commission', 0)) if data.get('commission') else 0.0
        commissionRate = float(data.get('commissionRate', 0)) if data.get('commissionRate') else 0.0
        takerCommission = float(data.get('takerCommission', 0)) if data.get('takerCommission') else 0.0
        takerCommissionRate = float(data.get('takerCommissionRate', 0)) if data.get('takerCommissionRate') else 0.0
        takerAmount = float(data.get('takerAmount', 0)) if data.get('takerAmount') else 0.0

        # Validate required fields
        if not all([orderNumber, tradeType]):
            logger.error("Required fields (orderNumber, tradeType) are missing. Aborting operation.")
            return
        
        # Fetch priceFloatingRatio from SharedData using advOrderNumber
        ad_details = await SharedData.get_ad(advOrderNumber)
        if ad_details:
            priceFloatingRatio = float(ad_details.get('floating_ratio', '0.0'))
        else:
            logger.warning(f"Ad details for advOrderNumber {advOrderNumber} not found in SharedData.")
            priceFloatingRatio = 0.0
        
        # Check if order exists and update or insert accordingly
        if await order_exists(conn, orderNumber):
            sql = """
                UPDATE orders
                SET advOrderNumber = ?, buyerName = ?, buyerNickname = ?, buyerMobilePhone = ?,
                    sellerName = ?, sellerNickname = ?, sellerMobilePhone = ?, tradeType = ?,
                    orderStatus = ?, totalPrice = ?, price = ?, fiatUnit = ?, fiatSymbol = ?,
                    asset = ?, amount = ?, payType = ?, selectedPayId = ?, currencyRate = ?,
                    createTime = ?, notifyPayTime = ?, confirmPayTime = ?, notifyPayEndTime = ?,
                    confirmPayEndTime = ?, remark = ?, merchantNo = ?, takerUserNo = ?,
                    commission = ?, commissionRate = ?, takerCommission = ?, takerCommissionRate = ?,
                    takerAmount = ?, priceFloatingRatio = ?
                WHERE orderNumber = ?
            """
            params = (advOrderNumber, buyerName, buyerNickname, buyerMobilePhone,
                     sellerName, sellerNickname, sellerMobilePhone, tradeType,
                     orderStatus, totalPrice, price, fiatUnit, fiatSymbol,
                     asset, amount, payType, selectedPayId, currencyRate,
                     createTime, notifyPayTime, confirmPayTime, notifyPayEndTime,
                     confirmPayEndTime, remark, merchantNo, takerUserNo,
                     commission, commissionRate, takerCommission, takerCommissionRate,
                     takerAmount, priceFloatingRatio, orderNumber)
            await execute_and_commit(conn, sql, params)
            logger.info(f"Order {orderNumber} updated successfully")
        else:
            # Insert buyer if they don't exist
            if buyerName:
                await find_or_insert_buyer(conn, buyerName)
            
            sql = """
                INSERT INTO orders (
                    orderNumber, advOrderNumber, buyerName, buyerNickname, buyerMobilePhone,
                    sellerName, sellerNickname, sellerMobilePhone, tradeType, orderStatus,
                    totalPrice, price, fiatUnit, fiatSymbol, asset, amount, payType,
                    selectedPayId, currencyRate, createTime, notifyPayTime, confirmPayTime,
                    notifyPayEndTime, confirmPayEndTime, remark, merchantNo, takerUserNo,
                    commission, commissionRate, takerCommission, takerCommissionRate,
                    takerAmount, priceFloatingRatio, order_date
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime')
                )
            """
            params = (orderNumber, advOrderNumber, buyerName, buyerNickname, buyerMobilePhone,
                     sellerName, sellerNickname, sellerMobilePhone, tradeType, orderStatus,
                     totalPrice, price, fiatUnit, fiatSymbol, asset, amount, payType,
                     selectedPayId, currencyRate, createTime, notifyPayTime, confirmPayTime,
                     notifyPayEndTime, confirmPayEndTime, remark, merchantNo, takerUserNo,
                     commission, commissionRate, takerCommission, takerCommissionRate,
                     takerAmount, priceFloatingRatio)
            await execute_and_commit(conn, sql, params)
            logger.info(f"Order {orderNumber} inserted successfully")

    except Exception as e:
        logger.error(f"Error in insert_or_update_order: {e}")
        print(f"Exception details: {e}")

# Original functions with enhanced upsert logic
async def register_merchant(conn, sellerName):
    if not sellerName: 
        logger.error(f"Provided sellerName is invalid: {sellerName}")
        return None
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM merchants WHERE sellerName = ?", (sellerName,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            await cursor.execute("INSERT INTO merchants (sellerName) VALUES (?)", (sellerName,))
            return cursor.lastrowid

async def update_total_spent(conn, orderNumber):
    try:
        order_sql = """
            SELECT buyerName, sellerName, totalPrice, order_date
            FROM orders
            WHERE orderNumber = ?
        """
        async with conn.cursor() as cursor:
            await cursor.execute(order_sql, (orderNumber,))
            order_details = await cursor.fetchone()
            if not order_details:
                logger.warning(f"No order found with orderNumber: {orderNumber}")
                return
            
            buyerName, sellerName, totalPrice, order_date = order_details
        
        # Ensure user exists before updating
        await find_or_insert_buyer(conn, buyerName)
        
        update_user_sql = """
            UPDATE users 
            SET total_crypto_sold_lifetime = total_crypto_sold_lifetime + ?
            WHERE name = ?
        """
        await execute_and_commit(conn, update_user_sql, (totalPrice, buyerName))
        await insert_transaction(conn, buyerName, sellerName, totalPrice, order_date)
    except Exception as e:
        logger.error(f"An error occurred in update_total_spent: {e}")

async def insert_transaction(conn, buyerName, sellerName, totalPrice, order_date):
    # Ensure both users exist
    await find_or_insert_buyer(conn, buyerName)
    await find_or_insert_buyer(conn, sellerName)
    
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT OR IGNORE INTO transactions 
            (buyer_name, seller_name, total_price, order_date) 
            VALUES (?, ?, ?, ?)
            """, 
            (buyerName, sellerName, totalPrice, order_date)
        )
    
async def update_kyc_status(conn, name, new_kyc_status):
    try:
        # Ensure user exists before updating
        await find_or_insert_buyer(conn, name)
        await update_table_column(conn, "users", "kyc_status", new_kyc_status, "name", name)
    except Exception as e:
        logger.error(f"Error updating KYC status for user {name}: {e}")

async def update_anti_fraud_stage(conn, buyerName, new_stage):
    try:
        # Ensure user exists before updating
        await find_or_insert_buyer(conn, buyerName)
        await update_table_column(conn, "users", "anti_fraud_stage", new_stage, "name", buyerName)
    except Exception as e:
        logger.error(f"Error updating anti-fraud stage for user {buyerName}: {e}")

async def update_returning_customer_stage(conn, orderNumber, new_stage):
    try:
        # Ensure order exists before updating
        await find_or_insert_order(conn, orderNumber)
        await update_table_column(conn, "orders", "returning_customer_stage", new_stage, "orderNumber", orderNumber)
    except Exception as e:
        logger.error(f"Error updating returning customer stage for order {orderNumber}: {e}")

async def set_menu_presented(conn, orderNumber, value):
    try:
        # Check if order exists, if not we can't set menu_presented without more info
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Cannot set menu_presented for non-existent order {orderNumber}")
            return
        await update_table_column(conn, "orders", "menu_presented", value, "orderNumber", orderNumber)
    except Exception as e:
        logger.error(f"Error setting menu_presented for orderNumber {orderNumber}: {e}")

async def update_order_status(conn, orderNumber, orderStatus):
    try:
        # Check if order exists, if not we can't update status without more info
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Cannot update status for non-existent order {orderNumber}")
            return
        await update_table_column(conn, "orders", "orderStatus", orderStatus, "orderNumber", orderNumber)
    except Exception as e:
        logger.error(f"Error updating order status for orderNumber {orderNumber}: {e}")

async def update_order_details(conn, orderNumber, account_number, seller_bank):
    try:
        # Check if order exists, if not we can't update details without more info
        if not await order_exists(conn, orderNumber):
            logger.warning(f"Cannot update details for non-existent order {orderNumber}")
            return
        sql = "UPDATE orders SET account_number = ?, seller_bank = ? WHERE orderNumber = ?"
        params = (account_number, seller_bank, orderNumber)
        await execute_and_commit(conn, sql, params)
    except Exception as e:
        logger.error(f"Error updating order details for orderNumber {orderNumber}: {e}")

async def update_buyer_bank(conn, buyerName, new_buyer_bank):
    try:
        # Ensure user exists before updating
        await find_or_insert_buyer(conn, buyerName)
        await update_table_column(conn, "users", "user_bank", new_buyer_bank, "name", buyerName)
    except Exception as e:
        logger.error(f"Error updating user_bank for user {buyerName}: {e}")

async def set_user_language_preference(conn, buyerName: str, language: str) -> bool:
    """Set user's language preference in database."""
    try:
        # Ensure user exists first
        await find_or_insert_buyer(conn, buyerName)
        
        # Update the language preference
        sql = "UPDATE users SET language_preference = ? WHERE name = ?"
        await execute_and_commit(conn, sql, (language, buyerName))
        return True
        
    except Exception as e:
        logger.error(f"Error setting language preference for {buyerName}: {str(e)}")
        return False
    
async def set_language_selection_stage(conn, buyerName: str, stage: int) -> bool:
    """Set user's language selection stage in database."""
    try:
        # Ensure user exists first
        await find_or_insert_buyer(conn, buyerName)
        
        # Update the language selection stage
        sql = "UPDATE users SET language_selection_stage = ? WHERE name = ?"
        await execute_and_commit(conn, sql, (stage, buyerName))
        return True
        
    except Exception as e:
        logger.error(f"Error setting language selection stage for {buyerName}: {str(e)}")
        return False

ALLOWED_TABLES: Dict[str, Dict[str, Union[type, tuple]]] = {
    "orders": {
        "orderNumber": str,
        "advOrderNumber": str,
        "buyerName": str,
        "buyerNickname": str,
        "buyerMobilePhone": str,
        "sellerName": str,
        "sellerNickname": str,
        "sellerMobilePhone": str,
        "tradeType": str,
        "orderStatus": int,
        "totalPrice": float,
        "price": float,
        "fiatUnit": str,
        "fiatSymbol": str,
        "asset": str,
        "amount": float,
        "payType": str,
        "selectedPayId": int,
        "currencyRate": float,
        "createTime": int,
        "notifyPayTime": int,
        "confirmPayTime": int,
        "notifyPayEndTime": int,
        "confirmPayEndTime": int,
        "remark": str,
        "merchantNo": str,
        "takerUserNo": str,
        "commission": float,
        "commissionRate": float,
        "takerCommission": float,
        "takerCommissionRate": float,
        "takerAmount": float,
        "menu_presented": bool,
        "ignore_count": int,
        "account_number": str,
        "buyer_bank": str,
        "seller_bank_account": str,
        "merchant_id": int,
        "priceFloatingRatio": float,
        "payment_screenshoot": bool,
        "payment_image_url": str,
        "paid": bool,
        "clave_de_rastreo": str,
        "seller_bank": str,
        "returning_customer_stage": int
    },
    "users": {
        "name": str,
        "kyc_status": int,
        "total_crypto_sold_lifetime": float,
        "anti_fraud_stage": int,
        "rfc": str,
        "codigo_postal": str,
        "user_bank": str,
        "usd_verification_stage": int,
        "language_preference": str,
        "language_selection_stage": int 
    },
    "merchants": {
        "sellerName": str,
        "api_key": str,
        "api_secret": str,
        "email": str,
        "password_hash": str,
        "phone_num": str,
        "user_bank": str
    },
    "transactions": {
        "buyer_name": str,
        "seller_name": str,
        "total_price": float,
        "order_date": str,
        "merchant_id": int
    },
    "order_bank_identifiers": {
        "orderNumber": str,
        "bank_identifier": str
    },
    "usd_price_manager": {
        "trade_type": str,
        "exchange_rate_ratio": float,
        "mxn_amount": float
    },
    "deposits": {
        "timestamp": str,
        "bank_account_id": int,
        "amount_deposited": float
    },
    "bank_accounts": {
        "account_bank_name": str,
        "account_beneficiary": str,
        "account_number": str,
        "account_limit": float,
        "account_balance": float
    },
    "blacklist": {
        "name": str,
        "orderNumber": str,
        "country": str
    },
    "mxn_deposits": {
        "timestamp": str,
        "account_number": str,
        "amount_deposited": float,
        "deposit_from": str,
        "year": int,
        "month": int,
        "merchant_id": int
    },
    "P2PBlacklist": {
        "name": str,
        "orderNumber": str,
        "country": str,
        "response": str,
        "anti_fraud_stage": int,
        "merchant_id": int
    },
    "mxn_bank_accounts": {
        "account_bank_name": str,
        "account_beneficiary": str,
        "account_number": str,
        "account_daily_limit": float,
        "account_monthly_limit": float,
        "account_balance": float,
        "last_used_timestamp": str,
        "merchant_id": int
    },
    "oxxo_debit_cards": {
        "account_bank_name": str,
        "account_beneficiary": str,
        "card_number": str,
        "account_daily_limit": float,
        "account_monthly_limit": float,
        "account_balance": float,
        "last_used_timestamp": str,
        "merchant_id": int
    }
}

async def update_table_column(
    conn: aiosqlite.Connection,
    table: str,
    column: str,
    value: Any,
    condition_column: str,
    condition_value: Any
) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table}")
    
    if column not in ALLOWED_TABLES[table]:
        raise ValueError(f"Invalid column: {column} for table: {table}")
    
    if condition_column not in ALLOWED_TABLES[table]:
        raise ValueError(f"Invalid condition column: {condition_column} for table: {table}")

    expected_type = ALLOWED_TABLES[table][column]
    if not isinstance(value, expected_type):
        raise TypeError(f"Expected {expected_type} for {column}, got {type(value)}")

    if expected_type == bool:
        value = 1 if value else 0

    try:
        sql = f"UPDATE {table} SET {column} = ? WHERE {condition_column} = ?"
        params = (value, condition_value)
        await execute_and_commit(conn, sql, params)
    except Exception as e:
        logger.error(f"Error updating {column} in {table} where {condition_column} = {condition_value}: {e}")
        raise