# bpa/binance_bank_deposit_db.py
import datetime
from typing import Optional

from src.utils.common_vars import payment_accounts 
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)

async def initialize_database(conn):
    """
    Initializes a generic schema and populates it from the common_vars list.
    """

    # This creates the table if it doesn't exist
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS payment_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiat TEXT NOT NULL,
            pay_type TEXT NOT NULL,
            beneficiary TEXT,
            account_details TEXT UNIQUE NOT NULL,
            daily_limit REAL DEFAULT 0,
            monthly_limit REAL DEFAULT 0,
            last_used_timestamp DATETIME DEFAULT NULL
        )
    ''')

    # This creates the deposits table if it doesn't exist
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            account_details TEXT,
            amount_deposited REAL,
            deposit_from TEXT,
            year INTEGER,
            month INTEGER
        )
    ''')

    # --- START of Integration Logic ---
    # Loop through the imported list and add any missing accounts
    for account in payment_accounts:
        cursor = await conn.execute("SELECT 1 FROM payment_accounts WHERE account_details = ?", (account['account_details'],))
        if not await cursor.fetchone():
            await add_payment_account(
                conn,
                fiat=account['fiat'],
                pay_type=account['pay_type'],
                beneficiary=account['beneficiary'],
                account_details=account['account_details'],
                daily_limit=account['daily_limit'],
                monthly_limit=account['monthly_limit']
            )
    # --- END of Integration Logic ---

    await conn.commit()
    logger.info("Database initialized and populated with payment accounts.")


async def add_payment_account(conn, fiat: str, pay_type: str, beneficiary: str, account_details: str, daily_limit: float = 0, monthly_limit: float = 0):
    """Adds any type of payment account to the generic table."""
    try:
        await conn.execute(
            'INSERT INTO payment_accounts (fiat, pay_type, beneficiary, account_details, daily_limit, monthly_limit) VALUES (?, ?, ?, ?, ?, ?)',
            (fiat, pay_type, beneficiary, account_details, daily_limit, monthly_limit)
        )
        await conn.commit()
        logger.info(f"Successfully added {pay_type} account: {account_details}")
    except Exception as e:
        # Ignore unique constraint errors, which are expected if account already exists
        if "UNIQUE constraint failed" not in str(e):
            logger.error(f"Error adding payment account: {e}")
            raise

async def remove_payment_account(conn, account_details: str):
    """Removes a payment account using its unique details (CLABE, email, etc.)."""
    try:
        await conn.execute('DELETE FROM payment_accounts WHERE account_details = ?', (account_details,))
        await conn.commit()
        logger.info(f"Successfully removed account: {account_details}")
    except Exception as e:
        logger.error(f"Error removing payment account: {e}")
        raise

async def log_deposit(conn, deposit_from: str, account_details: str, amount_deposited: float):
    """Logs a deposit into the generic deposits table."""
    timestamp = datetime.datetime.now()
    year, month = timestamp.year, timestamp.month
    await conn.execute(
        'INSERT INTO deposits (timestamp, account_details, amount_deposited, deposit_from, year, month) VALUES (?, ?, ?, ?, ?, ?)',
        (timestamp, account_details, amount_deposited, deposit_from, year, month)
    )
    await conn.commit()

async def update_last_used_timestamp(conn, account_details: str):
    """Updates the timestamp for any type of payment account."""
    current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    await conn.execute(
        'UPDATE payment_accounts SET last_used_timestamp = ? WHERE account_details = ?',
        (current_timestamp, account_details)
    )
    await conn.commit()

async def sum_recent_deposits(conn, account_details: str, buyer_name: Optional[str] = None) -> float:
    """Sums deposits for a specific account for the current day, optionally filtered by buyer."""
    start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = 'SELECT SUM(amount_deposited) FROM deposits WHERE account_details = ? AND timestamp >= ?'
    params = [account_details, start_of_day]
    
    if buyer_name:
        query += ' AND deposit_from = ?'
        params.append(buyer_name)
        
    cursor = await conn.execute(query, tuple(params))
    result = await cursor.fetchone()
    return result[0] if result and result[0] is not None else 0.0

async def sum_monthly_deposits(conn, account_details: str, buyer_name: Optional[str] = None) -> float:
    """Sums deposits for a specific account for the current month, optionally filtered by buyer."""
    start_of_month = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query = 'SELECT SUM(amount_deposited) FROM deposits WHERE account_details = ? AND timestamp >= ?'
    params = [account_details, start_of_month]

    if buyer_name:
        query += ' AND deposit_from = ?'
        params.append(buyer_name)

    cursor = await conn.execute(query, tuple(params))
    result = await cursor.fetchone()
    return result[0] if result and result[0] is not None else 0.0