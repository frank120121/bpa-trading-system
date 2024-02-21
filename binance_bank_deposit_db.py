import asyncio
from common_vars import bank_accounts, DB_FILE
from common_utils_db import print_table_contents, create_connection, add_column_if_not_exists
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
            account_limit REAL,
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
                'INSERT INTO mxn_bank_accounts (account_bank_name, account_beneficiary, account_number, account_limit, account_balance) VALUES (?, ?, ?, ?, ?)',
                (account['bank_name'], account['beneficiary'], account['account_number'], account['limit'], 0))
        else:
            logger.info(f"Account number {account['account_number']} already exists. Skipping insertion.")
    await conn.commit()

async def add_bank_account(conn, bank_name, beneficiary, account_number, account_limit, account_balance=0):
    try:
        await conn.execute(
            'INSERT INTO mxn_bank_accounts (account_bank_name, account_beneficiary, account_number, account_limit, account_balance) VALUES (?, ?, ?, ?, ?)',
            (bank_name, beneficiary, account_number, account_limit, account_balance))
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


async def main():
    conn = await create_connection(DB_FILE)
    if conn is not None:
        # Initialize the database (create tables and insert initial data)
        #await initialize_database(conn)

        # Print table contents for verification
        #Sawait remove_bank_account(conn, '012778004824246573')

        # await update_account_balance(conn, '710969000007300927', 92846.11)
        # await update_account_balance(conn, '710969000016348705', 4000.14)
        # await update_account_balance(conn, '710969000015306104', 37236.06)
        # await update_account_balance(conn, '014761655091416464', 117805.24)
        # await update_account_balance(conn, '058597000056476091', 91868.96)
        # await update_account_balance(conn, '646180204200033494', 86515.32)
        # await update_account_balance(conn, '646180146006124571', 108598.54)
        # await update_account_balance(conn, '012778015323351288', 162458.23)
        # await update_account_balance(conn, '012778015939990486', 139889.38)
        # await update_account_balance(conn, '058597000054265356', 55932.75)

        
        await print_table_contents(conn, 'mxn_bank_accounts')

        await conn.close()
    else:
        logger.error("Error! Cannot create the database connection.")

if __name__ == '__main__':
    asyncio.run(main())