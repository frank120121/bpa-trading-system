import datetime
import logging

# Importing custom modules and variables
from database import get_buyer_bank, update_order_details
from common_vars import BBVA_BANKS, CUTOFF_DAYS
logger = logging.getLogger(__name__)

async def log_deposit(conn, bank_account_number, amount_deposited):
    timestamp = datetime.datetime.now()
    await conn.execute('INSERT INTO mxn_deposits (timestamp, account_number, amount_deposited) VALUES (?, ?, ?)',
                      (timestamp, bank_account_number, amount_deposited))
    await conn.execute('UPDATE mxn_bank_accounts SET account_balance = account_balance + ? WHERE account_number = ?', (amount_deposited, bank_account_number))
    await conn.commit()

async def get_payment_details(conn, order_no):
    """Retrieve payment details for an order, assigning a bank account if necessary."""
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=CUTOFF_DAYS)

    assigned_account_number = await get_assigned_account(conn, order_no)

    if not assigned_account_number:
        buyer_bank = await get_buyer_bank(conn, order_no)
        is_bbva_bank = buyer_bank.lower() in BBVA_BANKS if buyer_bank else False
        bank_condition = "%BBVA%" if is_bbva_bank else "%BBVA%"
        
        last_account = await get_last_used_account(conn, bank_condition)
        accounts = await get_accounts(conn, bank_condition)
        
        assigned_account_number = await assign_account(conn, accounts, last_account, cutoff_time, order_no)

    return await get_account_details(conn, assigned_account_number) if assigned_account_number else None

async def get_assigned_account(conn, order_no):
    """Check if an account is already assigned to this order."""
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    return result[0] if result else None

async def get_last_used_account(conn, bank_condition):
    """Retrieve the last used account based on bank condition."""
    cursor = await conn.execute(f"SELECT account_number FROM mxn_bank_accounts WHERE account_bank_name LIKE '{bank_condition}' ORDER BY last_used_timestamp DESC LIMIT 1")
    last_account = await cursor.fetchone()
    return last_account[0] if last_account else None

async def get_accounts(conn, bank_condition):
    """Fetch accounts based on bank condition."""
    cursor = await conn.execute(f"SELECT id, account_bank_name, account_beneficiary, account_number, account_limit FROM mxn_bank_accounts WHERE account_bank_name LIKE '{bank_condition}' ORDER BY id")
    return await cursor.fetchall()

async def assign_account(conn, accounts, last_account, cutoff_time, order_no):
    """Assign a new account for the order."""
    start_index = next((index for index, account in enumerate(accounts) if account[3] == last_account), -1) + 1

    for i in range(len(accounts)):
        account = accounts[(start_index + i) % len(accounts)]
        total_deposited = await get_total_deposited(conn, account[3], cutoff_time)

        if total_deposited < account[4]:
            await conn.execute('UPDATE mxn_bank_accounts SET last_used_timestamp = ? WHERE account_number = ?', (datetime.datetime.now(), account[3]))
            await update_order_details(conn, order_no, account[3])
            return account[3]

    return None

async def get_total_deposited(conn, account_number, cutoff_time):
    """Calculate total amount deposited for an account since cutoff time."""
    cursor = await conn.execute('SELECT SUM(amount_deposited) FROM mxn_deposits WHERE account_number = ? AND timestamp >= ?', (account_number, cutoff_time))
    total_deposited = await cursor.fetchone()
    return total_deposited[0] if total_deposited and total_deposited[0] is not None else 0.0

async def get_account_details(conn, account_number):
    """Retrieve account details for the assigned account number."""
    cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM mxn_bank_accounts WHERE account_number = ?', (account_number,))
    account_details = await cursor.fetchone()
    
    if account_details:
        return (
            f"Los detalles para el pago son:\n\n"
            f"Nombre de banco: {account_details[0]}\n"
            f"Nombre del beneficiario: {account_details[1]}\n"
            f"Número de CLABE: {account_details[2]}\n"
        )
    return None