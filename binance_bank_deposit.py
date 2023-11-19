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
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                bank_account_id INTEGER,
                amount_deposited REAL
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_bank_name TEXT,
                account_beneficiary TEXT,
                account_number TEXT,
                account_limit REAL,
                account_balance REAL DEFAULT 0
            )
        ''')
        for account in bank_accounts:
            await conn.execute(
                'INSERT INTO bank_accounts (account_bank_name, account_beneficiary, account_number, account_limit, account_balance) VALUES (?, ?, ?, ?, ?)',
                (account['bank_name'], account['beneficiary'], account['account_number'], account['limit'], 0))
        await conn.commit()

async def log_deposit(conn, bank_account_id, amount_deposited):
    timestamp = datetime.datetime.now()
    await conn.execute('INSERT INTO deposits (timestamp, bank_account_id, amount_deposited) VALUES (?, ?, ?)',
                      (timestamp, bank_account_id, amount_deposited))
    await conn.execute('UPDATE bank_accounts SET account_balance = account_balance + ? WHERE id = ?', (amount_deposited, bank_account_id))
    await conn.commit()

async def get_payment_details(conn, order_no):
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=1)
        # First, check if an account is already assigned to this order
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    assigned_account_number = result[0] if result else None

        # If no account is assigned, find an appropriate account and update the order
    if not assigned_account_number:
        cursor = await conn.execute('SELECT id, account_bank_name, account_beneficiary, account_number, account_limit FROM bank_accounts ORDER BY id')
        accounts = await cursor.fetchall()
        for account in accounts:
            cursor = await conn.execute('SELECT SUM(amount_deposited) FROM deposits WHERE bank_account_id = ? AND timestamp >= ?', (account[0], cutoff_time))
            total_deposited = await cursor.fetchone()
            total_deposited = total_deposited[0] if total_deposited[0] is not None else 0.0
            if total_deposited < account[4]:
                assigned_account_number = account[3]
                await update_order_details(conn, order_no, assigned_account_number)
                break

    # If an account number is assigned, fetch its details to return
    if assigned_account_number:
        cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM bank_accounts WHERE account_number = ?', (assigned_account_number,))
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
    cursor = await conn.execute('SELECT SUM(amount_deposited) FROM deposits WHERE timestamp >= ?', (cutoff_time,))
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
        #await initialize_database()

        # Print table contents for verification
        await print_table_contents(conn, 'deposits')
        await print_table_contents(conn, 'bank_accounts')

        await conn.close()
    else:
        logger.error("Error! Cannot create the database connection.")

if __name__ == '__main__':
    asyncio.run(main())
