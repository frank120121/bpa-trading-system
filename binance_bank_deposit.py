import datetime
import random
import logging
from binance_db_get import get_buyer_bank
from binance_db_set import update_order_details
from common_vars import BBVA_BANKS

logger = logging.getLogger(__name__)

async def log_deposit(conn, deposit_from, bank_account_number, amount_deposited):
    timestamp = datetime.datetime.now()
    year, month = timestamp.year, timestamp.month 
    await conn.execute('INSERT INTO mxn_deposits (timestamp, account_number, amount_deposited, deposit_from, year, month) VALUES (?, ?, ?, ?, ?, ?)',
                       (timestamp, bank_account_number, amount_deposited, deposit_from, year, month))
    await conn.execute('UPDATE mxn_bank_accounts SET account_balance = account_balance + ? WHERE account_number = ?', (amount_deposited, bank_account_number))
    await conn.commit()

async def get_payment_details(conn, order_no):
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    assigned_account_number = result[0] if result else None

    if assigned_account_number:
        logger.info(f"Account already assigned for order {order_no}.")
        return await get_account_details(conn, assigned_account_number)

    buyer_bank = await get_buyer_bank(conn, order_no)
    bank_condition = 'BBVA' if buyer_bank in BBVA_BANKS else 'NOT BBVA'
    
    eligible_account = await get_eligible_account_with_lowest_balance(conn, bank_condition)

    if not eligible_account:
        logger.info("No eligible accounts found or all accounts have reached their limit.")
        return "No eligible accounts or reached limit."

    await update_order_details(conn, order_no, eligible_account['account_number'])
    logger.info(f"Account {eligible_account['account_number']} assigned to order {order_no}.")
    return await get_account_details(conn, eligible_account['account_number'])


async def get_eligible_account_with_lowest_balance(conn, bank_condition):
    # Adjust the SQL query to filter accounts based on the bank condition and order by account_balance
    condition = "account_bank_name = 'BBVA'" if bank_condition == 'BBVA' else "account_bank_name != 'BBVA'"
    query = f"""
    SELECT account_number, account_balance
    FROM mxn_bank_accounts
    WHERE {condition}
    ORDER BY account_balance ASC
    LIMIT 1
    """
    cursor = await conn.execute(query)
    return await cursor.fetchone()

async def get_account_details(conn, account_number):
    cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM mxn_bank_accounts WHERE account_number = ?', (account_number,))
    account_details = await cursor.fetchone()
    if account_details:
        # Determine the account label based on the bank name
        account_label = "Número de cuenta" if account_details[0].lower() == "bbva" else "Número de CLABE"
        
        return (
            f"Los detalles para el pago son:\n\n"
            f"Nombre de banco: {account_details[0]}\n"
            f"Nombre del beneficiario: {account_details[1]}\n"
            f"{account_label}: {account_details[2]}\n"
        )