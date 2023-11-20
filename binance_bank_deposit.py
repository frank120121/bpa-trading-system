import datetime
import asyncio
from common_vars import bank_accounts
from database import create_connection, print_table_contents
import logging
from logging_config import setup_logging
setup_logging(log_filename='Database_logger.log')
logger = logging.getLogger(__name__)

DB_FILE = 'C:/Users/p7016/Documents/bpa/orders_data.db'

async def initialize_database(conn):
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS mxn_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                account_number TEXT,
                amount_deposited REAL
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
                last_used_timestamp DATETIME DEFAULT NULL
            )
        ''')
        for account in bank_accounts:
            await conn.execute(
                'INSERT INTO mxn_bank_accounts (account_bank_name, account_beneficiary, account_number, account_limit, account_balance) VALUES (?, ?, ?, ?, ?)',
                (account['bank_name'], account['beneficiary'], account['account_number'], account['limit'], 0))
        await conn.commit()

async def log_deposit(conn, bank_account_number, amount_deposited):
    timestamp = datetime.datetime.now()
    await conn.execute('INSERT INTO mxn_deposits (timestamp, account_number, amount_deposited) VALUES (?, ?, ?)',
                      (timestamp, bank_account_number, amount_deposited))
    await conn.execute('UPDATE mxn_bank_accounts SET account_balance = account_balance + ? WHERE account_number = ?', (amount_deposited, bank_account_number))
    await conn.commit()

async def get_payment_details(conn, order_no):
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=1)
        # First, check if an account is already assigned to this order
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    assigned_account_number = result[0] if result else None

        # If no account is assigned, find an appropriate account and update the order
    if not assigned_account_number:
        # Find the last used account
        cursor = await conn.execute('SELECT account_number FROM mxn_bank_accounts ORDER BY last_used_timestamp DESC LIMIT 1')
        last_assigned_account = await cursor.fetchone()
        last_assigned_account = last_assigned_account[0] if last_assigned_account else None

        # Fetch all accounts, ordered by ID
        cursor = await conn.execute('SELECT id, account_bank_name, account_beneficiary, account_number, account_limit FROM mxn_bank_accounts ORDER BY id')
        accounts = await cursor.fetchall()

        # Determine the starting index for account selection
        start_index = next((index for index, account in enumerate(accounts) if account[3] == last_assigned_account), -1) + 1

        # Iterate over accounts starting from the one after the last assigned
        for i in range(len(accounts)):
            account = accounts[(start_index + i) % len(accounts)]
            # Check the total deposited amount for this account
            cursor = await conn.execute('SELECT SUM(amount_deposited) FROM mxn_deposits WHERE account_number = ? AND timestamp >= ?', (account[3], cutoff_time))
            total_deposited = await cursor.fetchone()
            total_deposited = total_deposited[0] if total_deposited[0] is not None else 0.0

            if total_deposited < account[4]:
                assigned_account_number = account[3]
                # Update the last used timestamp for this account
                await conn.execute('UPDATE mxn_bank_accounts SET last_used_timestamp = ? WHERE account_number = ?', (datetime.datetime.now(), assigned_account_number))
                await update_order_details(conn, order_no, assigned_account_number)
                break

    # If an account number is assigned, fetch its details to return
    if assigned_account_number:
        cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM mxn_bank_accounts WHERE account_number = ?', (assigned_account_number,))
        account_details = await cursor.fetchone()
        if account_details:
            return (
                f"Los detalles para el pago son:\n\n"
                f"Nombre de banco: {account_details[0]}\n"
                f"Nombre del beneficiario: {account_details[1]}\n"
                f"Número de CLABE: {account_details[2]}\n"
            )

    return None

async def get_total_deposited_last_24_hours(conn):
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=1)
    cursor = await conn.execute('SELECT SUM(amount_deposited) FROM mxn_deposits WHERE timestamp >= ?', (cutoff_time,))
    total_deposited = await cursor.fetchone()
    return total_deposited[0] if total_deposited else 0.0
async def update_order_details(conn, order_no, account_number):
        # Prepare the SQL statement for updating the order
    sql = '''
        UPDATE orders
        SET account_number = ?
        WHERE order_no = ?
    '''

    # Execute the SQL statement with the provided account number and order number
    await conn.execute(sql, (account_number, order_no))

    # Commit the changes to the database
    await conn.commit()

async def main():
    conn = await create_connection(DB_FILE)
    if conn is not None:
        # Initialize the database (create tables and insert initial data)
        #await initialize_database(conn)

        # Print table contents for verification
        await print_table_contents(conn, 'mxn_deposits')
        await print_table_contents(conn, 'mxn_bank_accounts')

        await conn.close()
    else:
        logger.error("Error! Cannot create the database connection.")

if __name__ == '__main__':
    asyncio.run(main())
