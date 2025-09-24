# balance_manager.py
"""
Balance Management System for Cryptocurrency Exchange Accounts

Handles balance tracking, aggregation, and reporting across multiple
exchange accounts with SQLite database persistence.

Key Features:
- Multi-account balance tracking
- Asset aggregation and reporting
- Async database operations for performance
- Clean error handling and logging
"""

import sqlite3
import asyncio
import aiosqlite
from utils.logging_config import setup_logging
from data.database.connection import print_table_contents, create_connection, DB_FILE

logger = setup_logging(log_filename='balance_manager.log')


def setup_database():
    """Initialize database tables for balance tracking"""
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()
        
        # Create main balances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                id INTEGER PRIMARY KEY,
                exchange_id INTEGER,
                account TEXT,
                asset TEXT,
                balance FLOAT,
                UNIQUE(exchange_id, account, asset)
            )
        ''')
        
        # Create aggregated balances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS total_balances (
                asset TEXT PRIMARY KEY,
                total_balance FLOAT
            )
        ''')
        
        connection.commit()
        logger.info("Database tables initialized successfully")
        
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if connection:
            connection.close()


def update_balance(exchange_id, account, combined_balances):
    """
    Update account balances, setting missing assets to zero.
    
    Args:
        exchange_id: Exchange identifier
        account: Account name
        combined_balances: Dict of {asset: balance}
    """
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()
        
        # Get existing assets for this account
        cursor.execute('''
            SELECT asset FROM balances 
            WHERE exchange_id = ? AND account = ?
        ''', (exchange_id, account))
        existing_assets = set(row[0] for row in cursor.fetchall())

        # Update or insert new balances
        for asset, balance in combined_balances.items():
            cursor.execute('''
                INSERT OR REPLACE INTO balances (exchange_id, account, asset, balance)
                VALUES (?, ?, ?, ?)
            ''', (exchange_id, account, asset, balance))
            existing_assets.discard(asset)

        # Set missing assets to zero
        for asset in existing_assets:
            cursor.execute('''
                UPDATE balances SET balance = 0
                WHERE exchange_id = ? AND account = ? AND asset = ?
            ''', (exchange_id, account, asset))

        connection.commit()
        logger.debug(f"Updated balances for {account}: {len(combined_balances)} assets")
        
    except sqlite3.Error as e:
        logger.error(f"Failed to update balance for {account}: {e}")
        raise
    finally:
        if connection:
            connection.close()


def update_total_balances():
    """Aggregate individual account balances into total balances table"""
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # Calculate aggregated balances
        cursor.execute('''
            SELECT asset, SUM(balance)
            FROM balances
            GROUP BY asset
        ''')
        aggregated_balances = cursor.fetchall()

        # Update total balances table
        for asset, total_balance in aggregated_balances:
            cursor.execute('''
                INSERT OR REPLACE INTO total_balances (asset, total_balance)
                VALUES (?, ?)
            ''', (asset, total_balance))
        
        connection.commit()
        logger.debug(f"Updated total balances for {len(aggregated_balances)} assets")
        
    except sqlite3.Error as e:
        logger.error(f"Failed to update total balances: {e}")
        raise
    finally:
        if connection:
            connection.close()


def get_balance(exchange_id, account):
    """
    Get balances for a specific account.
    
    Args:
        exchange_id: Exchange identifier
        account: Account name
        
    Returns:
        dict: {asset: balance} mapping
    """
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT asset, balance 
            FROM balances 
            WHERE exchange_id = ? AND account = ?
        ''', (exchange_id, account))
        balances = {asset: balance for asset, balance in cursor.fetchall()}
        return balances
        
    except sqlite3.Error as e:
        logger.error(f"Failed to get balance for {account}: {e}")
        return {}
    finally:
        if connection:
            connection.close()


def get_all_balances():
    """
    Get all account balances.
    
    Returns:
        list: [(exchange_id, account, asset, balance), ...]
    """
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT exchange_id, account, asset, balance 
            FROM balances
            WHERE balance > 0
        ''')
        balances_data = cursor.fetchall()
        return balances_data
        
    except sqlite3.Error as e:
        logger.error(f"Failed to get all balances: {e}")
        return []
    finally:
        if connection:
            connection.close()


def get_total_asset_balances():
    """
    Get aggregated balances by asset.
    
    Returns:
        list: [(asset, total_balance), ...]
    """
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT asset, SUM(balance)
            FROM balances
            WHERE balance > 0
            GROUP BY asset
        ''')
        total_balances = cursor.fetchall()
        return total_balances
        
    except sqlite3.Error as e:
        logger.error(f"Failed to get total asset balances: {e}")
        return []
    finally:
        if connection:
            connection.close()


async def get_total_usd():
    """
    Get total USD-equivalent balance across all stablecoins.
    
    Returns:
        float: Total USD balance
    """
    try:
        async with aiosqlite.connect(DB_FILE) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('''
                    SELECT SUM(balance)
                    FROM balances
                    WHERE asset IN ('USD', 'USDC', 'USDT', 'TUSD', 'DAI', 'FDUSD')
                      AND balance > 0
                ''')
                result = await cursor.fetchone()
                total_usd = result[0] if result and result[0] is not None else 0.0
                
        logger.debug(f"Total USD balance: {total_usd}")
        return total_usd
        
    except Exception as e:
        logger.error(f"Failed to get total USD: {e}")
        return 0.0


async def generate_balance_report():
    """Generate comprehensive balance report"""
    try:
        logger.info("Generating balance report...")
        
        # Get USD total
        usd_balance = await get_total_usd()
        logger.info(f"Total USD Balance: ${usd_balance:,.2f}")
        
        # Get asset breakdown
        asset_balances = get_total_asset_balances()
        if asset_balances:
            logger.info("Asset Breakdown:")
            for asset, balance in asset_balances:
                logger.info(f"  {asset}: {balance:,.6f}")
        
        # Get account breakdown
        all_balances = get_all_balances()
        account_totals = {}
        for exchange_id, account, asset, balance in all_balances:
            key = f"{account} (ID: {exchange_id})"
            if key not in account_totals:
                account_totals[key] = {}
            account_totals[key][asset] = balance
        
        if account_totals:
            logger.info("Account Breakdown:")
            for account, assets in account_totals.items():
                logger.info(f"  {account}:")
                for asset, balance in assets.items():
                    logger.info(f"    {asset}: {balance:,.6f}")
        
        return {
            'total_usd': usd_balance,
            'asset_balances': dict(asset_balances),
            'account_balances': account_totals
        }
        
    except Exception as e:
        logger.error(f"Failed to generate balance report: {e}")
        return None


async def main():
    """Demo function showing system usage"""
    try:
        # Initialize database
        setup_database()
        
        # Generate and display report
        report = await generate_balance_report()
        if report:
            logger.info("Balance report generated successfully")
        
        # Display raw table data
        conn = await create_connection(DB_FILE)
        if conn:
            await print_table_contents(conn, 'balances')
            await conn.close()
        else:
            logger.error("Cannot create database connection")
            
    except Exception as e:
        logger.error(f"Application error: {e}")


if __name__ == "__main__":
    asyncio.run(main())