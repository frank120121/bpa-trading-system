import datetime
import asyncio
from common_vars import bank_accounts, DB_FILE
from common_utils_db import print_table_contents, create_connection
import logging

logger = logging.getLogger(__name__)

async def initialize_database(conn):
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mxn_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            account_number TEXT,
            amount_deposited REAL,
            deposit_from TEXT DEFAULT NULL,
            year INTEGER DEFAULT NULL,
            month INTEGER DEFAULT NULL,
            merchant_id INTEGER REFERENCES merchants(id) 
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mxn_bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_bank_name TEXT,
            account_beneficiary TEXT,
            account_number TEXT UNIQUE,
            account_daily_limit REAL,
            account_monthly_limit REAL,
            account_balance REAL DEFAULT 0,
            last_used_timestamp DATETIME DEFAULT NULL,
            merchant_id INTEGER REFERENCES merchants(id)
        )
    ''')
    for account in bank_accounts:
        # Check if the account number already exists
        cursor = await conn.execute("SELECT 1 FROM mxn_bank_accounts WHERE account_number = ?", (account['account_number'],))
        if not await cursor.fetchone():
            await conn.execute(
                'INSERT INTO mxn_bank_accounts (account_bank_name, account_beneficiary, account_number, account_daily_limit, account_monthly_limit, account_balance) VALUES (?, ?, ?, ?, ?, ?)',
                (account['bank_name'], account['beneficiary'], account['account_number'], account['account_daily_limit'], account['account_monthly_limit'], 0))
        else:
            logger.info(f"Account number {account['account_number']} already exists. Skipping insertion.")
    await conn.commit()

async def add_bank_account(conn, bank_name, beneficiary, account_number, account_daily_limit, account_monthly_limit, account_balance=0):
    try:
        await conn.execute(
            'INSERT INTO mxn_bank_accounts (account_bank_name, account_beneficiary, account_number, account_daily_limit, account_monthly_limit, account_balance) VALUES (?, ?, ?, ?, ?, ?)',
            (bank_name, beneficiary, account_number, account_daily_limit, account_monthly_limit, account_balance))
        await conn.commit()
        logger.info(f"Added new bank account: {account_number}")
    except Exception as e:
        logger.error(f"Error adding bank account: {e}")
        raise

async def remove_bank_account(conn, account_number):
    try:
        await conn.execute('DELETE FROM mxn_bank_accounts WHERE account_number = ?', (account_number,))
        await conn.commit()
        logger.info(f"Removed bank account: {account_number}")
    except Exception as e:
        logger.error(f"Error removing bank account: {e}")
        raise

# Create an async function that updates the account balance
async def update_account_balance(conn, account_number, amount):
    try:
        await conn.execute('UPDATE mxn_bank_accounts SET account_balance = ? WHERE account_number = ?', (amount, account_number))
        await conn.commit()
        logger.info(f"Updated account balance for account: {account_number}")
    except Exception as e:
        logger.error(f"Error updating account balance: {e}")
        raise

async def update_last_used_timestamp(conn, account_number):
    try:
        # Format the current timestamp for SQLite DATETIME
        current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Execute the SQL command to update the last used timestamp
        await conn.execute(
            'UPDATE mxn_bank_accounts SET last_used_timestamp = ? WHERE account_number = ?',
            (current_timestamp, account_number)
        )

        # Commit the changes to the database
        await conn.commit()

        # Log the successful update
        logger.info(f"Updated last_used_timestamp for account: {account_number} to {current_timestamp}")
    except Exception as e:
        # Log the error and re-raise it to maintain the behavior of update_account_balance
        logger.error(f"Error updating last_used_timestamp for account: {account_number}: {e}")
        raise

async def log_deposit(conn, deposit_from, bank_account_number, amount_deposited):
    timestamp = datetime.datetime.now()
    year, month = timestamp.year, timestamp.month
    await conn.execute('INSERT INTO mxn_deposits (timestamp, account_number, amount_deposited, deposit_from, year, month) VALUES (?, ?, ?, ?, ?, ?)',
                       (timestamp, bank_account_number, amount_deposited, deposit_from, year, month))
    await conn.execute('UPDATE mxn_bank_accounts SET account_balance = account_balance + ? WHERE account_number = ?', (amount_deposited, bank_account_number))
    await conn.commit()
    logger.info(f"Logged deposit of {amount_deposited} from {deposit_from} to account {bank_account_number}")


async def main():
    conn = await create_connection(DB_FILE)
    if conn is not None:
        # Initialize the database (create tables and insert initial data)
        #await initialize_database(conn)
        # Print table contents for verification
        # await remove_bank_account(conn, '0482424657')
        # await remove_bank_account(conn, '012778015323351288')
        # await remove_bank_account(conn, '012778015939990486')

        # await update_account_balance(conn, '710969000007300927', 31800.08)
        # await update_account_balance(conn, '058597000056476091', 92084.33)
        # # await update_account_balance(conn, '646180146006124571', 77368.91)
        # await update_account_balance(conn, '1532335128', 120980.47)

        #MARIA FERNANDA MUNOZ PEREA
        # await update_account_balance(conn, '710969000016348705', 3500.03)    #NVIO
        # await update_account_balance(conn, '1593999048', 201223.95)
        # await update_account_balance(conn, '0482424657', 107092.24)    #BBVA

        # MARTHA GUERRERO LOPEZ
        # await update_account_balance(conn, '710969000015306104', 63970.07)
        # await update_account_balance(conn, '014761655091416464', 69611.56)    #SANTANDER
        # await update_account_balance(conn, '058597000054265356', 142037.53)

        # await update_account_balance(conn, '646180204200033494', 60275.06)

        await print_table_contents(conn, 'mxn_bank_accounts')

        await conn.close()
    else:
        logger.error("Error! Cannot create the database connection.")

if __name__ == '__main__':
    asyncio.run(main())